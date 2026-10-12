"""Bounded fallback across compatible free routes, with shared cooldowns."""
from dataclasses import replace
import fcntl
import json
import os
import time
from pathlib import Path

from cavren.errors import CavrenError
from cavren.modes import routes_for
from integration.lunvri_connections import STATE, connection_settings, deepseek_allowed
from integration.lunvri_manual import run as run_route, emit

RECOVERABLE = {'auth', 'forbidden', 'rate_limit', 'quota_exhausted', 'unavailable_for_plan',
               'unavailable', 'not_found', 'timeout', 'network', 'invalid_response', 'request', 'context_too_large'}


def cooldowns(route=None, error=None):
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (STATE / 'route_cooldowns.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = STATE / 'route_cooldowns.json'
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            data = {}
        data = {k: v for k, v in data.items() if isinstance(v, (int, float)) and v > time.time()}
        if route and error:
            delays = {'auth': 3600, 'forbidden': 3600, 'quota_exhausted': 3600,
                      'not_found': 3600, 'request': 300, 'rate_limit': 90}
            delay = max(delays.get(error.code, 60), min(error.retry_after or 0, 86400))
            provider = route.split(':', 1)[0]
            shared = error.code in ('auth', 'forbidden') or (error.code == 'quota_exhausted' and provider in ('cloudflare', 'cohere', 'nvidia', 'aihorde')) or (error.code == 'rate_limit' and provider in ('cohere', 'nvidia', 'aihorde', 'openrouter'))
            key = provider + ':*' if shared else route
            data[key] = time.time() + delay
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(data))
        temporary.chmod(0o600)
        temporary.replace(path)
        return data


def requirements(messages):
    caps = set()
    for message in messages:
        if isinstance(message['content'], list):
            for part in message['content']:
                cap = {'image_url': 'vision', 'input_video': 'video', 'video_url': 'video',
                       'input_audio': 'audio', 'file': 'pdf'}.get(part.get('type'))
                if cap:
                    caps.add(cap)
    return caps


def candidates(job, models, settings, blocked):
    required = requirements(job['messages'])
    manual = job['mode_options'].get('manual_route')
    mode_routes = {r.route_id: i for i, r in enumerate(routes_for(job['mode_id']))}
    def priority(model):
        info = model['cavren']
        route = info.get('route_id', '')
        if manual == route:
            return (-1, 0, route)
        if route in mode_routes:
            return (0, mode_routes[route], route)
        # Curated reasoning/code families supplement the existing mode profile.
        name = info.get('model_id', '').lower()
        good = any(s in name for s in ('qwen', 'nemotron', 'command-a', 'glm', 'gpt-oss', 'gemini', 'kimi'))
        fast = any(s in name for s in ('flash', '8b', '20b', 'nano', 'mini'))
        preferred = {'nvidia/nemotron-3.5-lightning-30b-a3b', 'command-a-03-2025', 'glm-4.5-flash'}
        return (1 if good else 2, 0 if name in preferred or (job['mode_id'] == 'impeto' and fast) else 1, route)
    result = []
    for model in sorted(models, key=priority):
        info = model['cavren']
        route, provider = info.get('route_id'), info.get('provider')
        if not route or not info.get('available', True):
            continue
        config = settings.providers.get(provider)
        if not config or not config.api_key or (provider == 'cloudflare' and not config.account_id):
            continue
        if info.get('price_kind') != 'free' and not (route == manual and job['mode_options'].get('billing_confirmed')):
            continue
        if not deepseek_allowed(provider, info['model_id'], info.get('price_kind') == 'free'):
            continue
        if blocked.get(route, 0) > time.time() or blocked.get(provider + ':*', 0) > time.time():
            continue
        caps = info['capabilities']
        if not all(caps.get(cap) for cap in required):
            continue
        image = bool(job.get('lunvri_image_generation'))
        if image and not caps.get('image_generation') or not image and info.get('image_only'):
            continue
        if job['mode_id'] in ('insight', 'arquiteto') and route != manual and priority(model)[0] == 2:
            continue
        # Never discard attachments or truncate the supplied conversation to fit a fallback.
        # Image/video bytes are not text tokens; native providers enforce their media limit.
        chars = sum(len(m['content']) if isinstance(m['content'], str) else sum(len(p.get('text','')) for p in m['content']) for m in job['messages'])
        if chars // 3 + 6000 + min(int(job.get('max_tokens', 4096)), int(info.get('output_limit',4096))) > int(info.get('context_window') or 32000):
            continue
        result.append(model)
    # Diversify supplemental providers to avoid exhausting many models of one account.
    primary = [m for m in result if priority(m)[0] <= 0]
    extra = [m for m in result if priority(m)[0] > 0]
    first, rest, seen = [], [], set()
    for model in extra:
        provider = model['cavren']['provider']
        (rest if provider in seen else first).append(model)
        seen.add(provider)
    return (primary + first + rest)[:10]


def run(job, normalize_messages, *, route_runner=run_route, output=emit):
    models = json.loads((STATE / 'models.json').read_text())['models']
    settings = connection_settings()
    choices = candidates(job, models, settings, cooldowns())
    if not choices:
        raise CavrenError('routes', 'Nenhum modelo gratuito compatível está disponível agora. Troque o modelo ou aguarde a renovação da cota.')
    started = time.monotonic()
    sequence = 0
    search_context = None
    last_error = None
    for index, model in enumerate(choices):
        if time.monotonic() - started > 480:
            break
        info = model['cavren']
        # Another process can discover an exhausted credential while this request is running.
        blocked = cooldowns()
        if blocked.get(info['route_id'],0) > time.time() or blocked.get(info['provider'] + ':*',0) > time.time():
            continue
        if index:
            output({'type': 'generation.fallback', 'description': 'Tentando ' + info['label'] + ' · ' + info.get('provider_name',info['provider'])})
        attempt = dict(job, mode_options=dict(job['mode_options'], manual_route=info['route_id']),
                       auren_context=search_context)
        visible = False
        def forward(event):
            nonlocal visible, sequence
            if event['type'] == 'generation.delta' and event.get('text', '').strip():
                visible = True
            if event['type'] == 'generation.error':
                raise CavrenError(event.get('code','provider'),event.get('message','Falha no provedor.'))
            if event['type'] == 'generation.completed':
                event['response']['public_mode'] = job['mode_id']
                event['response']['fallback_index'] = index
            sequence += 1
            output(dict(event, sequence=sequence))
        try:
            route_runner(attempt, normalize_messages, output=forward)
            return 0
        except CavrenError as error:
            last_error = error
            if error.code in RECOVERABLE and error.code != 'context_too_large':
                cooldowns(info['route_id'],error)
            if visible or error.code not in RECOVERABLE:
                raise
            # Search context is retained by the runner, keeping one search per request.
            search_context = attempt.get('auren_context')
    raise CavrenError('routes', 'Os modelos compatíveis atingiram limites ou falharam. Aguarde a renovação da cota ou escolha outro modelo. ' + (str(last_error) if last_error else ''))
