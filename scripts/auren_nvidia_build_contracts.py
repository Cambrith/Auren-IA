"""Read-only exact model page contracts; no inference or credentials."""
import datetime,hashlib,json,re,sys,time
from pathlib import Path
import httpx
from bs4 import BeautifulSoup
run=Path(sys.argv[1]);matrix=json.loads((run/'matrix.json').read_text());models=sorted({r['requested_model'] for r in matrix['rows'] if r['provider']=='nvidia' and r.get('blocker')=='contract_review'});out=[]
with httpx.Client(trust_env=False,follow_redirects=True,timeout=20) as client:
 for model in models:
  url='https://build.nvidia.com/'+model+'?section=deploy';row={'model':model,'source':url,'at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
  try:
   response=client.get(url);row['http_status']=response.status_code
   if response.status_code==429:row['documentation_rate_limit']=True
   if response.status_code==200:
    soup=BeautifulSoup(response.text,'html.parser');text=soup.get_text('\n',strip=True);row.update(text_sha256=hashlib.sha256(text.encode()).hexdigest(),endpoints=sorted(set(re.findall(r'https://(?:ai\.api|integrate\.api|api\.nvcf)\.nvidia\.com/[^\s"\'<>]+',text))))
    start=text.find('Prototype');end=text.find('Specifications',start);row['prototype_text']=text[start:end][:18000] if start>=0 else ''
    available=text.find('Model Availability');row['availability_text']=text[available:available+450] if available>=0 else None
    row['page_exact_model_match']=model.lower() in text.lower()
   out.append(row);temp=run/'.nvidia-build-contracts.tmp';temp.write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'models':out},ensure_ascii=False,indent=2));temp.replace(run/'nvidia-build-contracts.json');print(model,row['http_status'],row.get('availability_text'),flush=True)
   if response.status_code==429:break
  except Exception as error:row['error']=type(error).__name__;out.append(row)
  time.sleep(1.5)
