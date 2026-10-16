"""Read local credentials and public model metadata; never persist provider keys."""

from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import replace
from decimal import Decimal, InvalidOperation
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from cavren.config import load_settings, ProviderConfig
from cavren.model_registry import MODEL_BY_ROUTE
from cavren.nextchat_server import CavrenHandler, worker_env

KEY_LABELS = {
    'openai': 'OPENAI_API_KEY',
    'chatgpt': 'OPENAI_API_KEY',
    'deepseek': 'DEEPSEEK_API_KEY',
    'huggingface': 'HUGGINGFACE_API_KEY',
    'hugging face': 'HUGGINGFACE_API_KEY',
    'x.ai': 'XAI_API_KEY',
    'xai': 'XAI_API_KEY',
    'grok': 'XAI_API_KEY',
    'claude': 'ANTHROPIC_API_KEY',
    'anthropic': 'ANTHROPIC_API_KEY',
    'gemini': 'GEMINI_API_KEY',
    'groq': 'GROQ_API_KEY',
    'mistral': 'MISTRAL_API_KEY',
    'openrouter': 'OPENROUTER_API_KEY',
    'cloudflare': 'CLOUDFLARE_API_TOKEN',
    'cloudfare': 'CLOUDFLARE_API_TOKEN',
    'cohere': 'COHERE_API_KEY',
    'cohere (julgamento)': 'COHERE_API_KEY',
    'nvidia nim': 'NVIDIA_API_KEY',
    'nvidia': 'NVIDIA_API_KEY',
    'ollama cloud': 'OLLAMA_API_KEY',
    'ai horde': 'AI_HORDE_API_KEY',
    'z.ai': 'ZAI_API_KEY',
    'cloudflare account id': 'CLOUDFLARE_ACCOUNT_ID',
}
STATE = Path(os.environ.get('LUNVRI_RUNTIME_DIR', Path(__file__).resolve().parents[1] / '.cavren'))
LOCK = threading.RLock()
_catalog = None
_updated = 0.0
_refreshing = False
_attempted = 0.0


def parse_credentials(text: str) -> dict[str, str]:
    result = {}
    section = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('#'):
            section = KEY_LABELS.get(line.lstrip('#').strip().lower())
            continue
        if ':' in line:
            label, value = line.split(':', 1)
            label = label.lstrip('-* ').strip().lower()
            name = section if label in ('chave de api', 'chave', 'token') else KEY_LABELS.get(label)
        elif '=' in line:
            name, value = line.split('=', 1)
            name = name.strip() if name.strip() in KEY_LABELS.values() else None
        else:
            continue
        value = value.strip().strip('`"\'')
        if name and value and re.fullmatch(r'[!-~]+', value):
            result[name] = value
    return result


def credentials_env() -> dict[str, str]:
    from integration.auren_credentials import AurenVault, remember_credentials
    vault = AurenVault()
    env = {name: value for name, value in worker_env().items() if name not in ('DEEPSEEK_API_KEY',)}
    # Optional direct providers remain dormant until explicitly configured in Auren.
    for key in ('OPENAI_API_KEY','ANTHROPIC_API_KEY','DEEPSEEK_API_KEY','XAI_API_KEY','HUGGINGFACE_API_KEY'):
        env.pop(key,None)
    from cavren.credentials import KEY_NAMES
    try: optional_policy=json.loads((STATE/'provider_policy.json').read_text())
    except (OSError,ValueError): optional_policy={}
    for name in (set(KEY_LABELS.values()) - set(KEY_NAMES)) | {'DEEPSEEK_API_KEY'}:
        optional={'OPENAI_API_KEY':'openai','ANTHROPIC_API_KEY':'anthropic','DEEPSEEK_API_KEY':'deepseek','XAI_API_KEY':'xai','HUGGINGFACE_API_KEY':'huggingface'}.get(name)
        if optional and optional_policy.get(optional+'_configured') is not True: continue
        stored = vault.get(name)
        if stored: env[name] = stored
    # User documents are import sources only, never a runtime credential store.
    remember_credentials(env)
    for name in ('CEREBRAS_API_KEY','DEEPINFRA_API_KEY','NOVITA_API_KEY','FIREWORKS_API_KEY','AWS_BEARER_TOKEN_BEDROCK','AWS_REGION','AUREN_BEDROCK_BASE_URL'):
        value=vault.get(name)
        if value:env[name]=value
    return env


