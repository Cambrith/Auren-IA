"""Recheck the three integrated audio routes; public/synthetic samples only."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import base64,json,time
from datetime import datetime,timezone
from integration.auren_validation import STATE
from integration import auren_speech,auren_transcribe


def main():
 path=STATE/'audio_probes_2026-10-13.json';data={'records':{}}
 tests=[('speech','cavren:nvidia:magpie-tts-multilingual'),('transcribe','cavren:cohere:cohere-transcribe-03-2026'),('transcribe','cavren:mistral:voxtral-mini-latest')]
 for task,id in tests:
  samples=[]
  for index in range(2):
   events=[];start=time.monotonic();row={'date':datetime.now(timezone.utc).isoformat()}
   content='Auren está pronta para conversar em português.' if task=='speech' else [{'type':'input_audio','input_audio':{'format':'wav','data':base64.b64encode((STATE/'benchmark-speech.wav').read_bytes()).decode()}}]
   job={'generation_id':'synthetic-audio-probe','mode_options':{'manual_route':id.removeprefix('cavren:')},'mode_id':'ether','messages':[{'role':'user','content':content}],'prompt':content if isinstance(content,str) else 'Transcreva o áudio','auren_transcribe_language':'en','auren_deadline':time.monotonic()+45}
   def observe(event):
    # Store only booleans/short synthetic transcript checks, never base64 audio.
    if event['type']=='generation.files':events.append({'audio':bool(event.get('files'))})
    if event['type']=='generation.delta':events.append({'brooklyn':'brooklyn' in event.get('text','').lower()})
   try:
    (auren_speech.run if task=='speech' else auren_transcribe.run)(job,lambda m:m,output=observe)
    ok=any(e.get('audio') if task=='speech' else e.get('brooklyn') for e in events)
    row.update(ok=ok,code='ok' if ok else 'audio_check_failed')
   except Exception as error:row.update(ok=False,code=getattr(error,'code',type(error).__name__))
   row['seconds']=round(time.monotonic()-start,3);samples.append(row);print(task,id,index+1,row['code'],row['seconds'],flush=True);time.sleep(3)
  data['records'][id]={'task':task,'samples':samples}
  tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.chmod(0o600);tmp.replace(path)

if __name__=='__main__':main()
