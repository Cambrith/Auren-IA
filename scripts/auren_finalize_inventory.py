"""Normalize the private inventory after verified vault import. Read-only provider checks only."""
import argparse
import hashlib
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.auren_connection_inventory import parse_inventory,resolve_references,configured_fields
from integration.auren_connection_registry import CONNECTIONS,SERVICE_TYPES

BASE_URLS={
 'aihorde':'https://aihorde.net/api/v2','bedrock':'https://bedrock-runtime.sa-east-1.amazonaws.com/openai/v1',
 'anthropic':'https://api.anthropic.com/v1','assemblyai':'https://api.assemblyai.com/v2',
 'canva':'https://api.canva.com/rest/v1','cartesia':'https://api.cartesia.ai',
 'cerebras':'https://api.cerebras.ai/v1','cloudflare':'https://api.cloudflare.com/client/v4',
 'cohere':'https://api.cohere.com/v2','deepgram':'https://api.deepgram.com/v1',
 'deepinfra':'https://api.deepinfra.com/v1/openai','deepseek':'https://api.deepseek.com/v1',
 'elevenlabs':'https://api.elevenlabs.io/v1','fal':'https://api.fal.ai/v1',
 'fireworks':'https://api.fireworks.ai/inference/v1','gemini':'https://generativelanguage.googleapis.com/v1beta',
 'groq':'https://api.groq.com/openai/v1','huggingface':'https://router.huggingface.co/v1',
 'hyperbolic':'https://api.hyperbolic.ai/v2','mistral':'https://api.mistral.ai/v1',
 'nvidia':'https://integrate.api.nvidia.com/v1','novita':'https://api.novita.ai/v3/openai',
 'ollama':'https://ollama.com','openai':'https://api.openai.com/v1','openrouter':'https://openrouter.ai/api/v1',
 'replicate':'https://api.replicate.com/v1','stability':'https://api.stability.ai',
 'voyage':'https://api.voyageai.com/v1','xai':'https://api.x.ai/v1','zai':'https://api.z.ai/api/paas/v4',
}

def auth_label(id):
    auth=CONNECTIONS[id].auth
    return {'oauth':'OAuth 2.0 Authorization Code + PKCE S256; tokens no cofre',
      'raw':'Authorization com chave direta','anthropic':'x-api-key e anthropic-version',
      'cartesia':'Authorization Bearer e Cartesia-Version 2026-08-14',
      'apikey':'apikey','xi-api-key':'xi-api-key','x-goog-api-key':'x-goog-api-key',
      'token':'Authorization Token','Key':'Authorization Key'}.get(auth,'Authorization Bearer')

