"""Public connection state, persistent preferences, secure credential updates."""
import json
import os
import re
import tempfile
from pathlib import Path
from integration.lunvri_connections import STATE, PROVIDER_NAMES, catalog, connection_settings
from cavren.credentials import SecretServiceBackend

PROVIDER_KEYS = {'openai':'OPENAI_API_KEY','anthropic':'ANTHROPIC_API_KEY','gemini':'GEMINI_API_KEY','groq':'GROQ_API_KEY','mistral':'MISTRAL_API_KEY',
 'openrouter':'OPENROUTER_API_KEY','cloudflare':'CLOUDFLARE_API_TOKEN','cohere':'COHERE_API_KEY',
 'nvidia':'NVIDIA_API_KEY','ollama':'OLLAMA_API_KEY','zai':'ZAI_API_KEY','aihorde':'AI_HORDE_API_KEY'}


DEFAULT_PREFERENCES = {'image_model_id':'','image_width':512,'image_height':512,'image_steps':20}

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
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)


def save_preferences(values):
    existing=preferences()
    if set(values)-{'image_model_id','image_width','image_height','image_steps'}:
        raise ValueError('Preferência desconhecida.')
    result={**existing,**values}
    if result.get('image_model_id'):
        model=next((m for m in catalog() if m['id']==result['image_model_id']),None)
        if not model or not model['cavren']['capabilities'].get('image_generation'):
            raise ValueError('Escolha um modelo de geração de imagens disponível.')
    for key in ('image_width','image_height'):
        if type(result[key]) is not int or result[key] not in (512,768,1024): raise ValueError('Dimensão inválida.')
    if type(result['image_steps']) is not int or not 5<=result['image_steps']<=50: raise ValueError('Use entre 5 e 50 etapas.')
    atomic_json(STATE/'auren_preferences.json', result)
    return result


def public_state(refresh=False):
    models=catalog(refresh=refresh)
    snapshot=json.loads((STATE/'models.json').read_text())
    settings=connection_settings()
    connections=[]
    for provider,label in PROVIDER_NAMES.items():
        cfg=settings.providers.get(provider)
        status=snapshot.get('providers',{}).get(provider,{})
        configured=bool(cfg and cfg.api_key and (provider!='cloudflare' or cfg.account_id))
        code=status.get('status')
        state='unconfigured' if not configured else 'catalog_available' if status.get('connected') else 'configured' if code=='configured' else 'auth_error' if code in (401,403,498) else 'unavailable'
        connections.append({'id':provider,'name':label,'state':state,'count':sum(m['cavren'].get('provider')==provider for m in models),
                            'image_count':sum(m['cavren'].get('provider')==provider and m['cavren']['capabilities'].get('image_generation',False) for m in models)})
    return {'connections':connections,'preferences':preferences(),'updated':snapshot.get('updated'),
            'models':[{'id':m['id'],'name':m['name'],'cavren':m['cavren']} for m in models],
            'version': '0.12.0','local':True}


def save_key(provider,key,backend=None,free_trial=False):
    if not isinstance(provider,str) or provider not in PROVIDER_KEYS or not isinstance(key,str) or not 8<=len(key)<=1000 or not re.fullmatch(r'[!-~]+',key):
        raise ValueError('Provedor ou chave inválidos.')
    vault=backend or SecretServiceBackend()
    name=PROVIDER_KEYS[provider]
    before=vault.get(name)
    try:
        vault.set(name,key)
        if vault.get(name)!=key: raise OSError('Não foi possível confirmar o armazenamento seguro.')
        if provider in ('cohere','nvidia','openai','anthropic'):
            policy_path=STATE/'provider_policy.json'
            try: policy=json.loads(policy_path.read_text())
            except (OSError,ValueError): policy={}
            if provider in ('openai','anthropic'): policy[provider+'_configured']=True
            else: policy[provider+'_trial']=free_trial is True
            atomic_json(policy_path,policy)
    except OSError:
        if before: vault.set(name,before)
        else: vault.delete(name)
        raise
    return {'saved':True}
