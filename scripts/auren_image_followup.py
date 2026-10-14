"""Two bounded practical checks per selected route; no stored conversations."""
import sys,json,time,base64,hashlib,argparse
from pathlib import Path
from dataclasses import replace
import httpx
from cavren.models import Message
from integration.lunvri_connections import connection_settings
from integration.lunvri_manual import generate_images
from auren_curated_probe import atomic,now
P=Path('reports/auren-image-practical-2026-10-14/results.json')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--model',choices=('AbsoluteReality','Abyss OrangeMix'),default='AbsoluteReality');args=parser.parse_args()
 data=json.loads(P.read_text()); settings=connection_settings(); cfg=replace(settings.providers['aihorde'],model=args.model)
 for name in ('Deliberate::english','stable_diffusion::english'):
  data['records'][name].update(semantic_success=False,semantic_review='Visual inspection: blue concentric disks or rays; no single three-dimensional sphere on a plain white background.')
 atomic(P,data)
 for index in range(2):
  key=cfg.model+'::'+str(index)
  if key in data['records']:continue
  prompt='Photograph of one solid blue ball on an empty white studio background, soft shadow under the ball, no text, no patterns.'
  row={'at':now(),'provider':'aihorde','model':cfg.model,'operation':'text_to_image','real_call':True,'reported_cost_usd':None,'events':[],'semantic_review':'Pending visual inspection.'}
  start=time.monotonic();data['records'][key]=row;atomic(P,data)
  def progress(e):
   row['events'].append({k:e.get(k) for k in ('state','queue_position','wait_time','eligible_workers','started_at','done')});atomic(P,data)
  try:
   with httpx.Client(trust_env=False) as client:
    files,_=generate_images(client,cfg,[Message('user',prompt)],prompt,progress=progress,job={'generation_id':'auren-image-followup','auren_deadline':time.monotonic()+100,'auren_image_parameters':{'width':512,'height':512,'steps':20}})
   raw=base64.b64decode(files[0]['url'].split(',',1)[1]);out=P.parent/(cfg.model.replace(' ','-')+'-'+str(index)+'.webp');out.write_bytes(raw)
   row.update(success=True,file=str(out),sha256=hashlib.sha256(raw).hexdigest())
  except Exception as e:row.update(success=False,code=getattr(e,'code',type(e).__name__),semantic_success=False)
  row['seconds']=round(time.monotonic()-start,3);atomic(P,data);print(key,row['success'],row['seconds'],flush=True)
 data['finished_at']=now();atomic(P,data)
if __name__=='__main__':main()