def connection_settings(env=None):
    env = env or credentials_env()
    settings = load_settings(env)
    additions = {
        'openai': ('https://api.openai.com/v1', 'OPENAI_API_KEY'),
        'deepseek': ('https://api.deepseek.com/v1', 'DEEPSEEK_API_KEY'),
        'huggingface': ('https://router.huggingface.co/v1', 'HUGGINGFACE_API_KEY'),
        'xai': ('https://api.x.ai/v1', 'XAI_API_KEY'),
        'anthropic': ('https://api.anthropic.com/v1', 'ANTHROPIC_API_KEY'),
        'cohere': ('https://api.cohere.ai/compatibility/v1', 'COHERE_API_KEY'),
        'nvidia': ('https://integrate.api.nvidia.com/v1', 'NVIDIA_API_KEY'),
        'ollama': ('https://ollama.com/v1', 'OLLAMA_API_KEY'),
        'zai': ('https://api.z.ai/api/paas/v4', 'ZAI_API_KEY'),
        'aihorde': ('https://aihorde.net/api/v2', 'AI_HORDE_API_KEY'),
        'cerebras': ('https://api.cerebras.ai/v1','CEREBRAS_API_KEY'),
        'deepinfra': ('https://api.deepinfra.com/v1/openai','DEEPINFRA_API_KEY'),
        'novita': ('https://api.novita.ai/v3/openai','NOVITA_API_KEY'),
        'fireworks': ('https://api.fireworks.ai/inference/v1','FIREWORKS_API_KEY'),
    }
    providers = dict(settings.providers)
    for name, (url, key) in additions.items():
        providers[name] = ProviderConfig(name=name, model='', base_url=url, key_env=key, api_key=env.get(key, ''))
    if env.get('AWS_REGION') and env.get('AUREN_BEDROCK_BASE_URL'):
        from integration.auren_bedrock import validate_base_url
        base=validate_base_url(env['AUREN_BEDROCK_BASE_URL'],env['AWS_REGION'])
        providers['bedrock']=ProviderConfig(name='bedrock',model='',base_url=base,key_env='AWS_BEARER_TOKEN_BEDROCK',api_key=env.get('AWS_BEARER_TOKEN_BEDROCK',''))
    try: availability=json.loads((STATE/'provider_policy.json').read_text()).get('provider_availability',{})
    except (OSError,ValueError,AttributeError):availability={}
    for name,rule in availability.items():
        if name in providers and rule.get('disabled') is True:providers[name]=replace(providers[name],api_key='')
    return replace(settings, providers=providers)


PAID_PROVIDERS = frozenset(('openai', 'anthropic', 'deepseek', 'xai','bedrock','cerebras','deepinfra','novita','fireworks'))

PROVIDER_NAMES = {'openai':'OpenAI', 'anthropic':'Anthropic', 'deepseek':'DeepSeek', 'huggingface':'Hugging Face', 'xai':'xAI', 'gemini': 'Google Gemini', 'groq': 'Groq', 'mistral': 'Mistral AI',
                  'openrouter': 'OpenRouter', 'cloudflare': 'Cloudflare', 'cohere': 'Cohere',
                  'nvidia': 'NVIDIA NIM', 'ollama': 'Ollama Cloud', 'zai': 'Z.ai', 'aihorde': 'AI Horde'}
PROVIDER_NAMES.update({'bedrock':'Amazon Bedrock','cerebras':'Cerebras Inference API','deepinfra':'DeepInfra API','novita':'Novita AI API','fireworks':'Fireworks AI API'})


def display_name(value):
    value = value.removeprefix('models/').removeprefix('@cf/').split('/')[-1]
    value = value.removesuffix(':free').removesuffix(':cloud')
    value = re.sub(r'[-_]', ' ', value).replace(':', ' · ')
    words = {'gpt': 'GPT', 'oss': 'OSS', 'glm': 'GLM', 'llama': 'Llama', 'qwen': 'Qwen',
             'gemini': 'Gemini', 'nemotron': 'Nemotron', 'kimi': 'Kimi', 'command': 'Command',
             'deepseek': 'DeepSeek', 'openai': 'OpenAI', 'chatgpt': 'ChatGPT', 'gemma': 'Gemma', 'r1': 'R1', 'vl': 'VL', 'a': 'A', 'ai': 'AI'}
    clean = ' '.join(words.get(w.lower(), w.upper() if re.fullmatch(r'\d+[bB]', w) else w.capitalize()) for w in value.split())
    clean = re.sub(r'\b(Gpt|Glm)(?=\d)', lambda m: m[0].upper(), clean)
    return re.sub(r'\s*\(free\)', '', clean, flags=re.I)


