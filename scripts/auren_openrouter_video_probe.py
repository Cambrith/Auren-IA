"""Documented per-duration video pricing and native job flow; audit only."""
import base64,hashlib,time

def price_bound(meta,operation='video'):
 durations=meta.get('supported_durations') or [];resolutions=meta.get('supported_resolutions') or [];prices=meta.get('pricing_skus') or {}
 if not durations:return None,{},'native_input_video_contract_pending'
 duration=min(durations);resolution=next((v for v in ['480p','720p','768p','1080p','1K','2K','4K'] if v in resolutions),None)
 if not resolution:return None,{},'native_resolution_contract_pending'
 image=operation in ['video_first_frame','video_interpolation'];count=2 if operation=='video_interpolation' else 1 if image else 0;res=resolution.lower()
 if meta.get('id')=='bytedance/seedance-2.5' and '854x480' in (meta.get('supported_sizes') or []) and 'video_tokens_without_audio' in prices:
  # Official model review specifies 24 FPS; use the exact advertised size.
  cost=854*480*duration*24/1024*float(prices['video_tokens_without_audio'])
  return cost,{'duration':duration,'resolution':'480p','size':'854x480','aspect_ratio':'16:9','generate_audio':False},None
 if meta.get('id') in ['bytedance/seedance-1-5-pro','bytedance/seedance-2.0','bytedance/seedance-2.0-fast','bytedance/seedance-2.0-mini'] and 'video_tokens_without_audio' in prices and '480x480' in (meta.get('supported_sizes') or []):
  # These exact model cards document 24 FPS and (height*width*seconds*24)/1024.
  # Request the catalog-advertised square 480p size, preventing aspect ambiguity.
  tokens=480*480*duration*24/1024;cost=tokens*float(prices['video_tokens_without_audio'])
  return cost,{'duration':duration,'resolution':'480p','aspect_ratio':'1:1','generate_audio':False},None
 keys=(['image_to_video_duration_seconds_'+res,'reference_duration_seconds_'+res] if image else ['text_to_video_duration_seconds_'+res])+['duration_seconds_without_audio_'+res,'duration_seconds_'+res,'cents_per_video_output_second_'+res,'cents_per_second_output_'+res,'duration_seconds_without_audio','duration_seconds','cents_per_second_output']
 selected=next((key for key in keys if key in prices),None)
 if not selected:return None,{},'native_video_output_units_unverified'
 rate=float(prices[selected])/(100 if selected.startswith('cents_') else 1);cost=duration*rate
 if image:cost+=count*(float(prices.get('cents_per_image_input',0))/100+float(prices.get('reference_images',0)))
 cost=max(cost,float(prices.get('minimum_cents_per_generation',0))/100)
 body={'duration':duration,'resolution':resolution,'aspect_ratio':'16:9' if '16:9' in (meta.get('supported_aspect_ratios') or []) else (meta.get('supported_aspect_ratios') or ['16:9'])[0],'generate_audio':False}
 return cost,body,None

def video_probe(client,row,sample,cfg,asset,run):
 import auren_exhaustive_probe as audit
 from auren_native_media_probe import inspect_media,audit_error
 start=time.monotonic();out={'at':audit.now(),'sample':sample,'real_call':False,'success':False,'cost_class':'unknown','states':[]};op=row['operation'];parameters=row['video_parameters'];jobpath=run/'remote'/('or-video-'+hashlib.sha256(row['key'].encode()).hexdigest()[:20]+'.json');prior=audit.read(jobpath,{});remote=prior.get('remote_id');headers=audit.headers('openrouter',cfg)
 try:
  if not remote:
   body={'model':row['requested_model'],'prompt':'A blue sphere moves slowly across a plain white background. No people, words, or logos.',**parameters}
   if op in ['video_first_frame','video_interpolation']:
    image='data:image/png;base64,'+base64.b64encode((asset/'vision.png').read_bytes()).decode();body['frame_images']=[{'type':'image_url','image_url':{'url':image},'frame_type':'first_frame'}]
    if op=='video_interpolation':body['frame_images'].append({'type':'image_url','image_url':{'url':image},'frame_type':'last_frame'})
   out.update(real_call=True,parameters=parameters);response=client.post('https://openrouter.ai/api/v1/videos',headers=headers,json=body,timeout=30);data=response.json();out.update(audit.safe_response(response,data,cfg))
   if response.status_code>=400:out['result']=audit_error(response.status_code);return out
   remote=data.get('id');out['accepted']=bool(remote)
   if not remote:out['result']='video_missing_job_id';return out
   audit.atomic(jobpath,{'remote_id':remote,'provider':'openrouter','row':row['key'],'at':audit.now(),'max_output_seconds':parameters['duration'],'estimated_upper_usd':row['estimated_media_upper_usd']})
  else:out['polling_only']=True
  out['remote_id']=remote
  for index in range(3):
   response=client.get('https://openrouter.ai/api/v1/videos/'+remote,headers=headers,timeout=15);data=response.json();out.update(audit.safe_response(response,data,cfg));status=data.get('status');out['states'].append({'at':audit.now(),'http_status':response.status_code,'status':status})
   if status in ['failed','cancelled','expired']:out['result']='video_provider_'+status;break
   if status=='completed':
    download=client.get('https://openrouter.ai/api/v1/videos/'+remote+'/content',headers=headers,params={'index':0},timeout=30);out['download_http_status']=download.status_code
    if download.status_code!=200:out['result']='video_download_denied';break
    media=inspect_media(download.content,'.mp4');duration=parameters['duration'];ok=abs(media['duration_seconds']-duration)<.75 and any(s.get('codec_type')=='video' and s.get('width',0)>0 and s.get('height',0)>0 for s in media['streams']);out.update(success=ok,result='valid_video_container_semantics_pending' if ok else 'video_file_check_failed',semantic_pending=True,media=media);break
   if index<2:time.sleep(5)
  out.setdefault('result','accepted_pending_completion');audit.atomic(jobpath,{**prior,'remote_id':remote,'provider':'openrouter','row':row['key'],'at':audit.now(),'result':out['result'],'max_output_seconds':parameters['duration']})
  if out['result']=='accepted_pending_completion':out['cancel_note']='No cancellation method documented by the video API. Single fixed-duration output bounded; resume by polling existing ID.'
 except Exception as error:out['result']=type(error).__name__
 finally:
  out['seconds']=round(time.monotonic()-start,3);cost=out.get('reported_cost_usd');out['cost_class']='positive_reported' if cost and cost>0 else 'zero_reported' if cost==0 else 'unknown'
 return out
