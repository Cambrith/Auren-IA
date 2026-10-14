"""Add exact native function/operation identities from public NVIDIA examples."""
import fcntl,re,sys
from pathlib import Path
import auren_exhaustive_probe as audit
run=Path(sys.argv[1]);lock=(run/'.execution.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
matrix=audit.read(run/'matrix.json');journal=audit.read(run/'results.json');supp=audit.read(run/'supplemental-discovery.json');existing={v['key']:v for v in matrix['rows']};added=[];review=[]
for card in audit.read(run/'nvidia-api-examples.json')['models']:
 model=card['card_slug'];code='\n'.join(card.get('examples',[]));ids=card.get('function_ids',[]);ops=[]
 if ids:
  if 'transcribe_file_offline.py' in code or '/v1/audio/transcriptions' in code:ops.append('transcribe')
  if 'scripts/asr/transcribe_file.py' in code:ops.append('live')
  if 'scripts/tts/talk.py' in code:ops.append('speech')
  if 'scripts/nmt/nmt.py' in code:ops.append('translation')
 review.append({'provider':'nvidia','advertised_card':model,'source':card['source'],'http_status':card.get('http_status'),'native_function_ids':ids,'native_operations':ops,'operation_called':False,'state':'native_operations_added' if ops else 'native_contract_not_confirmed','pending':None if ops else 'Card does not yet have a confirmed bounded native transport in this audit. This is an explicit remaining discovery/implementation gap, not a model failure.'})
 for operation in ops:
  key='nvidia:'+model+'::'+operation;row=existing.get(key);fresh=row is None
  language=re.search(r'--language-code\s+([a-z]{2}-[A-Z]{2})',code);language=language.group(1) if language else 'en-US'
  if fresh:
   row={'key':key,'provider':'nvidia','requested_model':model,'operation':operation,'endpoint':'grpc.nvcf.nvidia.com:443','provenance':[card['source']],'contract_source':card['source'],'criterion':'Native finite synthetic audio, known transcript; synthesis also requires independent ASR. Translation checks seven blue circles in German.','required_samples':1,'blocker':None,'status':'not_tested','pending':'Native documented operation awaits bounded real probe.','declared_price':None,'benchmark':'not_confirmed_for_exact_version_in_new_round'};matrix['rows'].append(row);existing[key]=row;added.append(key)
   supp['models'].setdefault('nvidia:'+model,{'provider':'nvidia','model':model,'sources':[card['source']],'metadata':{'native_function_id':ids[0]}})
  row.update(native_function_id=ids[0],native_language=language)
  if language.startswith('zh'):
   row.update(native_audio_fixture='zh-synthetic.wav',native_expected_text='你好 早上好')
  elif language.startswith('es'):
   row.update(native_audio_fixture='es-synthetic.wav',native_expected_tokens=['hola','buenos','dias'])
  elif language.startswith('vi'):
   row.update(blocker='verified_vietnamese_fixture_pending',pending='Vietnamese-only route requires a Vietnamese gold audio sample. English/Portuguese fixtures are not substituted.')
  if operation=='speech':
   voice=re.search(r'--voice\s+"([^"]+)"',code)
   if voice:row['native_voice']=voice.group(1)
   if model=='resembleai/chatterbox-multilingual-tts':row.update(native_portuguese_voice='Chatterbox-Multilingual.pt-BR.Male',required_samples=2)
  if fresh:continue
  # Preserve finished work; reopen only the demonstrated validator correction.
  if model=='resembleai/chatterbox-multilingual-tts' and operation=='speech':
   record=journal['records'].get(key,{})
   if record.get('samples') and record['samples'][-1].get('result')=='native_speech_semantic_pending':
    record.setdefault('resumption_history',[]).append({'at':audit.now(),'reason':'Normalize expected and ASR text consistently; add Portuguese sample from confirmed voice configuration.'});record.update(terminal=False,retry_samples=[0,1])
supp['changes'].append({'at':audit.now(),'added_operations':added,'source':'51 advertised public NVIDIA card Try API pages, exact function ID and method examples.'})
audit.atomic(run/'matrix.json',matrix);audit.atomic(run/'results.json',journal);audit.atomic(run/'supplemental-discovery.json',supp);audit.atomic(run/'nvidia-additional-discovery-review.json',{'at':audit.now(),'candidates':review});print('added native operations',len(added))
