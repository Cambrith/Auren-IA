"""Check the Auren transcription adapter against the audited synthetic fixture."""
import json,base64,time,hashlib,re,unicodedata
from pathlib import Path
from integration.auren_transcribe import run
from integration.lunvri_connections import STATE
from auren_curated_probe import atomic,now
P=Path('reports/auren-gemini-groq-2026-10-14-r2')
OUT=Path('reports/auren-groq-transcribe-app-2026-10-14.json')
def main():
 if OUT.exists():raise SystemExit('Do not repeat completed application calls silently.')
 path=STATE/'validation_tasks.json';previous=path.read_bytes();backup=STATE/'scoped-transcribe-before-2026-10-14.json'
 if not backup.exists():backup.write_bytes(previous);backup.chmod(0o600)
 tasks=json.loads(previous);native=json.loads((P/'results.json').read_text())['records'];report={'started_at':now(),'records':{}}
 for model in ('whisper-large-v3','whisper-large-v3-turbo'):
  route='groq:'+model;key='transcribe_groq_'+model
  samples=native.get(route+'::transcribe',{}).get('samples',[])
  if len(samples)<3 or not all(s.get('success') for s in samples):
   report['records'][route]={'real_call':False,'blocker':'Native synthetic transcription did not pass all three samples.'};atomic(OUT,report);continue
  tasks['tasks'][key]={'model':'cavren:'+route,'ok':True,'date':now(),'safety':'configured_free_plan','samples':[{'ok':True,'date':s['at']} for s in samples]};atomic(path,tasks)
  rows=[]
  for index in range(2):
   events=[];start=time.monotonic();row={'date':now(),'operation':'audio/transcriptions','real_call':True,'reported_cost_usd':None}
   try:
    raw=(P/'fixtures/pt.wav').read_bytes();job={'generation_id':'auren-groq-transcribe-app','mode_id':'ether','mode_options':{'manual_route':route},'auren_transcribe_language':'pt','auren_deadline':time.monotonic()+25,'messages':[{'role':'user','content':[{'type':'input_audio','input_audio':{'format':'wav','data':base64.b64encode(raw).decode()}}]}]}
    run(job,None,output=events.append);text=''.join(e.get('text','') for e in events if e.get('type')=='generation.delta');norm=''.join(c for c in unicodedata.normalize('NFD',text.lower()) if not unicodedata.combining(c));wanted=('auren','pronta','bom','dia');coverage=sum(w in norm for w in wanted)/len(wanted)
    row.update(ok=coverage>=.75 and any(e.get('type')=='generation.completed' for e in events),semantic_check=True,token_coverage=coverage,response_sha256=hashlib.sha256(text.encode()).hexdigest())
   except Exception as e:row.update(ok=False,code=getattr(e,'code',type(e).__name__))
   row['seconds']=round(time.monotonic()-start,3);rows.append(row);report['records'][route]={'samples':rows};atomic(OUT,report)
  tasks['tasks'][key].update(ok=all(r['ok'] for r in rows),date=now(),samples=rows,seconds=sum(r['seconds'] for r in rows)/len(rows));atomic(path,tasks);print(route,all(r['ok'] for r in rows),flush=True)
 report['finished_at']=now();atomic(OUT,report)
if __name__=='__main__':main()
