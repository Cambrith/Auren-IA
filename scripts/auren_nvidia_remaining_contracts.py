"""Resolve additional POST contracts from the complete official navigation index."""
import concurrent.futures,datetime,hashlib,json,sys,threading,time
from pathlib import Path
import httpx
from bs4 import BeautifulSoup
run=Path(sys.argv[1]);index=json.loads((run/'nvidia-reference-index.json').read_text());prior=json.loads((run/'nvidia-openapi-contracts.json').read_text());known={v['source'] for v in prior['models'] if v.get('schema')};jobs={};parent=None
for link in index['links']:
 if ' / ' in link['title']:parent=link['title'].replace(' / ','/')
 if link['title'].lower().endswith('post'):
  url='https://docs.api.nvidia.com'+link['url'] if link['url'].startswith('/') else link['url']
  if url not in known:jobs.setdefault(url,parent)
out=[];pace=threading.Lock();last=[0.];stop=threading.Event()
def fetch(job):
 url,model=job;row={'advertised_model':model,'source':url,'at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 if stop.is_set():return {**row,'result':'documentation_rate_limit_stopped'}
 try:
  with pace:time.sleep(max(0,1.5-(time.monotonic()-last[0])));last[0]=time.monotonic()
  response=httpx.get(url,trust_env=False,follow_redirects=True,timeout=20);row['http_status']=response.status_code
  if response.status_code==429:stop.set();row['result']='documentation_rate_limit'
  if response.status_code==200:
   script=BeautifulSoup(response.text,'html.parser').find('script',id='ssr-props');document=json.loads(script.get_text()).get('document',{}) if script else {};api=document.get('api') or {};schema=api.get('schema');row.update(title=document.get('title'),document_path=api.get('path'),document_method=api.get('method'),schema=schema,schema_sha256=hashlib.sha256(json.dumps(schema,sort_keys=True).encode()).hexdigest() if schema else None)
 except Exception as error:row['error']=type(error).__name__
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for row in pool.map(fetch,jobs.items()):
  out.append(row);tmp=run/'.nvidia-additional-openapi-contracts.tmp';tmp.write_text(json.dumps({'models':out},ensure_ascii=False,indent=2));tmp.replace(run/'nvidia-additional-openapi-contracts.json');print(row['advertised_model'],row.get('http_status'),row.get('document_path'),flush=True)
