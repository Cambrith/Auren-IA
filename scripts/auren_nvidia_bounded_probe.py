"""Finite native weather/optimization/3D probes; persist async IDs before polling."""
import base64,hashlib,io,json,math,struct,tarfile,time,zipfile
def inspect_archive(raw,depth=0):
 if depth>1:raise ValueError('Archive nesting cap')
 if len(raw)>20_000_000:raise ValueError('Archive byte cap')
 if zipfile.is_zipfile(io.BytesIO(raw)):
  with zipfile.ZipFile(io.BytesIO(raw)) as archive:
   entries=archive.infolist()
   if sum(v.file_size for v in entries)>40_000_000:raise ValueError('Expanded archive cap')
   files=[(v.filename,archive.read(v)) for v in entries if not v.is_dir()]
 else:
  with tarfile.open(fileobj=io.BytesIO(raw),mode='r:*') as archive:
   entries=archive.getmembers()
   if sum(v.size for v in entries)>40_000_000:raise ValueError('Expanded archive cap')
   files=[(v.name,archive.extractfile(v).read()) for v in entries if v.isfile()]
 images=[]
 for name,data in files:
  if name.lower().endswith('.png') and data.startswith(b'\x89PNG\r\n\x1a\n') and len(data)>=24:
   import auren_exhaustive_probe as audit
   checked=audit.decode_image(data,None);images.append({'name':name,**checked})
  elif name.endswith('.response'):
   images.extend(inspect_archive(data,depth+1))
 return images
def inspect_stl(raw):
 if len(raw)<84:return False
 count=struct.unpack('<I',raw[80:84])[0]
 if count<1 or count>200000 or len(raw)!=84+50*count:return False
 return all(math.isfinite(v) and abs(v)<1e8 for i in range(count) for v in struct.unpack('<12f',raw[84+50*i:132+50*i]))
def inspect_solver(data):
 solver=(data.get('response') or {}).get('solver_response') or {};vehicle=(solver.get('vehicle_data') or {}).get('auren-synthetic-vehicle',{});cost=solver.get('solution_cost');route=vehicle.get('route');dropped=solver.get('dropped_tasks') or {}
 ok=solver.get('status')==0 and solver.get('num_vehicles')==1 and type(cost) in (int,float) and math.isfinite(cost) and abs(cost-2)<1e-6 and route==[0,1,0] and not dropped.get('task_id')
 return ok,{'status':solver.get('status'),'cost':cost,'route':route,'vehicles':solver.get('num_vehicles')}
