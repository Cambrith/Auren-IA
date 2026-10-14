"""Small native Maxine file streams. Official generated interfaces, isolated runtime."""
import base64,hashlib,json,math,subprocess,sys,time
from pathlib import Path
import grpc
args=json.load(sys.stdin);root=Path(__file__).resolve().parents[1];sdk=root/'.cavren/audit-maxine-clients';out={'real_call':False,'success':False,'cost_class':'unknown','transport':'grpc','seconds':0};started=time.monotonic()
try:
 with grpc.secure_channel('grpc.nvcf.nvidia.com:443',grpc.ssl_channel_credentials()) as channel:
  metadata=[('function-id',args['function_id']),('authorization','Bearer '+args['key'])]
  if args.get('function_version_id'):metadata.append(('function-version-id',args['function_version_id']))
  if args['operation'] in ['audio_enhance','audio_enhance_stream'] and args.get('feature')=='studiovoice':
   sys.path.insert(0,str(sdk/'studio-voice/interfaces/studio_voice'));import studiovoice_pb2 as p,studiovoice_pb2_grpc as g
   streaming=args['operation']=='audio_enhance_stream';rate=48000
   command=['ffmpeg','-v','error','-i',args['audio_path'],'-ac','1','-ar',str(rate)]
   if streaming:command+=['-af','apad=whole_dur=6','-t','6','-f','f32le','pipe:1']
   else:command+=['-c:a','pcm_s16le','-f','wav','pipe:1']
   raw=subprocess.run(command,capture_output=True,check=True,timeout=10).stdout
   if len(raw)>1200000:raise ValueError('Six-second synthetic audio cap')
   def requests():
    chunk=6*rate*4 if streaming else 65536
    for offset in range(0,len(raw),chunk):yield p.EnhanceAudioRequest(audio_stream_data=raw[offset:offset+chunk])
   out['real_call']=True;chunks=[];length=0
   for response in g.StudioVoiceStub(channel).EnhanceAudio(requests(),metadata=metadata,timeout=20):
    if response.HasField('audio_stream_data'):
     length+=len(response.audio_stream_data)
     if length>2000000:raise ValueError('Studio Voice output cap')
     chunks.append(response.audio_stream_data)
   audio=b''.join(chunks)
   if streaming:
    import numpy as np
    values=np.frombuffer(audio,dtype='<f4')
    if not len(values) or not np.isfinite(values).all():raise ValueError('Float audio missing or nonfinite')
    audio=subprocess.run(['ffmpeg','-v','error','-f','f32le','-ar',str(rate),'-ac','1','-i','pipe:0','-c:a','pcm_s16le','-f','wav','pipe:1'],input=audio,capture_output=True,check=True,timeout=10).stdout
   out.update(result='native_enhancement_audio_received',audio_base64=base64.b64encode(audio).decode(),audio_sha256=hashlib.sha256(audio).hexdigest(),native_mode='float32_stream_padded_six_seconds' if streaming else 'wav_file',sampling_rate=rate,model_configuration_selector_sent=False)
  elif args['operation']=='pose_estimation':
   sys.path.insert(0,str(sdk/'body-pose/interfaces'))
   from nvidia.ai4m.body_pose.v1 import body_pose_pb2 as p,body_pose_pb2_grpc as g
   raw=Path(args['video_path']).read_bytes()
   if len(raw)>1000000:raise ValueError('Two-second video cap')
   boxes=[p.FrameBoxes(frame_id=index,boxes=[p.BoundingBox(x=32,y=8,width=200,height=240,tracking_id=1)]) for index in range(48)]
   def requests():
    yield p.BodyPoseRequest(config=p.BodyPoseConfig(),tracked_bboxes=boxes)
    for offset in range(0,len(raw),65536):yield p.BodyPoseRequest(video_data=raw[offset:offset+65536])
   out['real_call']=True;frames=[];flushed=False;valid=True
   for response in g.BodyPoseServiceStub(channel).EstimateBodyPose(requests(),metadata=metadata,timeout=20):
    flushed=flushed or response.stream_flushed
    if response.ready:
     frames.append(response.frame_id)
     if len(frames)>48:raise ValueError('Pose output frame cap')
     valid=valid and response.frame_id<48 and len(response.bodies)==1
     for body in response.bodies:
      valid=valid and body.bbox.tracking_id==1 and all(len(value)==77 for value in [body.keypoints_2d,body.keypoints_3d,body.keypoint_confidence,body.joint_rotations,body.rest_pose])
      numbers=list(body.keypoint_confidence)+[v for point in list(body.keypoints_2d)+list(body.keypoints_3d)+list(body.rest_pose) for v in ([point.x,point.y,point.z] if hasattr(point,'z') else [point.x,point.y])]+[v for q in body.joint_rotations for v in [q.x,q.y,q.z,q.w]]
      valid=valid and all(math.isfinite(v) for v in numbers)
   ok=bool(frames) and valid and flushed and len(frames)==len(set(frames));out.update(success=ok,result='native_pose_format_only' if ok else 'native_pose_container_check_failed',semantic_pending=ok,output_frames=len(frames),stream_flushed=flushed,fixture_kind='synthetic graphic with caller-supplied boxes; anatomical ground truth absent',anatomical_quality_tested=False)
  elif args['operation']=='audio_enhance':
   sys.path.insert(0,str(sdk/'bnr/interfaces/bnr'));import bnr_pb2 as p,bnr_pb2_grpc as g
   raw=subprocess.run(['ffmpeg','-v','error','-i',args['audio_path'],'-ac','1','-ar','48000','-c:a','pcm_s16le','-f','wav','pipe:1'],capture_output=True,check=True,timeout=10).stdout
   if len(raw)>500000:raise ValueError('Synthetic audio input byte cap')
   def requests():
    yield p.EnhanceAudioRequest(config=p.EnhanceAudioConfig(intensity_ratio=.5))
    for offset in range(0,len(raw),65536):yield p.EnhanceAudioRequest(audio_stream_data=raw[offset:offset+65536])
   out['real_call']=True;chunks=[];length=0
   for response in g.BNRStub(channel).EnhanceAudio(requests(),metadata=metadata,timeout=20):
    if response.HasField('audio_stream_data'):
     length+=len(response.audio_stream_data)
     if length>1000000:raise ValueError('Audio output byte cap')
     chunks.append(response.audio_stream_data)
   audio=b''.join(chunks);out.update(result='native_enhancement_audio_received',audio_base64=base64.b64encode(audio).decode(),audio_sha256=hashlib.sha256(audio).hexdigest())
  elif args['operation']=='video_detection':
   sys.path.insert(0,str(sdk/'synthetic-video-detector/interfaces'))
   # The advertised function uses the legacy Maxine v1 wire, not AI4M v2.
   from nvidia.maxine.syntheticvideodetector.v1 import syntheticvideodetector_pb2 as p,syntheticvideodetector_pb2_grpc as g
   raw=Path(args['video_path']).read_bytes()
   if len(raw)>1000000:raise ValueError('Synthetic two-second video byte cap')
   def requests():
    for offset in range(0,len(raw),65536):yield p.DetectSyntheticVideoRequest(video_file_data=raw[offset:offset+65536])
   out['real_call']=True;frames=[];final=None
   for response in g.SyntheticVideoDetectorServiceStub(channel).DetectSyntheticVideo(requests(),metadata=metadata,timeout=20):
    if response.HasField('clip_result'):
     v=response.clip_result;frames.append({'id':v.index,'logit':v.logit})
    if len(frames)>100:raise ValueError('Two-second frame output cap')
    if response.HasField('final_result'):
     v=response.final_result;final={'mean_logit':v.logit,'synthetic_probability':v.probability,'total_clips':v.total_clips}
   finite=bool(final) and all(math.isfinite(v['logit']) for v in frames) and math.isfinite(final['mean_logit']) and math.isfinite(final['synthetic_probability']) and 0<=final['synthetic_probability']<=1 and final['total_clips']>0
   ok=finite and final['synthetic_probability']<.5;out.update(success=ok,result='valid_native_non_ai_graphic_video_control' if ok else 'native_video_negative_control_check_failed',final=final,clip_count=len(frames),probabilities_finite=finite,fixture_kind='programmatically drawn graphic, not AI-generated',positive_class_tested=False)
  else:raise ValueError('Native operation unsupported')
except grpc.RpcError as error:out.update(result='native_grpc_'+error.code().name.lower(),grpc_status=error.code().name,provider_error=(error.details() or '').replace(args['key'],'<redacted>')[:500])
except Exception as error:out.update(result=type(error).__name__)
out['seconds']=round(time.monotonic()-started,3);print(json.dumps(out))
