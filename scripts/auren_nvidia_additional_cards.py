"""Read public additional NVIDIA cards concurrently; no authenticated requests."""
import concurrent.futures,datetime,hashlib,json,re,sys,threading,time
from pathlib import Path
import httpx
from bs4 import BeautifulSoup
run=Path(sys.argv[1]);matrix=json.loads((run/'matrix.json').read_text());known={r['requested_model'] for r in matrix['rows'] if r['provider']=='nvidia'};norm=lambda value:re.sub('[._-]+','-',value.lower());normalized={norm(value) for value in known};catalog=json.loads((run/'nvidia-complete-build-catalog.json').read_text());jobs=[v for v in catalog['models'] if norm(v['card_slug']) not in normalized];pacer=threading.Lock();last=[0.];stop=threading.Event();out=[]
def fetch(card):
 row={'card_slug':card['card_slug'],'source':card['card_url']+'?section=deploy','at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 if stop.is_set():return {**row,'result':'documentation_refresh_stopped_after_rate_limit'}
 try:
  with pacer:time.sleep(max(0,1.5-(time.monotonic()-last[0])));last[0]=time.monotonic()
  response=httpx.get(row['source'],trust_env=False,follow_redirects=True,timeout=20);row['http_status']=response.status_code
  if response.status_code==429:stop.set();row['documentation_rate_limit']=True
  if response.status_code==200:
   soup=BeautifulSoup(response.text,'html.parser');text=soup.get_text('\n',strip=True);flat=soup.get_text(' ',strip=True);start=text.find('Prototype');end=text.find('Specifications',start);availability=text.find('Model Availability');row.update(title=soup.title.get_text() if soup.title else None,text_sha256=hashlib.sha256(text.encode()).hexdigest(),prototype_text=text[start:end][:24000] if start>=0 else text[:24000],availability_text=text[availability:availability+400] if availability>=0 else None,endpoints=sorted(set(re.findall(r'https://(?:ai\.api|integrate\.api|api\.nvcf|health\.api|grpc)\.nvidia\.com/[^\s"\'<>]+',flat))),wire_model_candidates=sorted(set(re.findall(r'"model"\s*:\s*"([^"\n]+)"',flat))),reference_links=sorted({a['href'] for a in soup.find_all('a',href=True) if 'docs.api.nvidia.com' in a['href']}))
 except Exception as error:row['error']=type(error).__name__
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for result in pool.map(fetch,jobs):
  out.append(result);tmp=run/'.nvidia-additional-cards.tmp';tmp.write_text(json.dumps({'models':out},ensure_ascii=False,indent=2));tmp.replace(run/'nvidia-additional-cards.json');print(result['card_slug'],result.get('http_status'),(result.get('availability_text') or '').replace('\n',';')[:120],flush=True)