def probe(client,row,sample,cfg,asset,run):
 import auren_exhaustive_probe as audit
 start=time.monotonic();out={'at':audit.now(),'sample':sample,'real_call':False,'success':False,'cost_class':'unknown','states':[]};model=row['requested_model'];job=run/'remote'/('nvidia-small-'+hashlib.sha256(row['key'].encode()).hexdigest()[:20]+'.json');prior=audit.read(job,{});remote=prior.get('remote_id')
 if model=='nvidia/cuOpt':
  url='https://optimize.api.nvidia.com/v1/nvidia/cuopt';body={'action':'cuOpt_OptimizedRouting','data':{'cost_matrix_data':{'data':{'0':[[0,1],[1,0]]}},'fleet_data':{'vehicle_locations':[[0,0]],'vehicle_ids':['auren-synthetic-vehicle']},'task_data':{'task_locations':[1],'task_ids':['auren-synthetic-task']},'solver_config':{'time_limit':1,'verbose_mode':False}},'client_version':''};pollbase='https://optimize.api.nvidia.com/v1/status/'
 elif model=='nvidia/corrdiff':url='https://climate.api.nvidia.com/v1/nvidia/corrdiff';body={'input_id':0,'samples':1,'steps':1,'seed':0};pollbase='https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/'
 elif model=='nvidia/fourcastnet':url='https://climate.api.nvidia.com/v1/nvidia/fourcastnet';body={'input_id':0,'variables':'w10m','simulation_length':1,'ensemble_size':1,'noise_amplitude':0};pollbase='https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/'
 elif model=='microsoft/trellis':url='https://ai.api.nvidia.com/v1/genai/microsoft/trellis';body={'mode':'text','prompt':'A simple blue cube','samples':1,'no_texture':True,'output_format':'stl','ss_sampling_steps':10,'slat_sampling_steps':10,'seed':7};pollbase='https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/'
 else:return {**out,'result':'bounded_native_contract_pending','seconds':0}
 headers={**audit.headers('nvidia',cfg),'NVCF-POLL-SECONDS':'5'};out['parameters']=body
 try:
  if remote:response=client.get(pollbase+remote,headers=headers,timeout=15);out['polling_only']=True
  else:out['real_call']=True;response=client.post(url,headers=headers,json=body,timeout=30)
  for index in range(3):
   out['states'].append({'at':audit.now(),'http_status':response.status_code})
   if response.status_code!=202:break
   remote=response.headers.get('nvcf-reqid') or remote
   if not remote:out['result']='native_async_id_missing';return out
   out.update(accepted=True,remote_id=remote);audit.atomic(job,{'remote_id':remote,'row':row['key'],'at':audit.now(),'parameters':body})
   response=client.get(pollbase+remote,headers=headers,timeout=15)
  try:data=response.json()
  except ValueError:data={}
  out.update(audit.safe_response(response,data,cfg))
  if response.status_code>=400:out['result']={400:'contract_error',401:'authentication',402:'credit_or_payment_required',403:'permission_or_plan',404:'route_unavailable',410:'native_endpoint_retired',422:'contract_error',429:'rate_or_quota_limit'}.get(response.status_code,'provider_error');return out
  if response.status_code==202:out['result']='accepted_pending_completion';return out
  out['response_header_names']=sorted(response.headers.keys())
  if response.status_code==302 or response.status_code==200 and response.headers.get('location'):
   from urllib.parse import urlparse
   url=response.headers.get('location','');host=urlparse(url).hostname or ''
   if urlparse(url).scheme!='https' or not host.endswith('.amazonaws.com'):out['result']='native_asset_host_review_pending';return out
   # Signed asset never receives the provider authorization header.
   with client.stream('GET',url,timeout=20) as download:
    if download.status_code!=200:out['result']='native_asset_download_denied';return out
    chunks=[];length=0
    for chunk in download.iter_bytes():
     length+=len(chunk)
     if length>20_000_000:raise ValueError('Download byte cap')
     chunks.append(chunk)
   raw=b''.join(chunks)
  else:raw=response.content
  out.update(response_sha256=hashlib.sha256(raw).hexdigest(),content_type=response.headers.get('content-type'),response_bytes=len(raw),response_encoding_header=raw[:8].hex(),response_json_keys=list(data) if isinstance(data,dict) else [])
  if model in ['nvidia/corrdiff','nvidia/fourcastnet']:
   if len(raw)<=20_000_000:
    saved=audit.STATE/('audit-native-'+hashlib.sha256(row['key'].encode()).hexdigest()[:20]+'.bin');saved.write_bytes(raw);out['private_output_retained_for_decoder_review']=True
   images=inspect_archive(raw);ok=bool(images) and any('output' in v['name'] or ('006' in v['name'] and model=='nvidia/fourcastnet') for v in images) and all(v['width']>0 and v['height']>0 for v in images);out.update(success=ok,result='native_weather_images_semantics_pending' if ok else 'native_weather_archive_check_failed',semantic_pending=ok,images=images)
  elif model=='microsoft/trellis':
   artifacts=data.get('artifacts',[]);decoded=base64.b64decode(artifacts[0].get('base64','')) if len(artifacts)==1 else b'';ok=bool(artifacts and artifacts[0].get('finishReason')=='SUCCESS' and inspect_stl(decoded));out.update(success=ok,result='native_stl_mesh_semantics_pending' if ok else 'native_3d_mesh_check_failed',semantic_pending=ok,output_sha256=hashlib.sha256(decoded).hexdigest())
  else:
   text=json.dumps(data);out['synthetic_response_excerpt']=text[:1800];ok,evidence=inspect_solver(data);out.update(success=ok,result='valid_native_two_node_solver' if ok else 'native_solver_semantic_review_pending',evidence=evidence,semantic_pending=not ok)
 except Exception as error:out['result']=type(error).__name__
 finally:out['seconds']=round(time.monotonic()-start,3)
 return out
