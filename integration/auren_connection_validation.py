"""Bounded official connection probes. Persist only an allowlisted result, never HTTP bodies."""
import json
import re
from datetime import datetime, timezone
import httpx
from integration.auren_connection_registry import CONNECTIONS
from integration.auren_credentials import AurenVault, LOCK

REASONS = {
 'ok':'Consulta autenticada concluída; não confirma capacidade de geração ou saldo.',
 'missing_credential':'Pendente: credencial não cadastrada.',
 'rotation_required':'Pendente: aguarda credencial rotacionada.',
 'missing_account_id':'Pendente: informe o identificador da conta Cloudflare.',
 'missing_region':'Pendente: informe a região AWS em que a chave foi emitida.',
 'oauth_required':'Pendente: configure a Redirect URL e conclua a autorização OAuth no Canva.',
 'vault_unavailable':'Pendente: cofre indisponível.',
 'auth_error':'Falha: credencial ou permissão recusada pelo serviço.',
 'rate_limit':'Falha: limite de requisições do serviço.',
 'unavailable':'Falha: serviço ou rede indisponível.',
 'endpoint':'Incompatibilidade de endpoint; autenticação não confirmada.',
 'public_catalog':'Pendente: catálogo público acessível; autenticação não confirmada.',
 'invalid_response':'Falha: resposta incompatível com o contrato esperado.',
 'bedrock_runtime':'Pendente: chave Bearer do Bedrock requer endpoint regional de runtime e modelo autorizado.',
 'account_blocked':'Falha: chave desativada ou conta/equipe bloqueada no painel do provedor.',
 'credit_required':'Falha: o provedor exige saldo ou liberação de cobrança.',
 'inference_ok':'Inferência mínima autenticada concluída; não confirma todos os modelos ou tarefas.',
 'account_ok':'Conta autenticada; disponibilidade de inferência não comprovada.',
 'inference_not_run':'Pendente: comprovação exige inferência; nenhuma operação com consumo foi autorizada nesta rodada.',
 'future_credentials':'Reservado para ativação futura; configuração depende do painel do provedor.',
}

# Only these documented models may be used for bounded connection checks.
# Select a currently listed ID before making one request, without retries/fallback generations.
PROBE_MODELS = {
 'nvidia': ('nvidia/nemotron-3-embed-1b', 'nvidia/llama-nemotron-embed-1b-v2'),
 'ollama': ('gemma4:31b',),
}


def response_payload(response):
    """Discard all server content on error. Never include it in an exception/result."""
    code = response.status_code
    if code in (401,403,498): return None, ('failed','auth_error')
    if code == 402: return None, ('failed','credit_required')
    if code == 429: return None, ('failed','rate_limit')
    if code in (404,405,410): return None, ('incompatible','endpoint')
    if not 200 <= code < 300: return None, ('failed','unavailable')
    try: payload = response.json()
    except ValueError: return None, ('failed','invalid_response')
    if not isinstance(payload,(dict,list)) or (isinstance(payload,dict) and (payload.get('error') or payload.get('success') is False)):
        return None, ('failed','invalid_response')
    return payload, None


def embedding_received(payload):
    if not isinstance(payload,dict): return False
    rows = payload.get('data')
    if not isinstance(rows,list) or not rows or not isinstance(rows[0],dict): return False
    vector = rows[0].get('embedding')
    return isinstance(vector,list) and bool(vector) and all(type(v) in (int,float) for v in vector)


def bounded_inference(provider, key, client):
    spec = CONNECTIONS[provider]
    headers = headers_for(spec,key)
    payload,error = response_payload(client.get(spec.endpoint,headers=headers))
    if error: return error
    rows = payload.get('data' if provider=='nvidia' else 'models') if isinstance(payload,dict) else None
    if not isinstance(rows,list): return ('failed','invalid_response')
    names = {row.get('id' if provider=='nvidia' else 'name') for row in rows
             if isinstance(row,dict) and isinstance(row.get('id' if provider=='nvidia' else 'name'),str)}
    model = next((name for name in PROBE_MODELS[provider] if name in names),None)
    if not model: return ('incompatible','endpoint')
    if provider=='nvidia':
        response = client.post('https://integrate.api.nvidia.com/v1/embeddings',headers=headers,
            json={'input':['test'],'model':model,'input_type':'query','encoding_format':'float','truncate':'NONE'})
    else:
        response = client.post('https://ollama.com/v1/chat/completions',headers=headers,
            json={'model':model,'messages':[{'role':'user','content':'Hi'}],'max_tokens':1,'stream':False})
    payload,error = response_payload(response)
    if error: return error
    if provider=='nvidia': valid = embedding_received(payload)
    else:
        choices = payload.get('choices') if isinstance(payload,dict) else None
        first = choices[0] if isinstance(choices,list) and choices else None
        message = first.get('message') if isinstance(first,dict) else None
        valid = isinstance(message,dict) and isinstance(message.get('content'),str) and bool(message['content'].strip())
    return ('success','inference_ok') if valid else ('failed','invalid_response')

def validation_results():
    from integration.auren_settings import STATE
    try:
        data = json.loads((STATE / 'connection_checks.json').read_text())
        return {id: value for id, value in data.items() if id in CONNECTIONS and isinstance(value, dict)
                and value.get('reason') in REASONS and value.get('status') in ('success','failed','pending','incompatible')}
    except (OSError, ValueError, AttributeError): return {}


def invalidate(provider):
    from integration.auren_settings import STATE, atomic_json
    with LOCK:
        checks = validation_results()
        if provider in checks:
            checks.pop(provider)
            atomic_json(STATE / 'connection_checks.json', checks)


