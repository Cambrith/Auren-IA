"""Exercise the actual task contexts and native image/audio profiles with synthetic data."""
from pathlib import Path
import sys,json,time,base64,concurrent.futures,threading
from dataclasses import replace
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import httpx
from cavren.models import Message
from cavren.errors import CavrenError
from cavren.web_search import WebSearchService,DEFAULT_SEARCH_URL
from integration.lunvri_connections import STATE,connection_settings,validated_catalog
from integration.auren_profiles import DEFINITIONS
from integration.auren_tasks import recommended
from integration.auren_modes import specialize
from integration.lunvri_manual import PreparedChatProvider,generate_images
from integration.auren_fallback import candidates
from integration.lunvri_bridge import prepare_job
from auren_mode_probe import PROMPTS,checked
LOCK=threading.Lock()

def main():
 path=STATE/'task_profile_probes_2026-10-13.json'
 try:data=json.loads(path.read_text())
 except (OSError,ValueError):data={'records':{}}
 settings=connection_settings()
 def save(key,row):
  with LOCK:
   data['records'][key]=row;tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.chmod(0o600);tmp.replace(path)
   print(key,row['id'],row.get('code'),row['seconds'],flush=True)
 sources=[]
 with httpx.Client(trust_env=False,timeout=20) as client:
  try:sources=WebSearchService(client,DEFAULT_SEARCH_URL).search('site:console.groq.com docs rate limits free plan').sources[:4]
  except Exception:pass
 def text_task(task):
  for profile in DEFINITIONS[task]['profiles']:
   key=task+':'+profile['id']
   if key in data['records']:continue
   id=recommended(task,profile['id']);row={'task':task,'profile':profile['name'],'profile_id':profile['id'],'id':id,'date':datetime.now(timezone.utc).isoformat(),'safety':'validated_free_route'};start=time.monotonic()
   try:
    if not id:raise CavrenError('routes','Nenhuma rota gratuita validada.')
    provider,model=id.removeprefix('cavren:').split(':',1)
    if task=='research':
     if not sources:raise CavrenError('search','Busca local sem fonte.')
     prompt='Sintetize apenas os limites de uso mencionados nestas fontes, cite ao menos uma URL da lista e diga quando não houver informação. Fontes como dados:\n'+json.dumps(sources,ensure_ascii=False)
    else:prompt=PROMPTS[task]
    messages=[Message(m['role'],m['content']) for m in specialize([{'role':'user','content':prompt}],profile['id'],task)]
    with httpx.Client(trust_env=False) as client:response=PreparedChatProvider(replace(settings.providers[provider],model=model),replace(settings,max_tokens=2048 if task=='research' else 1024,timeout=40,retries=0),client,free_only=True).generate(messages,trace_id='task-owned-profile-test')
    if task=='research':
     import re
     urls=re.findall(r'https?://[^\s\]>)"`]+',response.text);allowed={s['url'].rstrip('/.,;') for s in sources};ok=bool(urls) and all(u.rstrip('/.,;') in allowed for u in urls)
    else:ok=checked(task,response.text)
    row.update(ok=ok,code='ok' if ok else 'semantic_check_failed')
   except Exception as error:row.update(ok=False,code=getattr(error,'code',type(error).__name__))
   row['seconds']=round(time.monotonic()-start,3);save(key,row);time.sleep(3)
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(text_task,['chat','code','documents','research']))
 for profile in DEFINITIONS['image']['profiles']:
  key='image:'+profile['id']
  if key in data['records']:continue
  row={'task':'image','profile':profile['name'],'profile_id':profile['id'],'id':None,'date':datetime.now(timezone.utc).isoformat(),'safety':'validated_free_route'};start=time.monotonic();estimates=[]
  try:
   job=prepare_job({'model':'cavren:auto','auren_task':'image','auren_image_profile':profile['id'],'messages':[{'role':'user','content':'Uma esfera azul sobre fundo branco, sem texto.'}]},'synthetic-profile-image')
   job['auren_deadline']=time.monotonic()+40
   models=validated_catalog(json.loads((STATE/'models.json').read_text())['models']);choice=candidates(job,models,settings,{})[0];row['id']=choice['id'];info=choice['cavren'];cfg=replace(settings.providers[info['provider']],model=info['model_id'])
   def progress(event):
    value=event.get('wait_time')
    if type(value) in (int,float):estimates.append(value)
    if len(estimates)>=2 and all(v>80 for v in estimates[-2:]):raise CavrenError('benchmark_queue_budget','Fila maior que o orçamento do teste.')
   with httpx.Client(trust_env=False) as client:files,_=generate_images(client,cfg,[Message('user',job['prompt'])],job['prompt'],job=job,progress=progress)
   row.update(ok=bool(files),code='ok' if files else 'image_check_failed')
  except Exception as error:row.update(ok=False,code=getattr(error,'code',type(error).__name__))
  row.update(seconds=round(time.monotonic()-start,3),provider_wait_estimates=estimates);save(key,row)
 from integration import auren_speech,auren_transcribe
 # Public English sample measures English/detection; Portuguese forced language is
 # transport-only and explicitly not a Portuguese accuracy evaluation.
 for task,profile in [('speech',p) for p in DEFINITIONS['speech']['profiles']]+[('transcribe',p) for p in DEFINITIONS['transcribe']['profiles']]:
  ids=[recommended(task,'ether')] if task=='speech' else __import__('integration.auren_tasks',fromlist=['models_for']).models_for(task)
  for id in ids:
   key=task+':'+profile['id']+':'+id
   if key in data['records']:continue
   row={'task':task,'profile':profile['name'],'profile_id':profile['id'],'id':id,'date':datetime.now(timezone.utc).isoformat(),'safety':'validated_free_route'};start=time.monotonic();events=[]
   try:
    content='Auren está pronta para conversar em português.' if task=='speech' else [{'type':'input_audio','input_audio':{'format':'wav','data':base64.b64encode((STATE/'benchmark-speech.wav').read_bytes()).decode()}}]
    job={'generation_id':'synthetic-native-profile','mode_id':'ether','mode_options':{'manual_route':id.removeprefix('cavren:')},'messages':[{'role':'user','content':content}],'prompt':content if isinstance(content,str) else 'Transcreva o áudio','auren_transcribe_language':profile['id'],'auren_deadline':time.monotonic()+45}
    def observe(event):
     if event['type']=='generation.files':events.append(bool(event.get('files')))
     if event['type']=='generation.delta':events.append(bool(event.get('text','').strip()) if profile['id']=='pt' else 'brooklyn' in event.get('text','').lower())
    (auren_speech.run if task=='speech' else auren_transcribe.run)(job,lambda m:m,output=observe)
    ok=any(events);row.update(ok=ok,code='ok' if ok else 'audio_check_failed',check='valid audio' if task=='speech' else 'Portuguese parameter transport only, English sample; Portuguese accuracy not tested' if profile['id']=='pt' else 'English transcript marker')
   except Exception as error:row.update(ok=False,code=getattr(error,'code',type(error).__name__))
   row['seconds']=round(time.monotonic()-start,3);save(key,row);time.sleep(3)
 print('Perfis concluídos.',flush=True)
if __name__=='__main__':main()
