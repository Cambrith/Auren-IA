"""Export current profile candidates without inference or conversations."""
import json
from pathlib import Path
from integration.auren_profiles import DEFINITIONS
from integration.auren_tasks import recommended
from integration.auren_fallback import candidates,cooldowns
from integration.lunvri_connections import connection_settings,validated_catalog,STATE
from integration.auren_routing import effort_for
from auren_curated_probe import atomic,now
def main():
 models=validated_catalog(json.loads((STATE/'models.json').read_text())['models']);settings=connection_settings();rows=[]
 for task,spec in DEFINITIONS.items():
  if task=='auto':continue
  for p in spec['profiles']:
   profile=p['id'];mode=profile if profile in ('ether','impeto','insight','arquiteto') else 'ether';recommendation=recommended(task,mode,profile)
   job={'mode_id':mode,'mode_options':{'manual_route':'','billing_confirmed':False},'messages':[{'role':'user','content':'Pedido sintético de checagem da seleção.'}],'auren_task':task,'lunvri_image_generation':task=='image','auren_evidence_policy':True,'auren_recommended_route':(recommendation or '').removeprefix('cavren:'),'max_tokens':1536,'auren_image_profile':profile if task=='image' else 'balanced','auren_transcribe_language':profile if task=='transcribe' else 'auto','auren_image_operation':'text_to_image'}
   routes=[m['cavren']['route_id'] for m in candidates(job,models,settings,cooldowns())]
   rows.append({'task':task,'profile_id':profile,'name':p['name'],'recommended':recommendation,'eligible_current_order':routes,'effort':effort_for(routes[0],mode) if routes else None})
 atomic(Path('reports/auren-scoped-selection-2026-10-14.json'),{'at':now(),'method':'Dry selection only, no new inference. Availability/cooldowns may change. Image eligibility has historical transport evidence; current quality failures are in the separate practical report.','profiles':rows})
 print(len(rows),'profiles;',[(r['name'],r['eligible_current_order'][:1]) for r in rows if r['task']=='image'])
if __name__=='__main__':main()