def render_document(values,results,vault,archive):
    lines=['# Inventário de provedores — Auren','','Segredos preservados no cofre Auren/KWallet. As referências abaixo não contêm valores de chaves.',
           'Este documento é uma fonte de importação e organização; o aplicativo lê as credenciais do cofre.',
           'Registro original preservado com segurança: cofre://'+archive,
           'Testes desta revisão: somente operações sem geração e sem habilitar faturamento.','']
    for id in sorted(CONNECTIONS,key=lambda id:CONNECTIONS[id].name.casefold()):
        spec=CONNECTIONS[id];row=results[id];v=values.get(id,{})
        usable=bool(v.get('key')) or id=='xai' and bool(vault.get(spec.key))
        label='OAuth client secret' if id=='canva' else 'Standard API Key (voz/STT)' if id=='cartesia' else 'Chave de inferência; ativação futura' if id=='xai' else 'Bedrock API Key (Bearer)' if id=='bedrock' else 'API Key/token'
        lines += ['## '+spec.name,'','Tipo de serviço: '+SERVICE_TYPES[id],
                  'Tipo de credencial: '+label,
                  'Credencial: '+('cofre://'+spec.key if usable else 'Ainda não fornecida; preparado para ativação futura'),
                  'Autenticação: '+auth_label(id),'Base URL: '+v.get('base_url',BASE_URLS[id])]
        for field in spec.extra:
            if field.id=='base_url':continue
            value=v.get(field.id) or vault.get(field.vault)
            key={'region':'Região','redirect_uri':'Redirect URL','account_id':'Account ID','client_id':'Client ID'}[field.id]
            lines.append(key+': '+('cofre://'+field.vault if field.id in ('account_id','client_id') and value else value or 'A configurar'))
        if id=='canva':lines.append('Escopo solicitado: profile:read; consentimento do titular necessário')
        if id=='xai':lines.append('Chave tipo Cursor: rejeitada pela API pública conforme teste do titular; não utilizar como chave de inferência. Nenhum valor alternativo foi fornecido nesta revisão.')
        lines+=['Situação: '+row['message'],'Última verificação: '+str(row.get('checked_at') or 'Condição informada pelo titular'),
                'Documentação oficial: '+spec.docs,'']
        if row.get('previous_validation'):lines+=['Evidência anterior: '+row['previous_validation']['message']+' Data: '+row['previous_validation']['checked_at'],'']
    return '\n'.join(lines)+'\n'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--document',required=True,type=Path)
    parser.add_argument('--rotated-confirmed',action='store_true')
    args=parser.parse_args()
    if not args.rotated_confirmed:parser.error('Confirme que o inventário contém as credenciais atuais.')
    logging.disable(logging.CRITICAL)
    from integration.auren_credentials import AurenVault
    from integration.auren_settings import STATE,save_connection,atomic_json
    from integration.auren_connection_validation import validate_connection,validation_results
    vault=AurenVault();original=args.document.read_text()
    archive='AUREN_INVENTORY_ARCHIVE_'+hashlib.sha256(original.encode()).hexdigest()[:16].upper()
    vault.set(archive,original)
    if vault.get(archive)!=original.rstrip('\n'):raise OSError('A cópia segura do inventário não foi confirmada.')
    values=resolve_references(original,parse_inventory(original),vault)
    previous=validation_results();results={}
    try:policy=json.loads((STATE/'provider_policy.json').read_text())
    except (OSError,ValueError):policy={}
    for id,spec in CONNECTIONS.items():
        v=configured_fields(id,values.get(id,{}),vault)
        names={'key':spec.key,**{f.id:f.vault for f in spec.extra}}
        v={k:value for k,value in v.items() if k in names}
        unchanged=bool(v.get('key')) and v['key']==vault.get(spec.key)
        changes={k:value for k,value in v.items() if value!=vault.get(names[k])}
        if changes:save_connection(id,changes,backend=vault,free_trial=policy.get(id+'_trial') is True)
        if any(vault.get(names[k])!=value for k,value in v.items()):raise OSError('A importação não foi confirmada no cofre.')
        if id=='canva':
            from integration.auren_canva_oauth import access_token
            v['access_token']=access_token(vault)
        result=validate_connection(id,values=v,allow_inference=False)
        if unchanged and result['status']=='pending' and previous.get(id,{}).get('status')=='success':
            result['previous_validation']=previous[id]
        results[id]=result;values[id]=v
        print(json.dumps({'provider':id,'status':result['status'],'reason':result['reason']}),flush=True)
    root=Path(__file__).resolve().parents[1]
    atomic_json(root/'reports/auren-provider-final-review-2026-10-15.json',results)
    document=render_document(values,results,vault,archive)
    fd,temporary=tempfile.mkstemp(dir=args.document.parent,prefix='.auren-inventory-')
    try:
        with os.fdopen(fd,'w') as out:out.write(document);out.flush();os.fsync(out.fileno())
        os.replace(temporary,args.document)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)
    print(json.dumps({'document_updated':True,'providers':len(results),'archive':'vault_only','paid_inference':False}))

if __name__=='__main__':
    try:main()
    except Exception:
        print('Não foi possível concluir a revisão segura; nenhum conteúdo secreto será exibido.',file=sys.stderr)
        sys.exit(1)
