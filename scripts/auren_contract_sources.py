"""Read-only primary NVIDIA native contract refresh; never performs inference."""
import concurrent.futures,datetime,hashlib,json,re,sys,threading,time
from pathlib import Path
import httpx
from bs4 import BeautifulSoup
run=Path(sys.argv[1]);matrix=json.loads((run/'matrix.json').read_text());jobs={}
for row in matrix['rows']:
 source=row.get('contract_source','')
 if row['provider']=='nvidia' and '/reference-link/' in source:jobs[source]=row['requested_model']
pacer=threading.Lock();last_read=[0.]
def fetch(item):
 source,model=item;slug=source.rsplit('/',1)[1];out={'source_original':source,'requested_model':model,'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'attempts':[]}
 with httpx.Client(trust_env=False,timeout=15,follow_redirects=True) as client:
  for prefix in ['https://docs.api.nvidia.com/nim/reference/','https://docs.api.nvidia.com/nim/re/reference/']:
   url=prefix+slug
   try:
    with pacer:
     time.sleep(max(0,1.2-(time.monotonic()-last_read[0])));last_read[0]=time.monotonic()
    response=client.get(url);
    if response.status_code==429:
     out['attempts'].append({'url':url,'http_status':429,'retry_after':response.headers.get('retry-after'),'rate_limit_surface':'documentation, not inference'});break
    text=BeautifulSoup(response.text,'html.parser').get_text('\n',strip=True);out['attempts'].append({'url':url,'http_status':response.status_code,'final_url':str(response.url)})
    if response.status_code==200 and ('Body Params' in text or 'Path Params' in text):
     match=re.search(r'https://(?:ai\.api|integrate\.api|api\.nvcf)\.nvidia\.com/[^\s<>]+',text);start=text.find('Body Params') if 'Body Params' in text else text.find('Path Params');end=text.find('Responses',start)
     out.update(source_current=str(response.url),endpoint=match.group(0) if match else None,contract_text=text[start:end][:16000],text_sha256=hashlib.sha256(text.encode()).hexdigest(),verified_contract_page=True);return out
   except Exception as error:out['attempts'].append({'url':url,'error':type(error).__name__})
 return {**out,'verified_contract_page':False}
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for result in pool.map(fetch,jobs.items()):
  results.append(result);temp=run/'.nvidia-contracts.tmp';temp.write_text(json.dumps(results,ensure_ascii=False,indent=2));temp.replace(run/'nvidia-native-contracts.json');print(result['requested_model'],result['verified_contract_page'],result.get('endpoint'),flush=True)
print('contract refresh complete',len(results),flush=True)