def capabilities(provider, raw, model_id):
    from integration.auren_media import TESTED_INPUTS
    tested = TESTED_INPUTS.get(provider + ':' + model_id, set())
    arch = raw.get('architecture') or {}
    inputs = arch.get('input_modalities') or raw.get('input_modalities') or []
    outputs = arch.get('output_modalities') or raw.get('output_modalities') or []
    caps = raw.get('capabilities') or {}
    if not isinstance(caps, dict):
        caps = {name: True for name in caps}
    gemini = provider == 'gemini' and model_id.startswith('gemini-') and 'tts' not in model_id
    if provider == 'anthropic':
        caps = {**caps,'vision':(caps.get('image_input') or {}).get('supported') is True}
    image_out = 'image' in outputs or gemini and ('image' in model_id or 'nano-banana' in model_id)
    return {
        'vision': 'vision' in tested or 'image' in inputs or caps.get('vision') is True or gemini or (provider == 'nvidia' and model_id == 'meta/llama-3.2-11b-vision-instruct') or (provider == 'cohere' and model_id == 'command-a-vision-07-2025'),
        'video': 'video' in inputs or (gemini and not image_out),
        'audio': 'audio' in inputs or (gemini and not image_out),
        'pdf': 'file' in inputs or (gemini and not image_out),
        'image_generation': bool(image_out and provider in ('gemini', 'openrouter', 'aihorde')),
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
    if provider in ('deepseek', 'huggingface'):
        return True  # Manual paid/unknown routes still require the billing gate.
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
    if provider == 'openai' and (not model_id.startswith(('gpt-','chatgpt-','o1','o3','o4')) or any(w in model_id for w in ('image','audio','realtime','transcribe','search','codex','deep-research','-pro'))):
        return None
    if provider == 'anthropic' and (not model_id.startswith('claude-') or raw.get('lifecycle') in ('retired','deprecated')):
        return None
    if provider == 'xai' and not model_id.startswith('grok-'):
        return None
    if provider == 'xai' and any(w in model_id for w in ('image', 'video', 'imagine')):
        return None
    if provider == 'cohere' and (raw.get('is_deprecated') or 'chat' not in raw.get('endpoints', [])):
        return None
    if any(w in model_id.lower() for w in ('embed', 'rerank', 'guard', 'reward', 'whisper', 'tts', 'detector', 'content-safety', 'nemotron-parse', 'deplot')):
        return None
    if not model_id or raw.get('archived') or raw.get('active') is False:
        return None
    caps = raw.get('capabilities') or {}
    if not isinstance(caps, dict):
        caps = {name: True for name in caps}
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
    if provider == 'zai' and model_id == 'glm-4.5-flash':
        free = True
    if provider == 'aihorde':
        free = True
    if provider in ('cohere', 'nvidia'):
        try:
            policy = json.loads((STATE / 'provider_policy.json').read_text())
            free = policy.get(provider + '_trial') is True
        except (OSError, ValueError):
            pass
    if provider == 'openrouter':
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
    if provider in ('mistral', 'ollama'):
        label = model_id
    route = f'{provider}:{model_id}'
    info = {
        'image_workers': raw.get('count') if provider == 'aihorde' else None,
        'route_id': route,
        'provider': provider,
        'model_id': model_id,
        'label': display_name(label),
        'usage_label': 'Teste gratuito / créditos' if free and provider in ('cohere', 'nvidia') else '',
        'provider_name': PROVIDER_NAMES.get(provider, provider),
        'available': True,
        'price_kind': 'paid' if provider in PAID_PROVIDERS else 'free' if free else 'unknown',
        'integrated': False,
        'context_window': raw.get('inputTokenLimit') or raw.get('max_input_tokens') or raw.get('context_length') or 32000,
        'output_limit': raw.get('outputTokenLimit') or raw.get('max_tokens')
        or (raw.get('top_provider') or {}).get('max_completion_tokens')
        or 4096,
        'capabilities': capabilities(provider, raw, model_id),
        'image_only': bool(outputs and 'image' in outputs and 'text' not in outputs),
    }
    from integration.auren_images import operations
    info['image_operations'] = list(operations(info))
    info['image_validation'] = 'advertised'
    return model_entry('cavren:' + route, info)


def model_entry(id, info):
    from integration.auren_validation import model_evidence, verified
    kind = 'speech' if info.get('task_operations')==['speech'] else 'transcribe' if info.get('task_operations')==['transcribe'] else 'image' if info.get('capabilities', {}).get('image_generation') else 'text'
    record = model_evidence(id, kind)
    info['validation'] = {'status': record.get('status', 'not_tested'), 'free_verified': verified(id, kind),
                          'mean_seconds': record.get('mean_seconds'), 'date': record.get('verified_at')}
    return {
        'id': id,
        'object': 'model',
        'name': info['label'],
        'provider': info.get('provider'),
        'transport': 'openai-compatible',
        'owned_by': 'openai',
        'cavren': info,
        'info': {'meta': {'provider': info.get('provider'), 'provider_name': info.get('provider_name'), 'model_source': 'external' if info.get('provider') else 'automatic', 'capabilities': info['capabilities']}, 'params': {'function_calling': 'legacy'}},
    }


def discover(provider, config):
    if provider=='bedrock':
        from integration.auren_bedrock import discover as aws_discover
        from urllib.parse import urlsplit
        region=urlsplit(config.base_url).hostname.split('.')[1]
        try:
            with httpx.Client(trust_env=False,timeout=20) as client:
                rows,error=aws_discover({'key':config.api_key,'region':region,'base_url':config.base_url},client)
            if error:return [],{'connected':False,'status':error[1]}
            try:support=json.loads((STATE/'bedrock_model_support.json').read_text())
            except (OSError,ValueError):support={}
            allowed=set(support.get('runtime_chat_models',[])) if support.get('region')==region else set()
            models=[model for r in rows if r['id'] in allowed and (model:=public_model(provider,{'id':r['id'],'name':r['name']}))]
            return models,{'connected':True,'count':len(models),'regional_catalogue_count':len(rows),'inference_tested':False}
        except (httpx.HTTPError,ValueError,KeyError,TypeError):return [],{'connected':False,'status':'unavailable'}
    headers = {'Authorization': 'Bearer ' + config.api_key}
    url = config.base_url + '/models'
    params = {}
    if provider == 'anthropic':
        headers = {'x-api-key':config.api_key,'anthropic-version':'2023-06-01'}
        params = {'limit':1000}
    elif provider == 'cohere':
        url = 'https://api.cohere.com/v1/models'
        params = {'endpoint': 'chat', 'page_size': 1000}
    elif provider == 'ollama':
        url = 'https://ollama.com/api/tags'
    elif provider == 'aihorde':
        url = 'https://aihorde.net/api/v2/status/models'
        headers = {'apikey': config.api_key}
        params = {'type': 'image'}
    elif provider == 'zai':
        return [public_model(provider, {'id': 'glm-4.5-flash', 'context_length': 128000, 'outputTokenLimit': 8192})], {'connected': None, 'status': 'configured'}
    elif provider == 'gemini':
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
        items = payload if isinstance(payload, list) else payload.get('data', payload.get('models', payload.get('result', [])))
        if isinstance(items, dict):
            items = items.get('models', [])
        if not isinstance(items, list):
            return [], {'connected': False, 'status': 'invalid_catalog'}
        if provider == 'openrouter':
            image_ids = {raw['id'] for raw in image_models if isinstance(raw, dict) and raw.get('id')}
            items = [*items, *image_models]
        if provider == 'aihorde':
            items = [dict(raw, architecture={'output_modalities': ['image']}) for raw in items if isinstance(raw, dict) and raw.get('count', 0) > 0]
        models = [model for raw in items if isinstance(raw, dict) and (model := public_model(provider, raw))]
        if provider == 'openrouter':
            for model in models:
                model['cavren']['capabilities']['image_generation'] = model['cavren']['model_id'] in image_ids
        return models, {'connected': True, 'count': len(models)}
    except (httpx.HTTPError, ValueError, TypeError):
        return [], {'connected': False, 'status': 'unavailable'}


def validated_catalog(models):
    try: availability=json.loads((STATE/'provider_policy.json').read_text()).get('provider_availability',{})
    except (OSError,ValueError,AttributeError):availability={}
    for model in models:
        rule=availability.get(model.get('cavren',{}).get('provider'),{})
        if rule.get('disabled') is True:
            model['cavren'].update(available=False,usage_label='Reservado para ativação futura' if rule.get('reason')=='future_credentials' else 'Indisponível: conta bloqueada no provedor')
    from integration.auren_validation import model_evidence, verified
    from integration.auren_media import TESTED_INPUTS
    from integration.auren_tasks import task_evidence
    for task_name, record in task_evidence().items():
        id=record.get('model')
        if not (task_name.startswith('transcribe_') or task_name=='speech') or not id or not verified(id,'speech' if task_name=='speech' else 'transcribe') or any(m['id']==id for m in models):continue
        provider,name=id.removeprefix('cavren:').split(':',1)
        models.append(model_entry(id,{'route_id':id.removeprefix('cavren:'),'provider':provider,'model_id':name,'label':display_name(name),
                     'provider_name':PROVIDER_NAMES[provider],'price_kind':'free','available':True,'integrated':False,
                     'task_operations':['speech' if task_name=='speech' else 'transcribe'],'capabilities':{'audio':True,'file_upload':True,'image_generation':False}}))
    for model in models:
        info = model['cavren']
        for cap in TESTED_INPUTS.get(info.get('route_id'), ()):
            info.setdefault('capabilities', {})[cap] = True
        model.setdefault('info', {}).setdefault('meta', {})['capabilities'] = info.get('capabilities', {})
        info=model['cavren']; kind='speech' if info.get('task_operations')==['speech'] else 'transcribe' if info.get('task_operations')==['transcribe'] else 'image' if info.get('capabilities',{}).get('image_generation') else 'text'
        record=model_evidence(model['id'],kind)
        info['validation']={'status':record.get('status','not_tested'),'free_verified':verified(model['id'],kind),
                            'mean_seconds':record.get('mean_seconds'),'date':record.get('verified_at')}
        if info.get('provider') in PAID_PROVIDERS:
            info['price_kind'] = 'paid'
        elif info['validation']['free_verified'] and record.get('safety') in ('community_kudos','configured_trial','configured_free_plan','documented_free_model','zero_price_cap'):
            info['price_kind']='free'
    # Documented future choices remain visible even without an account catalogue.
    # They cannot generate until live discovery replaces them with accessible entries.
    reserved = {
        'anthropic': (('claude-fable-5-1', 'claude-opus-5-5', 'claude-sonnet-5-5', 'claude-haiku-5-5'),
                      'https://platform.claude.com/docs/en/models/overview'),
        'xai': (('grok-4.7',), 'https://docs.x.ai/developers/models'),
    }
    for provider, (names, source) in reserved.items():
        if any(m['cavren'].get('provider') == provider for m in models):
            continue
        for name in names:
            model = public_model(provider, {'id': name})
            model['cavren'].update(available=False, catalog_source='documentation', documentation_url=source,
                                  usage_label='Reservado · configure a chave e o saldo para consultar o catálogo')
            models.append(model)
    auto=next((m for m in models if m['id']=='cavren:auto'),None)
    if auto:
        caps = auto['cavren'].setdefault('capabilities', {})
        for cap in ('vision', 'pdf', 'audio', 'video'):
            caps[cap] = any(cap in TESTED_INPUTS.get(m['cavren'].get('route_id'), ())
                            and m['cavren'].get('price_kind') == 'free' and verified(m['id'], 'text') for m in models if m['id'] != 'cavren:auto')
        auto.setdefault('info', {}).setdefault('meta', {})['capabilities'] = caps
    if auto and any('transcribe' in m['cavren'].get('task_operations',[]) for m in models):
        auto['cavren']['capabilities']['audio']=True
        auto['info']['meta']['capabilities']['audio']=True
    return models


def _refresh_catalog():
    global _catalog, _updated
    with LOCK:
        previous = {m['id']: m for m in (_catalog or [])}
        try:
            old_statuses = json.loads((STATE / 'models.json').read_text()).get('providers', {})
        except (OSError, ValueError, AttributeError):
            old_statuses = {}
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
                    'label': display_name(item['model_id']),
                    'provider_name': PROVIDER_NAMES.get(item['provider'], item['provider']),
                    'integrated': True,
                    'context_window': definition.context_window,
                    'output_limit': definition.output_limit,
                    'capabilities': caps,
                },
            )
        providers = {
            name: config
            for name, config in settings.providers.items()
            if config.api_key and (name != 'cloudflare' or config.account_id)
        }
        statuses = {}
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {name: pool.submit(discover, name, config) for name, config in providers.items()}
            for name, future in futures.items():
                models, statuses[name] = future.result()
                # A timeout, lost network or rejected catalogue does not remove
                # saved models. Generation still validates credentials and cost.
                if not statuses[name].get('connected'):
                    models = [m for m in previous.values() if m['cavren'].get('provider') == name]
                for model in models:
                    if model['id'] not in entries or model['cavren'].get('image_only'):
                        entries[model['id']] = model
        # Wallet readiness is separate from catalogue availability. Preserve
        # existing metadata when login has not made credentials readable yet.
        for name in old_statuses.keys() - providers.keys():
            statuses[name] = {**old_statuses[name], 'connected': None, 'status': 'vault_unavailable'}
            for model in previous.values():
                if model['cavren'].get('provider') == name:
                    entries.setdefault(model['id'], model)
        for cap in ('vision', 'video', 'audio', 'pdf'):
            auto_caps[cap] = any(m['cavren'].get('price_kind') == 'free' and m['cavren']['capabilities'].get(cap) for m in entries.values() if m['id'] != 'cavren:auto')
        _catalog = [
            entries.pop('cavren:auto'),
            *sorted(entries.values(), key=lambda m: (m['cavren'].get('provider', ''), m['cavren']['label'].casefold())),
        ]
        _updated = time.time()
        STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
        from integration.auren_settings import atomic_json
        atomic_json(STATE / 'models.json', {'models': _catalog, 'providers': statuses, 'updated': _updated})
        return validated_catalog(_catalog)


