"""Real existing worker check of a synthetic PDF on the current Gemini fallback."""
import json,time,base64,subprocess,os,hashlib
from pathlib import Path
from integration.lunvri_bridge import prepare_job,WORKER
from integration.lunvri_connections import credentials_env
from auren_curated_probe import atomic,now
P=Path('reports/auren-gemini-native-app-2026-10-14.json')
def main():
 if P.exists():raise SystemExit('Already recorded; no silent repeats.')
 fixture=Path('reports/auren-gemini-groq-2026-10-14-r2/fixtures/document.pdf').read_bytes()
 row={'at':now(),'provider':'gemini','model':'gemini-3.5-flash-lite','operation':'native_pdf','real_call':True,'reported_cost_usd':None};start=time.monotonic();atomic(P,row)
 try:
  job=prepare_job({'model':'cavren:gemini:gemini-3.5-flash-lite','auren_task':'documents','cavren_mode_id':'insight','auren_mode_manual':True,'max_tokens':1536,'messages':[{'role':'user','content':[{'type':'text','text':'Leia o PDF e responda apenas o identificador e a quantidade de unidades nele.'},{'type':'input_file','input_file':{'mime_type':'application/pdf','data':base64.b64encode(fixture).decode()}}]}]},'auren-gemini-native-app')
  job['auren_deadline']=time.monotonic()+40
  env={**os.environ,**credentials_env(),'CAVREN_TIMEOUT':'35','CAVREN_RETRIES':'0'}
  result=subprocess.run([os.sys.executable,str(WORKER)],input=json.dumps(job),capture_output=True,text=True,env=env,timeout=45)
  events=[json.loads(s) for s in result.stdout.splitlines() if s.startswith('{')];final=next((e.get('response',{}) for e in events if e.get('type')=='generation.completed'),{});text=final.get('text','')
  row.update(ok='PDF-628' in text and '7' in text and final.get('model')=='gemini-3.5-flash-lite',effective_model=final.get('model'),effective_provider=final.get('provider'),response_sha256=hashlib.sha256(text.encode()).hexdigest(),errors=[e.get('code') for e in events if e.get('type')=='generation.error'])
 except Exception as e:row.update(ok=False,code=getattr(e,'code',type(e).__name__))
 row['seconds']=round(time.monotonic()-start,3);atomic(P,row);print(row)
if __name__=='__main__':main()
