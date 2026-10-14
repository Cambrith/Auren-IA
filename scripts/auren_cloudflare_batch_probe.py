"""One-item native Workers AI queue contract; no deployment or new resources."""
import hashlib,time

def properties(schema):
 keys=set()
 if isinstance(schema,dict):
  keys.update(schema.get('properties',{}))
  for union in ['oneOf','anyOf','allOf']:
   for alternative in schema.get(union,[]):keys.update(properties(alternative))
 elif isinstance(schema,list):
  for value in schema:keys.update(properties(value))
 return keys

def batch_probe(client,row,sample,cfg,asset,run):
 import auren_exhaustive_probe as audit
 start=time.monotonic();result={'at':audit.now(),'sample':sample,'real_call':False,'success':False,'cost_class':'unknown','states':[]};model=row['requested_model'];schema=audit.read(run/'cloudflare-all-schemas.json',{}).get(model,{}).get('schema',{}).get('input',{})
 if 'requests' not in properties(schema):return {**result,'result':'operation_not_advertised_in_native_schema','seconds':0,'contract_valid':False}
 url='https://api.cloudflare.com/client/v4/accounts/'+cfg.account_id+'/ai/run/'+model;headers=audit.headers('cloudflare',cfg);identity=row['key']+('::'+row['native_contract_revision'] if row.get('native_contract_revision') else '');jobpath=run/'remote'/('cf-batch-'+hashlib.sha256(identity.encode()).hexdigest()[:20]+'.json');prior=audit.read(jobpath,{});remote=prior.get('remote_id')
 op='rerank' if 'bge-m3' in model else 'embeddings' if any(word in model for word in ['bge-','embedding']) else 'translation' if 'm2m' in model else 'text';result['tested_native_operation']=op
 try:
  if not remote:
   base={**row,'operation':op,'endpoint':url};_,payload,_=audit.request_body(base,0,cfg,asset)
   # Responses wire is separately declared in the gpt-oss batch branch.
   if 'gpt-oss' in model:payload={'input':audit.PROMPTS['text'][0],'max_output_tokens':512,'reasoning':{'effort':'low'}}
   payload['external_reference']='auren-synthetic-one';result['real_call']=True
   response=client.post(url,headers=headers,params={'queueRequest':'true'},json={'requests':[payload]},timeout=30);data=response.json();result.update(audit.safe_response(response,data,cfg))
   if response.status_code>=400 or data.get('success') is False:result['result']='provider_denial';return result
   source=data.get('result',{});remote=source.get('request_id');result['accepted']=bool(remote)
   if remote:audit.atomic(jobpath,{'remote_id':remote,'provider':'cloudflare','row':row['key'],'at':audit.now()})
   elif not (source.get('responses') or source.get('results')):result['result']='batch_response_missing_id';return result
  else:data={};result['polling_only']=True
  result['remote_id']=remote
  for index in range(3):
   if not (data.get('result',{}).get('responses') or data.get('result',{}).get('results')):
    response=client.post(url,headers=headers,params={'queueRequest':'true'},json={'request_id':remote},timeout=15);data=response.json();result.update(audit.safe_response(response,data,cfg));result['states'].append({'at':audit.now(),'http_status':response.status_code,'status':data.get('result',{}).get('status')})
    result['poll_response_keys']=list(data.get('result',{})) if isinstance(data.get('result'),dict) else []
    if response.status_code>=400 or data.get('success') is False:result['result']='remote_poll_denied';break
   source=data.get('result',{});items=source.get('responses') or source.get('results') or []
   if items:
    if items[0].get('success') is False:result['result']='native_batch_item_error';break
    body=items[0].get('result',{})
    result.update(audit.safe_response(response,body,cfg))
    if 'gpt-oss' in model and body.get('output'):
     result['output_types']=[output.get('type') for output in body.get('output',[])]
     text=''.join(part.get('text','') for output in body.get('output',[]) if output.get('type')=='message' and output.get('channel') not in ['analysis','reasoning'] for part in output.get('content',[]) if isinstance(part,dict) and part.get('type') in ['output_text','text']);body={'response':text}
    ok,code,ev=audit.evaluate(body,'cloudflare',op,0);result.update(success=ok,result=code,evidence=ev);break
   if index<2:time.sleep(3)
  result.setdefault('result','accepted_pending_completion');audit.atomic(jobpath,{**prior,'remote_id':remote,'provider':'cloudflare','row':row['key'],'at':audit.now(),'result':result['result']})
 except Exception as error:result['result']=type(error).__name__
 finally:result['seconds']=round(time.monotonic()-start,3)
 return result
