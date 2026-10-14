"""Dedicated OpenRouter speech and streaming conversational audio probes."""
import base64,hashlib,json,time

def audio_probe(client,row,sample,cfg,asset,run):
 import auren_exhaustive_probe as audit
 from auren_native_media_probe import inspect_media,audit_error
 start=time.monotonic();op=row['operation'];model=row['requested_model'];result={'at':audit.now(),'sample':sample,'real_call':False,'success':False,'cost_class':'unknown'};raw=bytearray();headers=audit.headers('openrouter',cfg)
 try:
  if op=='speech':
   public_model=row.get('public_alias',model)
   contract=next((m for m in audit.read(run/'openrouter-speech-contract-discovery.json',{}).get('models',[]) if m['id']==public_model),{})
   voices=contract.get('supported_voices') or [];voice=next((v for v in voices if v.startswith('en-US-')),voices[0] if voices else None)
   body={'model':model,'input':'Auren is ready. Good morning.','response_format':'mp3'}
   if voice:body['voice']=voice
   if public_model=='bytedance-seed/seed-audio-1-0':body['input']='Say exactly: Auren is ready. Good morning.'
   result.update(real_call=True,voice=voice,language='en',input_characters=len(body['input']))
   response=client.post(row['endpoint'],headers=headers,json=body,timeout=30)
   if response.status_code>=400:
    result.update(audit.safe_response(response,response.json(),cfg),result=audit_error(response.status_code));return result
   result.update(http_status=response.status_code,content_type=response.headers.get('content-type'),generation_id=response.headers.get('x-generation-id'));raw.extend(response.content)
   if result.get('generation_id'):
    details=client.get('https://openrouter.ai/api/v1/generation',headers=headers,params={'id':result['generation_id']},timeout=10);result['cost_lookup_http_status']=details.status_code
    if details.status_code==200:
     info=details.json().get('data',{});result.update(reported_cost_usd=info.get('total_cost'),resolved_model=info.get('model'),resolved_provider=info.get('provider_name'))
  else:
   music='lyria' in model;prompt='Create a short instrumental piano piece with a steady rhythm, without lyrics.' if music else 'Say exactly in English: Auren is ready. Good morning.'
   body={'model':model,'messages':[{'role':'user','content':prompt}],'modalities':['text','audio'],'audio':{'voice':'alloy','format':'mp3'},'stream':True,'provider':{'allow_fallbacks':False},'max_tokens':512}
   if music:body['audio'].pop('voice',None)
   result.update(real_call=True,stream_completed=False)
   with client.stream('POST',row['endpoint'],headers=headers,json=body,timeout=30) as response:
    result['http_status']=response.status_code
    if response.status_code>=400:response.read();result.update(audit.safe_response(response,response.json(),cfg),result=audit_error(response.status_code));return result
    for line in response.iter_lines():
     if time.monotonic()-start>35:result['result']='audio_stream_deadline_inconclusive';break
     if not line.startswith('data:'):continue
     fragment=line[5:].strip()
     if fragment=='[DONE]':result['stream_completed']=True;break
     data=json.loads(fragment)
     if data.get('error'):result.update(audit.safe_response(response,data,cfg),result='provider_error');break
     if data.get('usage') or data.get('model'):result.update(audit.safe_response(response,data,cfg))
     for choice in data.get('choices',[]):
      audio=choice.get('delta',{}).get('audio') or {}
      if audio.get('data'):raw.extend(base64.b64decode(audio['data']))
     if len(raw)>4_000_000:result['result']='audio_output_byte_budget';break
  if not raw:result.setdefault('result','missing_audio_output');return result
  media=inspect_media(raw,'.mp3');ok=media['duration_seconds']>0 and any(s.get('codec_type')=='audio' for s in media['streams']);result.update(success=ok,result='valid_audio_container_semantics_pending' if ok else 'invalid_audio',media=media,semantic_pending=True)
  if op=='audio_output' and 'lyria' in model:result['result']='valid_music_container_semantics_pending';return result
  if ok:
   asr=audit.verify_speech(bytes(raw),'en','auren ready good morning',audio_format='mp3');result.update(semantic_asr=asr,auxiliary_call_count=int(asr.get('real_call',False)))
   if asr.get('success'):result.update(semantic_pending=False,result='valid_speech_and_asr')
   elif asr.get('result')=='semantic_asr_failed':result.update(success=False,semantic_pending=False,result='speech_semantic_check_failed')
 except Exception as error:result['result']=type(error).__name__
 finally:
  result['seconds']=round(time.monotonic()-start,3);cost=result.get('reported_cost_usd');result['cost_class']='positive_reported' if cost and cost>0 else 'zero_reported' if cost==0 else 'unknown'
 return result
