"""Bounded native WebSocket probes; credentials arrive only through stdin.

No URLs, authentication, raw replies, or session tokens are emitted. Only
synthetic audio is read. Uses the existing preview runtime, with no install.
"""
import base64,hashlib,io,json,re,subprocess,sys,time,unicodedata,wave
import httpx
from urllib.parse import quote
import websocket

def coverage(text,expected):
 norm=''.join(c for c in unicodedata.normalize('NFD',text.lower()) if unicodedata.category(c)!='Mn')
 tokens=re.findall(r'\w+',norm);wanted=expected.split()
 return sum(word in tokens for word in wanted)/len(wanted)

def pcm(path):
 return subprocess.run(['ffmpeg','-v','error','-i',path,'-f','s16le','-acodec','pcm_s16le','-ac','1','-ar','16000','-'],capture_output=True,check=True,timeout=10).stdout

def live_music(cfg):
 started=time.monotonic();deadline=started+10;socket=None;audio=bytearray();out={'real_call':False,'success':False,'cost_class':'unknown','semantic_pending':True,'events':[],'max_session_seconds':10,'max_retained_audio_seconds':2}
 try:
  out['real_call']=True;socket=websocket.create_connection('wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateMusic?key='+cfg['key'],timeout=5)
  socket.send(json.dumps({'setup':{'model':'models/'+cfg['model']}}))
  while time.monotonic()<deadline:
   socket.settimeout(max(.1,min(3,deadline-time.monotonic())))
   try:
    opcode,raw=socket.recv_data(control_frame=True)
    if opcode==websocket.ABNF.OPCODE_CLOSE:
     out['close_code']=int.from_bytes(raw[:2],'big') if len(raw)>=2 else None;out['close_reason']=raw[2:].decode('utf-8','replace').replace(cfg['key'],'<redacted>')[:400];break
   except websocket.WebSocketTimeoutException:continue
   if opcode not in [websocket.ABNF.OPCODE_TEXT,websocket.ABNF.OPCODE_BINARY]:continue
   if not raw:break
   data=json.loads(raw);out['events'].extend(k for k in data if k in ['setupComplete','serverContent','filteredPrompt','error'])
   if 'setupComplete' in data:
    out['setup_complete']=True;socket.send(json.dumps({'clientContent':{'weightedPrompts':[{'text':'Quiet instrumental piano with a steady simple rhythm.','weight':1.0}]}}));socket.send(json.dumps({'musicGenerationConfig':{'bpm':90}}));socket.send(json.dumps({'playbackControl':'PLAY'}))
   if data.get('error'):out['result']='provider_error';break
   if data.get('filteredPrompt'):out['result']='censored';break
   for chunk in data.get('serverContent',{}).get('audioChunks',[]):
    audio.extend(base64.b64decode(chunk.get('data','')));out['audio_mime']=chunk.get('mimeType')
   if audio:
    socket.send(json.dumps({'playbackControl':'STOP'}));out['stop_sent']=True;break
  retained=audio[:384000];duration=len(retained)/(48000*2*2);out.update(audio_bytes=len(audio),retained_audio_seconds=duration,audio_sha256=hashlib.sha256(retained).hexdigest(),success=len(retained)>1000,result='valid_live_music_pcm_semantics_pending' if len(retained)>1000 else out.get('result','live_deadline_inconclusive'))
 except Exception as error:out['result']=type(error).__name__;out['http_status']=getattr(error,'status_code',None)
 finally:
  if socket:
   try:
    if not out.get('stop_sent'):socket.send(json.dumps({'playbackControl':'STOP'}));out['stop_sent']=True
    socket.close(timeout=2)
   except Exception:pass
  out.update(seconds=round(time.monotonic()-started,3),connection_closed=True)
 return out

