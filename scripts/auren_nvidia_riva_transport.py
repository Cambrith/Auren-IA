"""Native bounded Riva calls in an isolated audit runtime; secrets only on stdin."""
import base64,hashlib,io,json,sys,time,wave
import grpc,riva.client
from riva.client.proto import riva_asr_pb2 as asr,riva_tts_pb2 as tts
args=json.load(sys.stdin);started=time.monotonic();out={'real_call':False,'success':False,'cost_class':'unknown','transport':'grpc','seconds':0}
try:
 metadata=[['function-id',args['function_id']],['authorization','Bearer '+args['key']]]
 if args.get('function_version_id'):metadata.append(['function-version-id',args['function_version_id']])
 auth=riva.client.Auth(use_ssl=True,uri='grpc.nvcf.nvidia.com:443',metadata_args=metadata)
 if args['operation'] in ['transcribe','live']:
  with wave.open(args['audio_path'],'rb') as wav:
   rate=wav.getframerate();audio=wav.readframes(wav.getnframes());channels=wav.getnchannels();width=wav.getsampwidth()
  if channels!=1 or width!=2 or len(audio)/rate/2>4:raise ValueError('Synthetic fixture must be mono PCM16 and at most four seconds')
  config=asr.RecognitionConfig(encoding=riva.client.AudioEncoding.LINEAR_PCM,sample_rate_hertz=rate,language_code=args['language'],max_alternatives=1,enable_automatic_punctuation=True)
  service=riva.client.ASRService(auth);request=asr.RecognizeRequest(config=config,audio=audio);out['real_call']=True
  if args['operation']=='transcribe':responses=[service.stub.Recognize(request,metadata=auth.get_auth_metadata(),timeout=20)]
  else:
   config_stream=asr.StreamingRecognitionConfig(config=config,interim_results=False)
   def requests():
    yield asr.StreamingRecognizeRequest(streaming_config=config_stream)
    for start in range(0,len(audio),rate//5*2):yield asr.StreamingRecognizeRequest(audio_content=audio[start:start+rate//5*2])
   responses=service.stub.StreamingRecognize(requests(),metadata=auth.get_auth_metadata(),timeout=20)
  text=' '.join(v.alternatives[0].transcript for response in responses for v in response.results if v.alternatives)
  out.update(transcript=text,transcript_sha256=hashlib.sha256(text.encode()).hexdigest(),result='native_transcript_received')
 elif args['operation']=='voices':
  service=riva.client.SpeechSynthesisService(auth);out['real_call']=True;response=service.stub.GetRivaSynthesisConfig(tts.RivaSynthesisConfigRequest(),metadata=auth.get_auth_metadata(),timeout=20)
  out.update(result='native_voice_configuration',configs=[{'name':v.model_name,'parameters':dict(v.parameters)} for v in response.model_config])
 elif args['operation']=='translation':
  from riva.client.proto import riva_nmt_pb2 as nmt,riva_nmt_pb2_grpc as nmt_grpc
  request=nmt.TranslateTextRequest(texts=['Good morning. There are seven blue circles.'],source_language='en',target_language='de');out['real_call']=True
  response=nmt_grpc.RivaTranslationStub(auth.channel).TranslateText(request,metadata=auth.get_auth_metadata(),timeout=20)
  out.update(result='native_translation_received',translations=[{'text':v.text,'language':v.language} for v in response.translations])
 elif args['operation']=='speech':
  service=riva.client.SpeechSynthesisService(auth);request=tts.SynthesizeSpeechRequest(text=args.get('text','Auren is ready. Good morning.'),language_code=args['language'],voice_name=args.get('voice',''),encoding=riva.client.AudioEncoding.LINEAR_PCM,sample_rate_hz=22050)
  out['real_call']=True;response=service.stub.Synthesize(request,metadata=auth.get_auth_metadata(),timeout=20);raw=response.audio
  if len(raw)>22050*2*10:raise ValueError('Speech output exceeds ten-second audit cap')
  buffer=io.BytesIO()
  with wave.open(buffer,'wb') as wav:wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(22050);wav.writeframes(raw)
  out.update(audio_base64=base64.b64encode(buffer.getvalue()).decode(),audio_seconds=len(raw)/22050/2,result='native_speech_received')
 else:raise ValueError('Unsupported native operation')
except grpc.RpcError as error:
 out.update(result='native_grpc_'+error.code().name.lower(),grpc_status=error.code().name,provider_error=(error.details() or '').replace(args['key'],'<redacted>')[:500])
except Exception as error:out.update(result=type(error).__name__)
out['seconds']=round(time.monotonic()-started,3);print(json.dumps(out))
