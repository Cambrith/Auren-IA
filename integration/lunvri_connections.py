"""Read local credentials and public model metadata; never persist provider keys."""

from __future__ import annotations

import json
import os
import re
import threading
import time
from decimal import Decimal, InvalidOperation
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from cavren.config import load_settings
from cavren.model_registry import MODEL_BY_ROUTE
from cavren.nextchat_server import CavrenHandler, worker_env

KEY_LABELS = {
    'gemini': 'GEMINI_API_KEY',
    'groq': 'GROQ_API_KEY',
    'mistral': 'MISTRAL_API_KEY',
    'openrouter': 'OPENROUTER_API_KEY',
    'cloudflare': 'CLOUDFLARE_API_TOKEN',
    'cloudfare': 'CLOUDFLARE_API_TOKEN',
    'cloudflare account id': 'CLOUDFLARE_ACCOUNT_ID',
}
STATE = Path(os.environ.get('LUNVRI_RUNTIME_DIR', Path(__file__).resolve().parents[1] / '.cavren'))
LOCK = threading.RLock()
_catalog = None
_updated = 0.0


def parse_credentials(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        if ':' in line:
            label, value = line.split(':', 1)
            name = KEY_LABELS.get(label.strip().lower())
        elif '=' in line:
            name, value = line.split('=', 1)
            name = name.strip() if name.strip() in KEY_LABELS.values() else None
        else:
            continue
        value = value.strip().strip('"\'')
        if name and value and re.fullmatch(r'[!-~]+', value):
            result[name] = value
    return result


def credentials_env() -> dict[str, str]:
    env = {name: value for name, value in worker_env().items() if not name.startswith('DEEPSEEK_')}
    path = Path(os.environ.get('LUNVRI_CREDENTIALS_FILE', Path.home() / 'Documentos' / 'Chaves de API - Cavren'))
    if path.is_file():
        # Existing working credentials take priority; the file fills missing connections.
        for name, value in parse_credentials(path.read_text()).items():
            if not env.get(name):
                env[name] = value
    return env


def connection_settings(env=None):
    env = env or credentials_env()
    settings = load_settings(env)
    return settings


def capabilities(provider, raw, model_id):
    arch = raw.get('architecture') or {}
    inputs = arch.get('input_modalities') or raw.get('input_modalities') or []
    outputs = arch.get('output_modalities') or raw.get('output_modalities') or []
    caps = raw.get('capabilities') or {}
    gemini = provider == 'gemini' and model_id.startswith('gemini-') and 'tts' not in model_id
    image_out = 'image' in outputs or gemini and ('image' in model_id or 'nano-banana' in model_id)
    return {
        'vision': 'image' in inputs or caps.get('vision') is True or gemini,
        'video': 'video' in inputs or (gemini and not image_out),
        'audio': 'audio' in inputs or (gemini and not image_out),
        'pdf': 'file' in inputs or (gemini and not image_out),
        'image_generation': bool(image_out and provider in ('gemini', 'openrouter')),
        'file_upload': True,  # Text documents are extracted locally, without embeddings.
        'web_search': False,  # The Lunvri search control uses the engine's SearXNG.
        'builtin_tools': False,
        'code_interpreter': False,
        'terminal': False,
    }


def cloudflare_free_plan():
    try:
        return json.loads((STATE / 'provider_policy.json').read_text()).get('cloudflare_workers_free') is True
    except (OSError, ValueError, AttributeError):
        return False


def deepseek_allowed(provider, model_id, free):
    if 'deepseek' not in (provider + ':' + model_id).casefold():
        return True
    if provider == 'openrouter':
        return model_id.endswith(':free') and free
    if provider == 'cloudflare':
        # Only this documented Free-plan model is allowed; new/paid variants stay blocked.
        return model_id == '@cf/deepseek-ai/deepseek-r1-distill-qwen-32b' and cloudflare_free_plan()
    return False


def public_model(provider, raw):
    model_id = (
        (raw.get('name') or raw.get('id') or '')
        if provider == 'cloudflare'
        else (raw.get('id') or raw.get('name') or '')
    )
    model_id = model_id.removeprefix('models/') if provider == 'gemini' else model_id
    if not model_id or raw.get('archived') or raw.get('active') is False:
        return None
    caps = raw.get('capabilities') or {}
    methods = raw.get('supportedGenerationMethods') or []
    if provider == 'gemini' and (
        'generateContent' not in methods or any(word in model_id.lower() for word in ('tts', 'lyria', 'transcribe'))
    ):
        return None
    if caps.get('completion_chat') is False:
        return None
    if provider == 'groq' and any(w in model_id for w in ('whisper', 'tts', 'speech', 'playai', 'orpheus')):
        return None
    if provider == 'cloudflare' and (raw.get('task') or {}).get('name') != 'Text Generation':
        return None
    arch = raw.get('architecture') or {}
    outputs = arch.get('output_modalities') or []
    if outputs and not any(m in outputs for m in ('text', 'image')):
        return None
    price = raw.get('pricing') or {}
    free = (
        not capabilities(provider, raw, model_id)['image_generation']
        and provider == 'openrouter'
        and str(price.get('prompt')) in ('0', '0.0')
        and str(price.get('completion')) in ('0', '0.0')
    )
    if provider == 'openrouter' and 'deepseek' in model_id.casefold():
        try:
            free = free and all(Decimal(str(value)) == 0 for value in price.values())
        except (InvalidOperation, ValueError):
            free = False
    if not deepseek_allowed(provider, model_id, free):
        return None
    if provider == 'cloudflare' and 'deepseek' in model_id.casefold():
        if any(
            p.get('property_id') == 'require_workers_paid' and str(p.get('value')).lower() == 'true'
            for p in raw.get('properties', [])
        ):
            return None
        free = True
    label = raw.get('displayName') or raw.get('display_name') or raw.get('name') or model_id
    route = f'{provider}:{model_id}'
    info = {
        'route_id': route,
        'provider': provider,
        'model_id': model_id,
        'label': f'{label} · {provider}',
        'available': True,
        'price_kind': 'free' if free else 'unknown',
        'integrated': False,
        'context_window': raw.get('inputTokenLimit') or raw.get('context_length') or 32000,
        'output_limit': raw.get('outputTokenLimit')
        or (raw.get('top_provider') or {}).get('max_completion_tokens')
        or 4096,
        'capabilities': capabilities(provider, raw, model_id),
        'image_only': bool(outputs and 'image' in outputs and 'text' not in outputs),
    }
    return model_entry('cavren:' + route, info)


def model_entry(id, info):
    return {
        'id': id,
        'object': 'model',
        'name': 'Lunvri',
        'owned_by': 'openai',
        'cavren': info,
        'info': {'meta': {'capabilities': info['capabilities']}, 'params': {'function_calling': 'legacy'}},
    }


def discover(provider, config):
    headers = {'Authorization': 'Bearer ' + config.api_key}
    url = config.base_url + '/models'
    params = {}
    if provider == 'gemini':
        url = 'https://generativelanguage.googleapis.com/v1beta/models'
        headers = {'x-goog-api-key': config.api_key}
        params = {'pageSize': 1000}
    elif provider == 'cloudflare':
        url = f'https://api.cloudflare.com/client/v4/accounts/{config.account_id}/ai/models/search'
        params = {'per_page': 1000}
    try:
        with httpx.Client(trust_env=False, timeout=20) as client:
            response = client.get(url, headers=headers, params=params)
            if response.status_code != 200:
                return [], {'connected': False, 'status': response.status_code}
            payload = response.json()
            image_models = []
            if provider == 'openrouter':
                image_response = client.get('https://openrouter.ai/api/v1/images/models', headers=headers)
                if image_response.status_code == 200:
                    image_models = image_response.json().get('data') or []
        items = payload.get('data', payload.get('models', payload.get('result', [])))
        if isinstance(items, dict):
            items = items.get('models', [])
        if not isinstance(items, list):
            return [], {'connected': False, 'status': 'invalid_catalog'}
        if provider == 'openrouter':
            image_ids = {raw['id'] for raw in image_models if isinstance(raw, dict) and raw.get('id')}
            items = [*items, *image_models]
        models = [model for raw in items if isinstance(raw, dict) and (model := public_model(provider, raw))]
        if provider == 'openrouter':
            for model in models:
                model['cavren']['capabilities']['image_generation'] = model['cavren']['model_id'] in image_ids
        return models, {'connected': True, 'count': len(models)}
    except (httpx.HTTPError, ValueError, TypeError):
        return [], {'connected': False, 'status': 'unavailable'}


def catalog(refresh=False):
    global _catalog, _updated
    with LOCK:
        if _catalog is not None and not refresh and time.time() - _updated < 300:
            return _catalog
        settings = connection_settings()
        auto_caps = capabilities('', {}, '') | {'vision': True}
        entries = {
            'cavren:auto': model_entry(
                'cavren:auto',
                {
                    'label': 'Automático',
                    'available': True,
                    'price_kind': 'free',
                    'integrated': True,
                    'capabilities': auto_caps,
                },
            )
        }
        for item in CavrenHandler._integrated_models():
            if 'deepseek' in item['route_id'].casefold():
                continue
            definition = MODEL_BY_ROUTE[item['route_id']]
            caps = {
                **auto_caps,
                'vision': 'vision' in definition.capabilities,
                'video': 'video_input' in definition.capabilities,
                'audio': 'audio_input' in definition.capabilities,
                'pdf': 'pdf_input' in definition.capabilities,
            }
            entries['cavren:' + item['route_id']] = model_entry(
                'cavren:' + item['route_id'],
                {
                    **item,
                    'label': item['name'] + ' · ' + item['provider'],
                    'integrated': True,
                    'capabilities': caps,
                },
            )
        providers = {
            name: config
            for name, config in settings.providers.items()
            if name != 'deepseek' and config.api_key and (name != 'cloudflare' or config.account_id)
        }
        statuses = {}
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {name: pool.submit(discover, name, config) for name, config in providers.items()}
            for name, future in futures.items():
                models, statuses[name] = future.result()
                for model in models:
                    if model['id'] not in entries or model['cavren'].get('image_only'):
                        entries[model['id']] = model
        _catalog = [
            entries.pop('cavren:auto'),
            *sorted(entries.values(), key=lambda m: m['cavren']['label'].casefold()),
        ]
        _updated = time.time()
        STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
        (STATE / 'models.json').write_text(json.dumps({'models': _catalog, 'providers': statuses, 'updated': _updated}))
        return _catalog


def cached_model(id):
    try:
        model = next((m for m in json.loads((STATE / 'models.json').read_text())['models'] if m['id'] == id), None)
        if model:
            info = model['cavren']
            if not deepseek_allowed(
                info.get('provider', ''), info.get('model_id', id), info.get('price_kind') == 'free'
            ):
                return None
        return model
    except (FileNotFoundError, ValueError, KeyError):
        return None
