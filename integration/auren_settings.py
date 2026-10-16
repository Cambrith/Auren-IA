"""Public connection state, persistent preferences, secure credential updates."""
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from integration.lunvri_connections import STATE, PAID_PROVIDERS, PROVIDER_NAMES, catalog, connection_settings
from integration.auren_credentials import AurenVault, credential_inventory, remember_credentials

from integration.auren_connection_registry import CONNECTIONS, CONNECTION_NAMES, PROVIDER_KEYS, fields
from integration.auren_credentials import LOCK



DEFAULT_PREFERENCES = {'image_model_id':'','image_width':512,'image_height':512,'image_steps':20,'connection_order':[]}

def preferences():
    try:
        data = json.loads((STATE/'auren_preferences.json').read_text())
        return {**DEFAULT_PREFERENCES, **{k:v for k,v in data.items() if k in DEFAULT_PREFERENCES}}
    except (OSError, ValueError, AttributeError):
        return dict(DEFAULT_PREFERENCES)

def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=path.stem+'-', suffix='.tmp')
    try:
        with os.fdopen(fd,'w') as f:
            json.dump(value,f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name,path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if os.path.exists(name): os.unlink(name)


def save_preferences(values):
    with LOCK:
        return _save_preferences(values)

def _save_preferences(values):
    existing=preferences()
    if set(values)-{'image_model_id','image_width','image_height','image_steps','connection_order'}:
        raise ValueError('Preferência desconhecida.')
    result={**existing,**values}
    if 'image_model_id' in values and result.get('image_model_id'):
        model=next((m for m in catalog() if m['id']==result['image_model_id']),None)
        if not model or not model['cavren']['capabilities'].get('image_generation'):
            raise ValueError('Escolha um modelo de geração de imagens disponível.')
    for key in ('image_width','image_height'):
        if type(result[key]) is not int or result[key] not in (512,768,1024): raise ValueError('Dimensão inválida.')
    if type(result['image_steps']) is not int or not 5<=result['image_steps']<=50: raise ValueError('Use entre 5 e 50 etapas.')
    order = result.get('connection_order', [])
    if not isinstance(order, list) or any(not isinstance(id, str) or id not in CONNECTIONS for id in order) or len(set(order)) != len(order):
        raise ValueError('Ordem de conexões inválida.')
    atomic_json(STATE/'auren_preferences.json', result)
    return result


def public_state(refresh=False):
    models=catalog(refresh=refresh)
    try: snapshot=json.loads((STATE/'models.json').read_text())
    except (OSError, ValueError): snapshot={}
    try: settings=connection_settings()
    except OSError: settings=None
    saved_names=credential_inventory()
    connections=[]
    for provider,label in CONNECTION_NAMES.items():
        cfg=settings.providers.get(provider) if settings else None
        status=snapshot.get('providers',{}).get(provider,{})
        configured=bool(cfg and cfg.api_key and (provider!='cloudflare' or cfg.account_id))
        code=status.get('status')
        saved=configured or PROVIDER_KEYS[provider] in saved_names or provider in snapshot.get('providers',{})
        state=('vault_unavailable' if saved else 'unconfigured') if not configured else 'catalog_available' if status.get('connected') else 'configured' if code in ('configured',None,'vault_unavailable') else 'auth_error' if code in (401,403,498) else 'unavailable'
        if provider not in PROVIDER_NAMES:
            saved = PROVIDER_KEYS[provider] in saved_names
            state = 'configured' if saved else 'unconfigured'
        connections.append({'auth_kind': CONNECTIONS[provider].kind, 'fields': fields(provider), 'id':provider,'name':label,'state':state,'credential_saved':saved,'billing_required':provider in PAID_PROVIDERS,'count':sum(m['cavren'].get('provider')==provider and m['cavren'].get('available',True) for m in models),
                            'image_count':sum(m['cavren'].get('provider')==provider and m['cavren']['capabilities'].get('image_generation',False) for m in models)})
    from integration.auren_connection_validation import validation_results
    checks = validation_results()
    try: availability=json.loads((STATE/'provider_policy.json').read_text()).get('provider_availability',{})
    except (OSError,ValueError,AttributeError):availability={}
    for connection in connections:
        from integration.auren_connection_registry import SERVICE_TYPES
        connection['service_type']=SERVICE_TYPES[connection['id']]
        connection['check'] = checks.get(connection['id'])
        rule=availability.get(connection['id'],{})
        if rule.get('disabled') is True:
            from integration.auren_connection_validation import REASONS
            reason=rule.get('reason','account_blocked')
            if reason in REASONS:connection['check']={'status':'pending' if reason=='future_credentials' else 'failed','reason':reason,'message':REASONS[reason],'checked_at':None}
    from integration.auren_tasks import tasks, recommended
    return {'mode_recommendations': {mode:recommended('code' if mode=='arquiteto' else 'chat',mode) for mode in ('ether','impeto','insight','arquiteto')},
            'image_profile_recommendations': {profile:recommended('image', profile=profile) for profile in ('rapid','balanced','detailed')},
            'tasks': tasks(), 'connections':connections,'preferences':preferences(),'updated':snapshot.get('updated'),
            'models':[{'id':m['id'],'name':m['name'],'cavren':m['cavren']} for m in models],
            'version': '0.12.0','local':True}


def save_key(provider,key,backend=None,free_trial=False):
    if not isinstance(provider,str) or provider not in PROVIDER_KEYS or not isinstance(key,str) or not 8<=len(key)<=1000 or not re.fullmatch(r'[!-~]+',key):
        raise ValueError('Provedor ou chave inválidos.')
    vault=backend or AurenVault()
    name=PROVIDER_KEYS[provider]
    before=vault.get(name)
    try:
        vault.set(name,key)
        if vault.get(name)!=key: raise OSError('Não foi possível confirmar o armazenamento seguro.')
        policy_path=STATE/'provider_policy.json'
        try: policy=json.loads(policy_path.read_text())
        except (OSError,ValueError): policy={}
        old_trial=policy.get(provider+'_trial')
        if provider in ('openai','anthropic','deepseek','xai','huggingface'): policy[provider+'_configured']=True
        elif provider in ('cohere','nvidia'): policy[provider+'_trial']=free_trial is True
        if before != key or old_trial != policy.get(provider+'_trial'):
            policy.setdefault('validation_not_before', {})[provider]=datetime.now(timezone.utc).isoformat()
        atomic_json(policy_path,policy)
        remember_credentials({name:key})
    except OSError:
        if before: vault.set(name,before)
        else: vault.delete(name)
        raise
    return {'saved':True}


def save_connection(provider, values, backend=None, free_trial=False):
    """Partial updates keep omitted vault entries. Roll back the whole bundle on failure."""
    if not isinstance(provider,str) or provider not in CONNECTIONS or not isinstance(values, dict):
        raise ValueError('Conexão inválida.')
    spec = CONNECTIONS[provider]
    names = {'key': spec.key, **{f.id: f.vault for f in spec.extra}}
    if set(values) - names.keys(): raise ValueError('Campo desconhecido.')
    updates = {}
    for id, value in values.items():
        if not isinstance(value, str): raise ValueError('Campo inválido.')
        if not value: continue
        if len(value) > 4096 or not re.fullmatch(r'[!-~]+', value): raise ValueError('Campo inválido.')
        if id == 'key' and len(value) < 8: raise ValueError('Chave inválida.')
        if id == 'account_id' and not re.fullmatch(r'[a-fA-F0-9]{32}', value): raise ValueError('Conta inválida.')
        if id == 'region' and not re.fullmatch(r'[a-z]{2}(?:-[a-z]+)+-\d', value): raise ValueError('Região inválida.')
        if id == 'base_url':
            from integration.auren_bedrock import validate_base_url
            validate_base_url(value, values.get('region') or vault_region(backend))
        if id == 'redirect_uri':
            from integration.auren_canva_oauth import redirect_address
            redirect_address(value)
        updates[names[id]] = value
    if not updates: raise ValueError('Preencha ao menos um campo.')
    vault = backend or AurenVault()
    with LOCK:
        token_names = ('CANVA_ACCESS_TOKEN', 'CANVA_REFRESH_TOKEN', 'CANVA_TOKEN_EXPIRES_AT') if provider == 'canva' else ()
        before = {name: vault.get(name) for name in (*updates, *token_names)}
        metadata = {name: (STATE/name).read_bytes() if (STATE/name).exists() else None
                    for name in ('provider_policy.json','credential_inventory.json','connection_checks.json')}
        try:
            for name, value in updates.items():
                if name == spec.key and provider in PROVIDER_NAMES:
                    save_key(provider, value, backend=vault, free_trial=free_trial)
                else:
                    vault.set(name, value)
                if vault.get(name) != value: raise OSError('O cofre não confirmou a gravação.')
            remember_credentials(updates)
            if spec.key in updates:
                try: policy = json.loads((STATE/'provider_policy.json').read_text())
                except (OSError,ValueError): policy = {}
                policy.setdefault('connection_credentials_updated', {})[provider] = datetime.now(timezone.utc).isoformat()
                atomic_json(STATE/'provider_policy.json',policy)
            from integration.auren_connection_validation import invalidate
            invalidate(provider)
            if provider == 'canva':
                for name in token_names:
                    vault.delete(name)
        except OSError:
            for name, value in before.items():
                if value: vault.set(name, value)
                else: vault.delete(name)
            for name, data in metadata.items():
                if data is None: (STATE/name).unlink(missing_ok=True)
                else: atomic_json(STATE/name, json.loads(data))
            raise
    return {'saved': True}


def vault_region(backend=None):
    return (backend or AurenVault()).get('AWS_REGION')
