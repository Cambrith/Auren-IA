"""Primary model-specific OpenAPI extraction; only public contract fields saved."""
import datetime,hashlib,json,sys,time
from pathlib import Path
import httpx
from bs4 import BeautifulSoup
run=Path(sys.argv[1]);matrix=json.loads((run/'matrix.json').read_text());jobs={}
for row in matrix['rows']:
 source=row.get('contract_source','')
 if row['provider']=='nvidia' and row.get('blocker')=='contract_review' and '/reference-link/' in source:jobs[row['requested_model']]=source.replace('/reference-link/','/nim/reference/')
# Exact additional names discovered in the current official catalog review.
for model,slug in [('meta/esm2-650m','meta-esm2-650m-infer'),('meta/esmfold','meta-esmfold-infer'),('arc/evo2-40b-forward','arc-evo2-40b-forward-infer'),('mit/diffdock','mit-diffdock-infer')]:jobs.setdefault(model,'https://docs.api.nvidia.com/nim/reference/'+slug)
out=[]
with httpx.Client(trust_env=False,follow_redirects=True,timeout=20) as client:
 for model,url in jobs.items():
  row={'model':model,'source':url,'at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
  try:
   r=client.get(url);row['http_status']=r.status_code
   if r.status_code==200:
    script=BeautifulSoup(r.text,'html.parser').find('script',id='ssr-props');data=json.loads(script.get_text()) if script else {};api=(data.get('document') or {}).get('api') or {};schema=api.get('schema')
    row.update(document_title=(data.get('document') or {}).get('title'),document_path=api.get('path'),document_method=api.get('method'),document_updated_at=(data.get('document') or {}).get('updated_at'),schema=schema,schema_sha256=hashlib.sha256(json.dumps(schema,sort_keys=True).encode()).hexdigest() if schema else None)
   elif r.status_code==429:row['documentation_rate_limit']=True
  except Exception as error:row['error']=type(error).__name__
  out.append(row);tmp=run/'.nvidia-openapi-contracts.tmp';tmp.write_text(json.dumps({'models':out},ensure_ascii=False,indent=2));tmp.replace(run/'nvidia-openapi-contracts.json');print(model,row.get('http_status'),row.get('document_path'),flush=True)
  if row.get('documentation_rate_limit'):break
  time.sleep(1.5)
