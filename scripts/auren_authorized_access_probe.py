"""One user-authorized access probe for previously blocked OpenRouter routes.

Explicit authorization in the current conversation permits advertised paid routes.
This never enables billing, tops up credits, promotes a route as free, or changes app
confirmation gates. Only synthetic content and allowlisted response metadata persist.
"""
from pathlib import Path
import sys,json,time,threading,concurrent.futures
from dataclasses import replace
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import httpx
from cavren.models import Message
from integration.lunvri_connections import STATE,connection_settings,validated_catalog
from integration.lunvri_manual import PreparedChatProvider,generate_images
LOCK=threading.Lock()

def main():
 path=STATE/'authorized_access_probes_2026-10-13.json'
 try:data=json.loads(path.read_text())
 except (OSError,ValueError):data={'authorization':'User explicitly authorized testing advertised paid models; no billing activation or topup.','records':{}}
 models=validated_catalog(json.loads((STATE/'models.json').read_text())['models'])
 settings=connection_settings();cfg=settings.providers.get('openrouter')
 if not cfg or not cfg.api_key:raise SystemExit('OpenRouter sem credencial disponível no cofre.')
 items=[m for m in models if m.get('cavren',{}).get('provider')=='openrouter' and m['cavren'].get('price_kind')!='free']
 def probe(model):
  info=model['cavren'];kind='image' if info.get('image_only') else 'text';key=kind+':'+model['id']
  with LOCK:
   if key in data['records']:return
  row={'id':model['id'],'provider':'openrouter','model':info['model_id'],'kind':kind,'date':datetime.now(timezone.utc).isoformat(),'advertised_price_kind':info.get('price_kind'),'authorization':'explicit_paid_test','status':'called'}
  statuses=[];limits={};billing={}
  def response_hook(response):
   statuses.append(response.status_code)
   if response.status_code==200 and 'application/json' in response.headers.get('content-type',''):
    try:
     response.read();usage=response.json().get('usage',{})
     if isinstance(usage,dict):
      cost=usage.get('cost')
      if type(cost) in (int,float):billing['reported_cost_usd']=cost
    except (ValueError,TypeError):pass
   for k,v in response.headers.items():
    if k.lower().startswith(('x-ratelimit-limit','x-ratelimit-remaining','x-ratelimit-reset','ratelimit-limit','ratelimit-remaining','ratelimit-reset')):limits[k.lower()]=v[:80]
  start=time.monotonic()
  try:
   with httpx.Client(trust_env=False,event_hooks={'response':[response_hook]}) as client:
    config=replace(cfg,model=info['model_id'])
    if kind=='image':
     files,_=generate_images(client,config,[Message('user','Uma esfera azul sobre fundo branco, sem texto.')],'Uma esfera azul sobre fundo branco, sem texto.',job={'mode_options':{'billing_confirmed':True},'auren_deadline':time.monotonic()+20})
     ok=bool(files)
    else:
     response=PreparedChatProvider(config,replace(settings,max_tokens=512,timeout=20,retries=0),client,free_only=False).generate([Message('user','Responda apenas o resultado de 17 × 23.')],trace_id='authorized-account-access-probe')
     ok='391' in response.text
   row.update(ok=ok,code='ok' if ok else 'semantic_check_failed')
  except Exception as error:row.update(ok=False,code=getattr(error,'code',type(error).__name__))
  row.update(seconds=round(time.monotonic()-start,3),http_status=statuses[-1] if statuses else None,limits=limits,free_proven=False,**billing)
  with LOCK:
   data['records'][key]=row;temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');temporary.chmod(0o600);temporary.replace(path)
   print(len(data['records']),len(items),info['model_id'],row['code'],row['http_status'],flush=True)
  time.sleep(.5)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(probe,items))
 print('Sondagens autorizadas concluídas.',flush=True)
if __name__=='__main__':main()
