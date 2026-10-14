"""Public complete NVIDIA Build cards; URL slugs are never assumed wire IDs."""
import datetime,hashlib,json,re,sys,time
from pathlib import Path
import httpx
from bs4 import BeautifulSoup
run=Path(sys.argv[1]);models={};calls=[]
with httpx.Client(trust_env=False,follow_redirects=True,timeout=20) as client:
 for page in range(1,10):
  url='https://build.nvidia.com/models?pageSize=96&page='+str(page);r=client.get(url);call={'source':url,'http_status':r.status_code,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sha256':hashlib.sha256(r.content).hexdigest()};calls.append(call)
  if r.status_code!=200:break
  soup=BeautifulSoup(r.text,'html.parser');count=0
  for link in soup.find_all('a',href=True):
   if 'linkbox-overlay' not in (link.get('class') or []):continue
   slug=link['href'].split('?')[0].strip('/')
   if not re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+',slug):continue
   parent=link.parent;entry={'card_slug':slug,'card_url':'https://build.nvidia.com/'+slug,'card_name':link.get_text(' ',strip=True),'card_metadata_text':parent.get_text(' ',strip=True)[:1800],'catalog_source':url,'native_wire_id_status':'Unverified; card URL slug is not automatically an inference identifier.'};models[slug]=entry;count+=1
  call['card_count']=count;print('page',page,'cards',count,flush=True)
  if count<96:break
  time.sleep(2)
(run/'nvidia-complete-build-catalog.json').write_text(json.dumps({'catalog_calls':calls,'models':list(models.values())},ensure_ascii=False,indent=2)+'\n')
