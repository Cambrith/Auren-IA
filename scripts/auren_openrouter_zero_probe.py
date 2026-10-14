"""Probe every advertised OpenRouter route with server-enforced zero-price limits."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import json,time
from dataclasses import replace
from datetime import datetime,timezone
import httpx
from cavren.models import Message
from integration.lunvri_connections import STATE,connection_settings
from integration.lunvri_manual import PreparedChatProvider


def main():
 path=STATE/'openrouter_zero_probes_2026-10-13.json'
 try:data=json.loads(path.read_text())
 except (OSError,ValueError):data={'records':{}}
 settings=connection_settings();config=settings.providers.get('openrouter')
 if not config or not config.api_key:raise SystemExit('Credencial ausente no cofre.')
 models=[m for m in json.loads((STATE/'models.json').read_text())['models'] if m.get('cavren',{}).get('provider')=='openrouter']
 for index,model in enumerate(models):
  if model['id'] in data['records']:continue
  if model['cavren'].get('image_only') or model['cavren'].get('capabilities',{}).get('image_generation'):
   data['records'][model['id']]={'status':'not_called','code':'image_price_cap_not_integrated'}
  else:
   start=time.monotonic();row={'date':datetime.now(timezone.utc).isoformat(),'status':'called','price_cap':{'prompt':0,'completion':0,'request':0,'image':0}}
   try:
    with httpx.Client(trust_env=False) as client:
     response=PreparedChatProvider(replace(config,model=model['cavren']['model_id']),replace(settings,max_tokens=1024,timeout=20,retries=0),client,free_only=True).generate([Message('user','Responda apenas o resultado de 17 × 23.')],trace_id='zero-price-probe')
    row.update(ok='391' in response.text,code='ok' if '391' in response.text else 'semantic_check_failed')
   except Exception as error:row.update(ok=False,code=getattr(error,'code',type(error).__name__))
   row['seconds']=round(time.monotonic()-start,3);data['records'][model['id']]=row
  temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');temp.chmod(0o600);temp.replace(path)
  print(index+1,len(models),model['cavren']['model_id'],data['records'][model['id']].get('code'),flush=True)
  time.sleep(3)
 print('Todas as rotas OpenRouter verificadas com teto zero.',flush=True)

if __name__=='__main__':main()
