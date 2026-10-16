"""Explicit, one-shot vault import and sanitized probes. Never prints inventory contents."""
import argparse
import json
import logging
import re
import sys
import unicodedata
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from integration.auren_connection_registry import CONNECTIONS


def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',value.casefold()) if not unicodedata.combining(c))

ALIASES = {
 'aihorde':('ai horde',), 'bedrock':('bedrock',),'anthropic':('anthropic','claude'),
 'assemblyai':('assemblyai','assembly ai'),'canva':('canva',),'cartesia':('cartesia',),
 'cerebras':('cerebras',),'cloudflare':('cloudflare','cloudfare'),'cohere':('cohere',),
 'deepgram':('deepgram',),'deepinfra':('deepinfra',),'deepseek':('deepseek',),
 'elevenlabs':('elevenlabs',),'fal':('fal','fal.ai'),'fireworks':('fireworks',),
 'gemini':('gemini',),'groq':('groq','groqcloud'),'huggingface':('hugging face','huggingface'),
 'hyperbolic':('hyperbolic',),'mistral':('mistral',),'nvidia':('nvidia',),
 'novita':('novita',),'ollama':('ollama',),'openai':('openai','chatgpt'),
 'openrouter':('openrouter',),'replicate':('replicate',),'stability':('stability',),
 'voyage':('voyage',),'xai':('xai','x.ai'),'zai':('z.ai',),
}


def parse_inventory(text):
    """Heading/label parsing; values remain in memory and never appear in diagnostics."""
    inventory = {}
    current = None
    for raw in text.splitlines():
        line=raw.strip().strip('*# ').strip()
        lowered=normalize(line)
        if ':' not in line and '=' not in line and len(line.split()) <= 6:
            matched=[id for id,aliases in ALIASES.items() if any(re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',lowered) for alias in aliases)]
            if len(matched)==1:
                current=matched[0];inventory.setdefault(current,{})
            continue
        if not current: continue
        if ':' in line: label,value=line.split(':',1)
        elif '=' in line: label,value=line.split('=',1)
        else: continue
        label=normalize(label).strip('-* ')
        field = {'client id':'client_id','client secret':'key','redirect url':'redirect_uri','redirect uri':'redirect_uri',
                 'account id':'account_id','id da conta':'account_id','identificador da conta':'account_id',
                 'regiao':'region','regiao aws':'region','region':'region','base url':'base_url','endpoint':'base_url',
                 'chave de api':'key','chave api':'key','api key':'key','chave':'key','token':'key',
                 'credencial':'key','credencial informada':'key'}.get(label)
        if field is None: continue
        value=value.strip().strip('`\"\'')
        if value.startswith('cofre://'): continue  # Resolved separately, with an exact provider/name check.
        if value and re.fullmatch(r'[!-~]+',value) and (field != 'key' or len(value)>=8):
            inventory[current][field]=value
    return inventory


def resolve_references(text, inventory, vault):
    """A document reference can only name its own provider's credential, never an arbitrary secret."""
    result={provider:dict(values) for provider,values in inventory.items()}
    current=None
    for raw in text.splitlines():
        line=raw.strip().strip('*# ').strip()
        if ':' not in line and '=' not in line and len(line.split())<=6:
            found=[id for id,aliases in ALIASES.items() if any(re.search(r'(?<!\w)'+re.escape(a)+r'(?!\w)',normalize(line)) for a in aliases)]
            current=found[0] if len(found)==1 else current
        if current and ':' in line:
            label,reference=line.split(':',1);reference=reference.strip()
            field={'credencial':'key','client id':'client_id','account id':'account_id'}.get(normalize(label))
            if not field or not reference.startswith('cofre://'):continue
            names={'key':CONNECTIONS[current].key,**{f.id:f.vault for f in CONNECTIONS[current].extra}}
            name=reference.removeprefix('cofre://')
            if name!=names.get(field): raise ValueError('Referência de credencial incompatível com o provedor.')
            value=vault.get(name)
            if value: result.setdefault(current,{})[field]=value
    return result


def configured_fields(provider, values, vault):
    """Reuse only existing configuration fields; never supply a missing API key/token."""
    result = dict(values)
    for field in CONNECTIONS[provider].extra:
        if field.id in ('account_id','region','redirect_uri') and not result.get(field.id):
            value = vault.get(field.vault)
            if value: result[field.id] = value
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--document',type=Path,required=True)
    parser.add_argument('--rotated-confirmed',action='store_true')
    parser.add_argument('--import-vault',action='store_true')
    parser.add_argument('--validate',action='store_true')
    parser.add_argument('--use-configured-fields',action='store_true',help='Usar conta, região e Redirect URL já configuradas no cofre; nunca completar chaves ausentes.')
    args=parser.parse_args()
    if (args.import_vault or args.validate or args.use_configured_fields) and not args.rotated_confirmed:
        parser.error('Confirme a rotação antes de importar ou validar.')
    logging.disable(logging.CRITICAL)
    document=args.document.read_text()
    inventory=parse_inventory(document)
    if not args.import_vault and not args.validate:
        print(json.dumps({id:sorted(values) for id,values in inventory.items()},ensure_ascii=False));return
    from integration.auren_settings import STATE, save_connection
    from integration.auren_credentials import AurenVault
    from integration.auren_connection_validation import validate_connection
    vault = AurenVault() if args.import_vault or args.use_configured_fields or 'cofre://' in document else None
    if 'cofre://' in document: inventory=resolve_references(document,inventory,vault)
    try: policy=json.loads((STATE/'provider_policy.json').read_text())
    except (OSError,ValueError): policy={}
    for id,spec in CONNECTIONS.items():
        values=inventory.get(id,{})
        allowed={'key',*(f.id for f in spec.extra)}
        values={key:value for key,value in values.items() if key in allowed}
        if args.use_configured_fields: values=configured_fields(id,values,vault)
        imported=False
        if args.import_vault and values:
            try:
                names={'key':spec.key,**{f.id:f.vault for f in spec.extra}}
                updates={field:value for field,value in values.items() if vault.get(names[field])!=value}
                if values.get('key') and not policy.get('connection_credentials_updated',{}).get(id): updates['key']=values['key']
                if updates: save_connection(id,updates,backend=vault,free_trial=policy.get(id+'_trial') is True)
                imported=True
            except (OSError,ValueError):
                print(json.dumps({'provider':id,'imported':False,'reason':'vault_or_field_unavailable'}));continue
        if args.validate:
            # API keys come only from the updated document. Optional configured fields contain no key/token.
            result=validate_connection(id,values=values,rotated=args.rotated_confirmed)
            print(json.dumps({'provider':id,'imported':imported,**result},ensure_ascii=False),flush=True)
        else: print(json.dumps({'provider':id,'imported':imported}),flush=True)

if __name__=='__main__':
    try: main()
    except Exception:
        # Exceptions may include source text, URLs or request headers. Never print them.
        print('Não foi possível concluir a leitura segura do inventário.',file=sys.stderr);sys.exit(1)