def _catalog_background():
    global _refreshing
    try:
        _refresh_catalog()
    except (OSError, ValueError, TypeError):
        # The last complete snapshot remains usable; no secret or raw error log.
        pass
    finally:
        with LOCK:
            _refreshing = False


def catalog(refresh=False):
    """Serve the local snapshot first; external discovery never blocks opening."""
    global _catalog, _updated, _refreshing, _attempted
    # The background worker holds LOCK while publishing. Fast reads deliberately
    # use the immutable list reference without waiting for provider requests.
    if _catalog is None:
        with LOCK:
            if _catalog is None:
                try:
                    data = json.loads((STATE / 'models.json').read_text())
                    saved = data['models']
                    if not isinstance(saved, list) or not saved: raise ValueError()
                    _catalog = saved
                    _updated = float(data.get('updated', 0))
                except (OSError, ValueError, KeyError, TypeError):
                    _catalog = [model_entry('cavren:auto', {'label': 'Automático', 'available': True,
                                'price_kind': 'free', 'integrated': True, 'capabilities': capabilities('', {}, '')})]
    if refresh:
        return _refresh_catalog()
    now = time.time()
    if now - _updated >= 300 and now - _attempted >= 15 and not _refreshing:
        # Do not wait on a refresh already holding LOCK.
        if LOCK.acquire(blocking=False):
            try:
                if not _refreshing:
                    _refreshing = True
                    _attempted = now
                    threading.Thread(target=_catalog_background, name='auren-catalog', daemon=True).start()
            finally:
                LOCK.release()
    return validated_catalog(list(_catalog))


def cached_model(id):
    try:
        model = next((m for m in validated_catalog(json.loads((STATE / 'models.json').read_text())['models']) if m['id'] == id), None)
        if model:
            info = model['cavren']
            if not deepseek_allowed(
                info.get('provider', ''), info.get('model_id', id), info.get('price_kind') == 'free'
            ):
                return None
        return validated_catalog([model])[0] if model else None
    except (FileNotFoundError, ValueError, KeyError):
        return None
