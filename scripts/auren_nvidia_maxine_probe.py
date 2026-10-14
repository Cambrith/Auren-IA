"""Exact public Maxine function IDs; files and independent speech verification."""
def probe(row,sample,cfg,asset):
 import base64,json,subprocess
 import auren_exhaustive_probe as audit
 from auren_native_media_probe import inspect_media
 args={'operation':row['operation'],'function_id':row['native_function_id'],'key':cfg.api_key,'audio_path':str(asset/'pt.wav'),'video_path':str(asset/'video-detection.mp4')}
 args['feature']=row.get('native_maxine_feature')
 if row.get('native_function_version_id'):args['function_version_id']=row['native_function_version_id']
 try:out=json.loads(subprocess.run([str(audit.ROOT/'.cavren/audit-riva-runtime/bin/python'),str(audit.ROOT/'scripts/auren_nvidia_maxine_transport.py')],input=json.dumps(args),capture_output=True,text=True,timeout=35,check=True).stdout)
 except subprocess.TimeoutExpired:return {'at':audit.now(),'sample':sample,'real_call':True,'success':False,'result':'native_grpc_deadline_unknown','cost_class':'unknown','seconds':35}
 except (subprocess.CalledProcessError,ValueError):return {'at':audit.now(),'sample':sample,'real_call':False,'success':False,'result':'isolated_transport_startup_failed','cost_class':'unknown','seconds':0}
 out.update(at=audit.now(),sample=sample,function_id=row['native_function_id'])
 if args.get('function_version_id'):out['requested_function_version_id']=args['function_version_id']
 if out.get('audio_base64'):
  raw=base64.b64decode(out.pop('audio_base64'))
  try:out['media']=inspect_media(raw,'.wav');check=audit.verify_speech(raw,'pt','auren esta pronta bom dia');out.update(semantic_asr=check,auxiliary_call_count=int(check.get('real_call',False)),success=bool(check.get('success')),result='valid_native_enhancement_speech_preservation' if check.get('success') else 'native_enhancement_semantic_pending',noise_reduction_quality_tested=False)
  except ValueError:out.update(success=False,result='native_enhancement_audio_decode_failed')
 return out
