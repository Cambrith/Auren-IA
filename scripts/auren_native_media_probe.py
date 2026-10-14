"""Native, bounded cache, music and video contracts for the audit only."""
import base64,hashlib,json,math,subprocess,tempfile,time
from pathlib import Path
from urllib.parse import urlparse

def inspect_media(raw,suffix):
 with tempfile.NamedTemporaryFile(suffix=suffix) as f:
  f.write(raw);f.flush()
  check=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,width,height,sample_rate,channels','-of','json',f.name],capture_output=True,text=True,timeout=10)
  if check.returncode:raise ValueError('InvalidMedia')
  data=json.loads(check.stdout);duration=float(data.get('format',{}).get('duration',0))
  return {'duration_seconds':duration,'streams':data.get('streams',[]),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}

def media_probe(client,row,sample,cfg,asset,run):
 import auren_exhaustive_probe as audit
 if row['provider']=='zai':
  from auren_zai_media_probe import probe as zai_media_probe
  return zai_media_probe(client,row,sample,cfg,asset,run)
 if row['provider']=='openrouter' and row['operation'].startswith('video'):
  from auren_openrouter_video_probe import video_probe
  return video_probe(client,row,sample,cfg,asset,run)
 start=time.monotonic();op=row['operation'];result={'at':audit.now(),'sample':sample,'real_call':False,'success':False,'cost_class':'unknown'};headers={'x-goog-api-key':cfg.api_key};remote=None
 try:
  if op=='music':
   body={'contents':[{'parts':[{'text':'Create a short instrumental piece with piano and steady rhythm, without lyrics.'}]}]}
   result['real_call']=True;response=client.post(row['endpoint'],headers=headers,json=body,timeout=45);data=response.json();result.update(audit.safe_response(response,data,cfg))
   if response.status_code>=400:result['result']=audit_error(response.status_code);return result
   parts=(data.get('candidates') or [{}])[0].get('content',{}).get('parts',[]);parts=[p['inlineData'] for p in parts if p.get('inlineData',{}).get('data')]
   if not parts:result['result']='missing_music_audio';return result
   raw=base64.b64decode(parts[0]['data']);media=inspect_media(raw,'.mp3');ok=media['duration_seconds']>1 and any(s.get('codec_type')=='audio' for s in media['streams']);result.update(success=ok,result='valid_music_container_semantics_pending' if ok else 'music_file_check_failed',media=media,semantic_pending=True)
  elif op=='cache':
   model=row['requested_model'];content='Inventory line: seven boxes were counted in Lima. No price was supplied.\n'*350
   contents=[{'role':'user','parts':[{'text':content}]}];counturl='https://generativelanguage.googleapis.com/v1beta/models/'+model+':countTokens'
   count=client.post(counturl,headers=headers,json={'contents':contents},timeout=20);result['count_http_status']=count.status_code;result['auxiliary_call_count']=1
   if count.status_code>=400:result.update(audit.safe_response(count,count.json(),cfg),result='cache_token_count_denied',real_call=False);return result
   token_count=count.json().get('totalTokens',0);result['counted_input_tokens']=token_count
   if token_count>8000 or token_count<4096:result['result']='cache_input_budget_or_minimum';return result
   result['real_call']=True;response=client.post('https://generativelanguage.googleapis.com/v1beta/cachedContents',headers=headers,json={'model':'models/'+model,'contents':contents,'ttl':'60s','displayName':'Auren synthetic audit cache'},timeout=30);data=response.json();result.update(audit.safe_response(response,data,cfg))
   if response.status_code>=400:result['result']=audit_error(response.status_code);return result
   remote=data.get('name');result['remote_id']=remote;audit.atomic(run/'remote'/('cache-'+hashlib.sha256(row['key'].encode()).hexdigest()[:20]+'.json'),{'remote_id':remote,'expires_at':data.get('expireTime'),'row':row['key'],'provider':'gemini'})
   query=client.post('https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent',headers=headers,json={'cachedContent':remote,'contents':[{'role':'user','parts':[{'text':'Return only the documented city, quantity, and absent price as city|quantity|NL.'}]}],'generationConfig':{'maxOutputTokens':64}},timeout=30);d=query.json();result['cached_generation_http_status']=query.status_code;result['auxiliary_call_count']+=1
   usage=d.get('usageMetadata',{});text,_,finish=audit.extract(d,'gemini');hits=usage.get('cachedContentTokenCount',0);ok=query.status_code==200 and hits>0 and text.strip()=='Lima|7|NL';result.update(success=ok,result='valid_cache_hit_and_grounding' if ok else 'cache_generation_check_failed',cache_hit_tokens=hits,finish_reason=finish,response_sha256=hashlib.sha256(text.encode()).hexdigest())
  else:
   jobpath=run/'remote'/('video-'+hashlib.sha256(row['key'].encode()).hexdigest()[:20]+'.json');prior=audit.read(jobpath,{});remote=prior.get('remote_id');result['polling_only']=bool(remote)
   if not remote:
    body={'instances':[{'prompt':'A blue sphere slowly moving across a plain white background. No people, words, logos or other objects.'}],'parameters':{'durationSeconds':4,'resolution':'720p','aspectRatio':'16:9','sampleCount':1}}
    result.update(real_call=True,parameters=body['parameters']);response=client.post(row['endpoint'],headers=headers,json=body,timeout=30);data=response.json();result.update(audit.safe_response(response,data,cfg))
    if response.status_code>=400:result['result']=audit_error(response.status_code);return result
    remote=data.get('name');audit.atomic(jobpath,{'remote_id':remote,'row':row['key'],'provider':'gemini','at':audit.now(),'max_output_seconds':4,'max_outputs':1,'estimated_upper_usd':row['estimated_media_upper_usd']})
   result['remote_id']=remote;result['states']=[]
   for index in range(3):
    response=client.get('https://generativelanguage.googleapis.com/v1beta/'+remote,headers=headers,timeout=15);data=response.json();result['states'].append({'at':audit.now(),'http_status':response.status_code,'done':bool(data.get('done'))})
    if data.get('done'):
     if data.get('error'):result['result']='video_provider_error';break
     samples=data.get('response',{}).get('generateVideoResponse',{}).get('generatedSamples',[])
     uri=samples[0].get('video',{}).get('uri') if samples else None
     if not uri:result['result']='video_output_missing';break
     # Never forward credentials to unrelated hosts. Native generated files only.
     if urlparse(uri).hostname!='generativelanguage.googleapis.com':result['result']='video_download_origin_unverified';break
     download=client.get(uri,headers=headers,timeout=30);result['download_http_status']=download.status_code
     if download.status_code!=200:result['result']='video_download_denied';break
     media=inspect_media(download.content,'.mp4');ok=3.5<=media['duration_seconds']<=4.5 and any(s.get('codec_type')=='video' and min(s.get('width',0),s.get('height',0))>=720 for s in media['streams']);result.update(success=ok,result='valid_video_container_semantics_pending' if ok else 'video_file_check_failed',media=media,semantic_pending=True);break
    if index<2:time.sleep(5)
   result.setdefault('result','accepted_pending_completion');audit.atomic(jobpath,{**prior,'remote_id':remote,'row':row['key'],'provider':'gemini','at':audit.now(),'result':result['result'],'max_output_seconds':4,'max_outputs':1})
   if result['result']=='accepted_pending_completion':result['cancel_note']='No cancellation method documented in the Veo guide; one four-second output remains bounded, job ID retained for polling without resubmission.'
 except Exception as error:result['result']=type(error).__name__
 finally:
  if op=='cache' and remote:
   try:result['delete_http_status']=client.delete('https://generativelanguage.googleapis.com/v1beta/'+remote,headers=headers,timeout=15).status_code
   except Exception as error:result['delete_error']=type(error).__name__
  result['seconds']=round(time.monotonic()-start,3)
 return result

def audit_error(status):
 return {400:'contract_error',401:'authentication',402:'credit_or_payment_required',403:'permission_or_plan',404:'route_unavailable',429:'rate_or_quota_limit'}.get(status,'provider_error')
