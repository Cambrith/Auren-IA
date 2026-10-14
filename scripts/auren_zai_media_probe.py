"""Native fixed-price Z.ai image/video probes with durable IDs and no retries."""
import base64,hashlib,time
from urllib.parse import quote,urlsplit

def download(client,url):
 parsed=urlsplit(url)
 if parsed.scheme!='https' or not parsed.hostname or not any(parsed.hostname==host or parsed.hostname.endswith('.'+host) for host in ['z.ai','bigmodel.cn','aliyuncs.com','myqcloud.com','volces.com']):raise ValueError('NativeMediaHostNeedsVerification')
 # Never forward API credentials to storage, and never save signed URLs.
 with client.stream('GET',url,timeout=25) as response:
  response.raise_for_status();raw=bytearray()
  for part in response.iter_bytes():
   raw.extend(part)
   if len(raw)>20_000_000:raise ValueError('NativeMediaDownloadByteBudget')
 return bytes(raw)

def probe(client,row,sample,cfg,asset,run):
 import auren_exhaustive_probe as audit
 from auren_native_media_probe import inspect_media,audit_error
 started=time.monotonic();op=row['operation'];video=op.startswith('video');asynchronous=video or op=='image_async';out={'at':audit.now(),'sample':sample,'real_call':False,'success':False,'cost_class':'unknown','states':[]};path=run/'remote'/('zai-'+hashlib.sha256((row['key']+':'+str(sample)).encode()).hexdigest()[:20]+'.json');prior=audit.read(path,{});remote=prior.get('remote_id');data={}
 try:
  if not remote:
   body={'model':row['requested_model'],'prompt':'A blue sphere moves slowly across a plain white background. No words.' if video else audit.PROMPTS['image'][sample],**row['native_media_parameters']}
   if op in ['video_first_frame','video_interpolation']:
    image=base64.b64encode((asset/'vision.png').read_bytes()).decode();body['image_url']=[image]* (2 if op=='video_interpolation' else 1)
   out.update(real_call=True,parameters=row['native_media_parameters'],estimated_request_upper_usd=row['estimated_media_upper_usd']);response=client.post(row['endpoint'],headers=audit.headers('zai',cfg),json=body,timeout=30);data=response.json();out.update(audit.safe_response(response,data,cfg))
   if response.status_code>=400:out['result']=audit_error(response.status_code);return out
   if asynchronous:
    remote=data.get('id');out['accepted']=bool(remote)
    if not remote:out['result']='native_async_job_id_missing';return out
    audit.atomic(path,{'remote_id':remote,'row':row['key'],'provider':'zai','sample':sample,'at':audit.now(),'estimated_upper_usd':row['estimated_media_upper_usd']})
  else:out['polling_only']=True
  if asynchronous:
   out['remote_id']=remote
   for index in range(3):
    response=client.get('https://api.z.ai/api/paas/v4/async-result/'+quote(remote,safe=''),headers=audit.headers('zai',cfg),timeout=15);data=response.json();out.update(audit.safe_response(response,data,cfg));state=data.get('task_status');out['states'].append({'at':audit.now(),'http_status':response.status_code,'state':state})
    if response.status_code>=400:out['result']='native_async_result_denied';return out
    if state=='FAIL':out['result']='native_async_generation_failed';return out
    if state=='SUCCESS':break
    if index<2:time.sleep(5)
   if data.get('task_status')!='SUCCESS':out.update(result='accepted_pending_completion',cancel_note='No native cancellation documented; output bounded by fixed per-image/video price. Resume existing ID.');return out
  items=data.get('video_result') if video else data.get('image_result',data.get('data'));items=items or []
  if len(items)!=1 or not items[0].get('url'):out['result']='native_media_output_missing';return out
  url=items[0]['url'];out['download_host']=urlsplit(url).hostname;raw=download(client,url)
  if video:
   inspected=inspect_media(raw,'.mp4');streams=[s for s in inspected['streams'] if s.get('codec_type')=='video'];ok=len(streams)==1 and abs(inspected['duration_seconds']-5)<.75 and (streams[0].get('width'),streams[0].get('height'))==(1280,720);out.update(success=ok,result='valid_video_container_semantics_pending' if ok else 'native_video_file_check_failed',semantic_pending=True,media=inspected)
  else:
   image=audit.decode_image(raw,run);out.update(success=True,result='valid_native_image_container',files=[image])
 except Exception as error:out['result']=type(error).__name__ if not isinstance(error,ValueError) else str(error)
 finally:out['seconds']=round(time.monotonic()-started,3)
 return out
