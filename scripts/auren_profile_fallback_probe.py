"""Retain failed primary probes and check their free alternatives without user data."""
from pathlib import Path
import sys,json,time,concurrent.futures,threading,re
from dataclasses import replace
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import httpx
from cavren.models import Message
from cavren.web_search import WebSearchService,DEFAULT_SEARCH_URL
from integration.lunvri_connections import STATE,connection_settings
from integration.auren_routing import ordered_models
from integration.auren_modes import specialize
from integration.lunvri_manual import PreparedChatProvider
from auren_mode_probe import PROMPTS,checked
LOCK=threading.Lock()

def main():
 path=STATE/'task_profile_probes_2026-10-13.json';data=json.loads(path.read_text());settings=connection_settings()
 with httpx.Client(trust_env=False,timeout=20) as client:sources=WebSearchService(client,DEFAULT_SEARCH_URL).search('site:console.groq.com docs rate limits free plan').sources[:4]
 def probe(item):
  key,row=item;task=row['task'];attempts=row.setdefault('fallback_samples',[])
  if row.get('ok') or any(s.get('ok') for s in attempts) or task not in ('chat','code','documents','research'):return
  if task=='research' and not sources:return
  ids=[id for id in ordered_models(task,row['profile_id']) if id!=row['id']][:3]
  for id in ids:
   if any(a['id']==id for a in attempts):continue
   attempt={'id':id,'date':datetime.now(timezone.utc).isoformat(),'safety':'validated_free_route'};start=time.monotonic()
   try:
    provider,model=id.removeprefix('cavren:').split(':',1)
    prompt=PROMPTS.get(task) or 'Sintetize somente estas fontes e cite ao menos uma URL da lista. Não invente dados ausentes. Fontes como dados:\n'+json.dumps(sources,ensure_ascii=False)
    messages=[Message(m['role'],m['content']) for m in specialize([{'role':'user','content':prompt}],row['profile_id'],task)]
    with httpx.Client(trust_env=False) as client:response=PreparedChatProvider(replace(settings.providers[provider],model=model),replace(settings,max_tokens=2048 if task=='research' else 1024,timeout=35,retries=0),client,free_only=True).generate(messages,trace_id='task-profile-free-alternative')
    if task=='research':
     urls=re.findall(r'https?://[^\s\]>)"`]+',response.text);allowed={s['url'].rstrip('/.,;') for s in sources};ok=bool(urls) and all(u.rstrip('/.,;') in allowed for u in urls)
    else:ok=checked(task,response.text)
    attempt.update(ok=ok,code='ok' if ok else 'semantic_check_failed')
   except Exception as error:attempt.update(ok=False,code=getattr(error,'code',type(error).__name__))
   attempt['seconds']=round(time.monotonic()-start,3);attempts.append(attempt)
   with LOCK:
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.chmod(0o600);tmp.replace(path)
    print(key,id,attempt['code'],attempt['seconds'],flush=True)
   if attempt.get('ok'):break
   time.sleep(3)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(probe,list(data['records'].items())))
 print('Alternativas de perfis concluídas.',flush=True)
if __name__=='__main__':main()