def headers_for(spec, key):
    if spec.auth == 'anthropic': return {'x-api-key': key, 'anthropic-version':'2023-06-01'}
    if spec.auth == 'cartesia': return {'Authorization':'Bearer '+key, 'Cartesia-Version':'2026-08-14'}
    if spec.auth in ('apikey','xi-api-key','x-goog-api-key'): return {spec.auth:key}
    prefix = {'raw':'','token':'Token ','Key':'Key '}.get(spec.auth,'Bearer ')
    return {'Authorization':prefix+key}


def probe(provider, values, client, allow_inference=False):
    """values must come from the vault or an explicitly confirmed rotated inventory."""
    spec = CONNECTIONS[provider]
    key = values.get('access_token' if spec.kind == 'oauth' else 'key')
    if not key: return ('pending','oauth_required' if spec.kind == 'oauth' else 'missing_credential')
    if provider in PROBE_MODELS and allow_inference: return bounded_inference(provider,key,client)
    url = 'https://api.voyageai.com/v1/files?limit=1' if provider=='voyage' and not allow_inference else spec.endpoint
    if provider == 'bedrock':
        region = values.get('region','')
        if not re.fullmatch(r'[a-z]{2}(?:-[a-z]+)+-\d',region): return ('pending','missing_region')
        from integration.auren_bedrock import catalogue_url
        url = catalogue_url(values)
    if provider == 'cloudflare':
        account = values.get('account_id','')
        if not re.fullmatch(r'[a-fA-F0-9]{32}',account): return ('pending','missing_account_id')
        url = url.format(account_id=account)
    headers = headers_for(spec,key)
    if provider == 'voyage' and allow_inference:
        response = client.post(url, headers=headers, json={'input':['test'],'model':'voyage-4-lite','input_type':'query'})
    else:
        response = client.get(url, headers=headers)
    payload,error = response_payload(response)
    if error: return error
    if provider == 'voyage':
        valid = embedding_received(payload) if allow_inference else isinstance(payload,dict) and payload.get('object')=='list' and isinstance(payload.get('data'),list)
        if not valid: return ('failed','invalid_response')
    if provider == 'xai':
        flags = ('api_key_blocked','api_key_disabled','team_blocked')
        if not isinstance(payload,dict) or any(type(payload.get(k)) is not bool for k in flags) or not isinstance(payload.get('acls'),list):
            return ('failed','invalid_response')
        if any(payload[k] for k in flags): return ('failed','account_blocked')
    if provider in ('novita','hyperbolic','bedrock'):
        field = {'novita':'availableBalance','hyperbolic':'balanceCents','bedrock':'data' if 'bedrock-mantle.' in url else 'modelSummaries'}[provider]
        value = payload.get(field) if isinstance(payload,dict) else None
        valid = isinstance(value,list) if provider=='bedrock' else type(value) in (int,float) if provider=='hyperbolic' else isinstance(value,str) and bool(re.fullmatch(r'-?\d+(?:\.\d+)?',value))
        if not valid: return ('failed','invalid_response')
    if provider=='cloudflare' and (not isinstance(payload,dict) or payload.get('success') is not True or not isinstance(payload.get('result'),list)):
        return ('failed','invalid_response')
    # Many catalogs ignore authentication. A successful public GET is not key validation.
    if provider in {'cerebras','deepinfra','fireworks','novita','hyperbolic','bedrock','xai','fal','zai','nvidia','ollama'} or provider=='voyage' and not allow_inference:
        control = client.get(url, headers=headers_for(spec,'auren-invalid-credential-control'))
        if 200 <= control.status_code < 300: return ('pending','public_catalog')
        if control.status_code not in (401,403,498): return ('pending','public_catalog')
    return ('success','account_ok' if provider=='hyperbolic' else 'ok')


def validate_connection(provider, backend=None, values=None, persist=True, rotated=True, allow_inference=False):
    if not isinstance(provider,str) or provider not in CONNECTIONS: raise ValueError('Conexão inválida.')
    spec = CONNECTIONS[provider]
    if values is None and rotated:
        from integration.auren_settings import STATE
        try: rotated = bool(json.loads((STATE/'provider_policy.json').read_text()).get('connection_credentials_updated',{}).get(provider))
        except (OSError,ValueError,AttributeError): rotated = False
    try:
        from integration.auren_settings import STATE
        try:rule=json.loads((STATE/'provider_policy.json').read_text()).get('provider_availability',{}).get(provider,{})
        except (OSError,ValueError,AttributeError):rule={}
        if rule.get('disabled') is True and rule.get('reason') in ('future_credentials','account_blocked'):
            reason=rule['reason'];status='pending' if reason=='future_credentials' else 'failed'
        elif not rotated: status,reason = 'pending','rotation_required'
        else:
            if values is None:
                vault = backend or AurenVault()
                values = {'key':vault.get(spec.key), **{f.id:vault.get(f.vault) for f in spec.extra}}
                if spec.kind == 'oauth':
                    from integration.auren_canva_oauth import access_token
                    values['access_token'] = access_token(vault)
            with httpx.Client(timeout=15, trust_env=False, follow_redirects=False) as client:
                status,reason = probe(provider, values, client, allow_inference=allow_inference)
    except OSError: status,reason = 'pending','vault_unavailable'
    except (httpx.HTTPError,ValueError,TypeError,KeyError,IndexError): status,reason = 'failed','unavailable'
    result = {'status':status,'reason':reason,'message':REASONS[reason],'checked_at':datetime.now(timezone.utc).isoformat()}
    if persist:
        from integration.auren_settings import STATE, atomic_json
        with LOCK:
            checks = validation_results(); checks[provider] = result
            atomic_json(STATE / 'connection_checks.json', checks)
    return result
