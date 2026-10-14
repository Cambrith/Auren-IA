"""Two real streaming samples for each mode's primary, no model fallback."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dataclasses import replace
from datetime import datetime,timezone
import json,time
import httpx
from cavren.models import Message
from integration.lunvri_connections import connection_settings,STATE
from integration.auren_tasks import recommended
from integration.lunvri_manual import PreparedChatProvider
from integration.auren_modes import specialize


def main():
 settings=connection_settings();path=STATE/'stream_mode_probes_2026-10-13.json'
 data={'records':{}}
 for mode in ('ether','impeto','insight','arquiteto'):
  id=recommended('chat',mode)
  if not id:continue
  provider,name=id.removeprefix('cavren:').split(':',1);cfg=settings.providers.get(provider)
  if not cfg or not cfg.api_key:continue
  samples=[]
  for index in range(2):
   start=time.monotonic();ttft=None;answer='';completed=False;row={'date':datetime.now(timezone.utc).isoformat()}
   try:
    tuned=replace(settings,max_tokens=1024,timeout=30,retries=0)
    messages=[Message(m['role'],m['content']) for m in specialize([{'role':'user','content':'Responda apenas o resultado de 17 × 23.'}],mode,'chat')]
    with httpx.Client(trust_env=False) as client:
     for event in PreparedChatProvider(replace(cfg,model=name),tuned,client,free_only=True).stream(messages,trace_id='synthetic-stream-probe',generation_id='synthetic-stream-probe'):
      value=event.to_dict()
      if value['type']=='generation.delta':
       answer+=value.get('text','')
       if ttft is None and value.get('text','').strip():ttft=time.monotonic()-start
      elif value['type']=='generation.completed':completed=True
      elif value['type']=='generation.error':raise RuntimeError(value.get('code','stream_error'))
    row.update(ok=completed and '391' in answer,code='ok' if completed and '391' in answer else 'stream_check_failed')
   except Exception as error:row.update(ok=False,code=getattr(error,'code',type(error).__name__))
   row.update(seconds=round(time.monotonic()-start,3),first_text_seconds=round(ttft,3) if ttft is not None else None)
   samples.append(row);print(mode,id,index+1,row['code'],row['seconds'],flush=True);time.sleep(3)
  data['records'][mode]={'id':id,'samples':samples}
  tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.chmod(0o600);tmp.replace(path)

if __name__=='__main__':main()