def main():
 cfg=json.loads(sys.stdin.read())
 if cfg.get('operation')=='live_music':print(json.dumps(live_music(cfg)));return
 model=cfg['model'];provider=cfg.get('provider','gemini');key=cfg['key'];started=time.monotonic();deadline=started+25;socket=None
 result={'real_call':False,'success':False,'cost_class':'unknown','setup_complete':False,'turn_complete':False,'audio_bytes':0,'events':[]}
 audio=bytearray();text=[];mode='transcribe' if provider=='mistral' or 'transcribe-live' in model else 'translate' if 'live-translate' in model else 'robotics' if 'robotics' in model else 'agent';sent=False;extended='extended-thinking' in model
 try:
  result['real_call']=True
  if provider=='mistral':
   socket=websocket.create_connection('wss://api.mistral.ai/v1/audio/transcriptions/realtime?model='+quote(model,safe=''),header={'Authorization':'Bearer '+key},timeout=8)
   socket.send(json.dumps({'type':'session.update','session':{'audio_format':{'encoding':'pcm_s16le','sample_rate':16000}}}))
  else:
   version='v1alpha' if model.startswith('gemini-3.8-live') else 'v1beta'
   result['api_version']=version
   socket=websocket.create_connection('wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.'+version+'.GenerativeService.BidiGenerateContent?key='+key,timeout=8)
   setup={'model':'models/'+model,'generationConfig':{'responseModalities':['TEXT' if mode in ['transcribe','robotics'] else 'AUDIO']}}
   if mode=='transcribe':setup['inputAudioTranscription']={'languageCodes':['pt-BR']}
   elif mode=='translate':
    setup.update(inputAudioTranscription={},outputAudioTranscription={});setup['generationConfig']['translationConfig']={'targetLanguageCode':'en','echoTargetLanguage':False}
   else:setup['generationConfig']['maxOutputTokens']=512
   if model.startswith('gemini-3.8-live'):setup['generationConfig']['speechConfig']={'voiceConfig':{'prebuiltVoiceConfig':{'voiceName':'Puck'}}}
   if extended:setup['generationConfig']['thinkingConfig']={'thinkingLevel':'LOW'}
   socket.send(json.dumps({'setup':setup}))
  while time.monotonic()<deadline:
   socket.settimeout(min(8,max(.1,deadline-time.monotonic())))
   try:
    opcode,raw=socket.recv_data(control_frame=True)
    if opcode==websocket.ABNF.OPCODE_CLOSE:
     result['close_code']=int.from_bytes(raw[:2],'big') if len(raw)>=2 else None;result['close_reason']=raw[2:].decode('utf-8','replace').replace(cfg['key'],'<redacted>')[:400];break
   except websocket.WebSocketTimeoutException:
    if mode!='agent' and text:break
    continue
   if opcode not in [websocket.ABNF.OPCODE_TEXT,websocket.ABNF.OPCODE_BINARY]:continue
   if not raw:break
   data=json.loads(raw);event=data.get('type');result['events'].extend(k for k in data if k in ['setupComplete','serverContent','usageMetadata','error','goAway']);
   if event in ['session.created','session.updated','transcription.text.delta','transcription.done','error']:result['events'].append(event)
   if data.get('usageMetadata'):result['usage']={k:v for k,v in data['usageMetadata'].items() if k in ['totalTokenCount','promptTokenCount','responseTokenCount']}
   if data.get('error') or event=='error':result['result']='provider_error';break
   ready='setupComplete' in data or event in ['session.created','session.updated']
   if ready and not sent:
    result['setup_complete']=True;sent=True
    if mode=='agent':socket.send(json.dumps({'clientContent':{'turns':[{'role':'user','parts':[{'text':'Diga apenas: Bom dia.'}]}],'turnComplete':True}}))
    elif mode=='robotics':
     with open(cfg['image_path'],'rb') as fixture:frame=fixture.read()
     socket.send(json.dumps({'clientContent':{'turns':[{'role':'user','parts':[{'inlineData':{'mimeType':'image/jpeg','data':base64.b64encode(frame).decode()}},{'text':'Read the visible marker and count red circles and blue squares. Return only marker|red_count|blue_count.'}]}],'turnComplete':True}}))
    else:
     raw_pcm=pcm(cfg['audio_path']);result['input_audio_bytes']=len(raw_pcm)
     for offset in range(0,len(raw_pcm),6400):
      chunk=base64.b64encode(raw_pcm[offset:offset+6400]).decode()
      socket.send(json.dumps({'type':'input_audio.append','audio':chunk} if provider=='mistral' else {'realtimeInput':{'audio':{'data':chunk,'mimeType':'audio/pcm;rate=16000'}}}));time.sleep(.2)
     if provider=='mistral':
      socket.send(json.dumps({'type':'input_audio.flush'}));socket.send(json.dumps({'type':'input_audio.end'}))
     else:socket.send(json.dumps({'realtimeInput':{'audioStreamEnd':True}}))
   server=data.get('serverContent') or {}
   if provider=='mistral' and event=='transcription.text.delta':text.append(data.get('text',''))
   if mode=='transcribe' and server.get('inputTranscription'):text.append(server['inputTranscription'].get('text',''))
   if mode=='translate' and server.get('outputTranscription'):text.append(server['outputTranscription'].get('text',''))
   for part in server.get('modelTurn',{}).get('parts',[]):
    if mode=='robotics' and part.get('text') and not part.get('thought'):text.append(part['text'])
    inline=part.get('inlineData') or {}
    if inline.get('data'):audio.extend(base64.b64decode(inline['data']));result['audio_mime']=inline.get('mimeType')
   if len(audio)>3_000_000:result['result']='output_byte_budget';break
   interaction=data.get('interactionStatus',data.get('interaction_status'))
   if interaction:result['interaction_status']=interaction
   if extended and interaction=='IDLE' and audio:result['turn_complete']=True;result['interaction_complete']=True;break
   if event=='transcription.done' or server.get('turnComplete'):
    if not extended:result['turn_complete']=True
    if mode=='agent' and not extended:break
    if text:break
  result.update(audio_bytes=len(audio),audio_sha256=hashlib.sha256(audio).hexdigest(),text_sha256=hashlib.sha256(''.join(text).encode()).hexdigest(),mode=mode)
  if 'result' not in result:
   if mode=='agent':result.update(success=len(audio)>1000 and result['turn_complete'],semantic_pending=True,result='valid_live_audio_format_semantics_pending' if len(audio)>1000 and result['turn_complete'] else 'live_deadline_inconclusive')
   elif mode=='robotics':
    normalized=''.join(text).strip().replace(' ','');ok='PIXEL-739|2|1' in normalized
    result.update(success=ok,result='valid_live_robotics_visual_grounding' if ok else 'live_robotics_visual_check_failed' if text else 'live_deadline_inconclusive',semantic_pending=False)
   else:
    score=coverage(''.join(text),'auren esta pronta bom dia' if mode=='transcribe' else 'auren ready good morning');ok=score>=.8 and (mode=='transcribe' or len(audio)>1000)
    result.update(success=ok,token_coverage=score,result='valid_live_transcription' if ok and mode=='transcribe' else 'valid_translation_audio_and_provider_transcript' if ok else 'native_session_closed_without_output' if not text and not audio else 'live_semantic_check_failed',semantic_pending=mode=='translate')
  if len(audio)>1000 and mode in ['translate','agent'] and cfg.get('asr_key'):
   stream=io.BytesIO();match=re.search(r'rate=(\d+)',result.get('audio_mime',''));rate=int(match.group(1)) if match else 24000
   with wave.open(stream,'wb') as wav:wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(audio)
   result['auxiliary_call_count']=1
   try:
    check=httpx.post('https://api.mistral.ai/v1/audio/transcriptions',headers={'Authorization':'Bearer '+cfg['asr_key']},data={'model':'voxtral-mini-latest','language':'en' if mode=='translate' else 'pt'},files={'file':('synthetic-live.wav',stream.getvalue(),'audio/wav')},trust_env=False,timeout=15)
    result['semantic_asr_http_status']=check.status_code
    if check.status_code==200:
     transcript=check.json().get('text','');score=coverage(transcript,'good morning ready' if mode=='translate' else 'bom dia');result.update(semantic_asr_token_coverage=score,semantic_asr_sha256=hashlib.sha256(transcript.encode()).hexdigest())
     if score>=.8:
      result.update(success=mode=='translate' or result['turn_complete'],semantic_pending=False,result='valid_live_translation_and_independent_asr' if mode=='translate' else 'valid_live_audio_and_independent_asr' if result['turn_complete'] else 'live_audio_valid_completion_inconclusive')
     else:result.update(success=False,result='live_audio_semantic_check_failed',semantic_pending=False)
   except Exception as error:result['semantic_asr_error']=type(error).__name__
 except Exception as error:
  result['result']=type(error).__name__
  status=getattr(error,'status_code',None)
  if status:result['http_status']=status
 finally:
  if socket:
   try:socket.close(timeout=2)
   except Exception:pass
  result['seconds']=round(time.monotonic()-started,3);result['connection_closed']=True
 print(json.dumps(result))
if __name__=='__main__':main()
