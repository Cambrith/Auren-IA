"""Journal adapter for exact Riva function IDs found in official public examples."""
def probe(row,sample,cfg,asset):
 import base64,hashlib,json,re,subprocess
 import auren_exhaustive_probe as audit
 body={'operation':row['operation'],'function_id':row['native_function_id'],'language':row['native_language'],'voice':row.get('native_voice'),'audio_path':str(asset/row.get('native_audio_fixture','en-synthetic.wav')),'key':cfg.api_key}
 if row.get('native_function_version_id'):body['function_version_id']=row['native_function_version_id']
 if row['operation']=='speech' and sample==1 and row.get('native_portuguese_voice'):
  body.update(language='pt-BR',voice=row['native_portuguese_voice'],text='Auren está pronta. Bom dia.')
 try:
  out=json.loads(subprocess.run([str(audit.ROOT/'.cavren/audit-riva-runtime/bin/python'),str(audit.ROOT/'scripts/auren_nvidia_riva_transport.py')],input=json.dumps(body),text=True,capture_output=True,timeout=30,check=True).stdout)
 except subprocess.TimeoutExpired:return {'at':audit.now(),'sample':sample,'real_call':True,'success':False,'result':'native_grpc_deadline_unknown','cost_class':'unknown','seconds':30}
 except (subprocess.CalledProcessError,ValueError):return {'at':audit.now(),'sample':sample,'real_call':False,'success':False,'result':'isolated_transport_startup_failed','cost_class':'unknown','seconds':0}
 out.update(at=audit.now(),sample=sample,function_id=row['native_function_id'],native_language=body['language'])
 if body.get('function_version_id'):out['requested_function_version_id']=body['function_version_id']
 if row['operation'] in ['transcribe','live'] and 'transcript' in out:
  import unicodedata
  text=out.pop('transcript');normalized=''.join(c for c in unicodedata.normalize('NFD',text.lower()) if unicodedata.category(c)!='Mn');tokens=re.findall(r'\w+',normalized);wanted=row.get('native_expected_tokens',['auren','is','ready','good','morning']);coverage=sum(t in tokens for t in wanted)/len(wanted)
  if row.get('native_expected_text'):
   import difflib
   reference=''.join(re.findall(r'\w+',row['native_expected_text']));observed=''.join(tokens);coverage=difflib.SequenceMatcher(None,reference,observed).ratio();out['metric']='normalized_character_similarity'
  out.update(success=coverage>=.8,token_coverage=coverage,result='valid_native_grpc_transcription' if coverage>=.8 else 'native_transcription_check_failed')
 if row['operation']=='translation' and out.get('translations'):
  text=out['translations'][0]['text'].lower();ok='sieben' in text and 'blau' in text and 'kreis' in text and 'morgen' in text and len(text)<1000;out.update(success=ok,result='valid_native_grpc_translation' if ok else 'native_translation_check_failed')
 if row['operation']=='speech' and 'audio_base64' in out:
  raw=base64.b64decode(out.pop('audio_base64'));out['audio_sha256']=hashlib.sha256(raw).hexdigest();check=audit.verify_speech(raw,'pt' if body['language']=='pt-BR' else 'en','auren esta pronta bom dia' if body['language']=='pt-BR' else 'auren is ready good morning');out.update(semantic_asr=check,auxiliary_call_count=int(check.get('real_call',False)),success=bool(check.get('success')),result='valid_native_grpc_speech_and_asr' if check.get('success') else 'native_speech_semantic_pending',semantic_pending=not check.get('success'))
 return out
