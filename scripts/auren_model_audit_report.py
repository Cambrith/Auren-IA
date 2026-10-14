"""Publish only allowlisted model test metadata; never export credentials or replies."""
from pathlib import Path
import sys,json,csv,collections
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from integration.lunvri_connections import STATE,validated_catalog
from integration.auren_validation import model_evidence,verified
from integration.auren_tasks import models_for
from integration.auren_routing import ordered_models

def read(name):return json.loads((STATE/name).read_text())
def main():
 models=validated_catalog(read('models.json')['models'])
 probes=read('mode_probes_2026-10-13.json')['records'];zero=read('openrouter_zero_probes_2026-10-13.json')['records'];research=read('research_mode_probes_2026-10-13.json')['records'];audio=read('audio_probes_2026-10-13.json')['records']
 sources=json.loads((ROOT/'reports/AUREN-BENCHMARKS-INVENTARIO-2026-10-13.json').read_text());source_by={r['id']:r for r in sources['routes']}
 rows=[];baseline=collections.defaultdict(lambda:[0,0,0])
 for model in models:
  info=model.get('cavren',{});id=model['id'];provider=info.get('provider')
  if not provider:continue
  operations=info.get('task_operations',[])
  kinds=['speech'] if 'speech' in operations else ['transcribe'] if 'transcribe' in operations else (['image'] if info.get('image_only') else ['text'])
  if info.get('capabilities',{}).get('image_generation') and 'image' not in kinds:kinds.append('image')
  for kind in kinds:
   record=model_evidence(id,kind);samples=record.get('samples',[])
   probe=probes.get('chat:'+id,{}) if kind=='text' else {}
   z=zero.get(id,{}) if kind=='text' else {}
   if kind in ('speech','transcribe'):samples=audio.get(id,{}).get('samples',[])
   successes=[s['seconds'] for s in samples if s.get('ok') and isinstance(s.get('seconds'),(int,float))]
   codes=sorted({str(s.get('code','unknown')) for s in samples})
   called=probe.get('status')=='called' if kind=='text' else bool(samples)
   ok=probe.get('ok') if kind=='text' and called else any(s.get('ok') for s in samples) if samples else None
   duration=probe.get('seconds') if kind=='text' and called else round(sum(successes)/len(successes),3) if successes else None
   status=probe.get('code') if kind=='text' and called else ' / '.join(codes) if codes else 'não testado'
   free=verified(id,kind)
   cost='gratuito com limites, validado' if free else 'não comprovado neste teste'
   if 'quota_exhausted' in codes or probe.get('code')=='quota_exhausted':cost='sem cota/crédito disponível; não habilitado no automático'
   if not called and z.get('status')=='called':
    status='teto zero: '+str(z.get('code'));duration=z.get('seconds');cost='teto de preço zero; acesso gratuito não comprovado' if not z.get('ok') else 'resposta sob teto zero; sem promoção automática por este teste isolado'
   source=source_by.get(id,{})
   scope=source.get('scope','not_confirmed')
   if any(token in info['model_id'].lower() for token in ('fp8','lora','quantized')) and scope=='candidate_card':scope='base_model_reference_not_exact_deployment'
   row={'provider':provider,'model':info['model_id'],'kind':kind,'called':called or z.get('status')=='called','works_in_probe':ok if called else z.get('ok'),'free_eligible':free,'cost':cost,'seconds':duration,'status':status,'successful_samples':len(successes),'samples':len(samples) if kind!='text' else int(called),'test_dates':' / '.join(sorted({s.get('date','') for s in samples})) if kind!='text' else probe.get('date') or z.get('date'),'limits':'Não se mediu teto de cota; nenhum modelo foi declarado ilimitado.','code_ok':probes.get('code:'+id,{}).get('ok'),'documents_ok':probes.get('documents:'+id,{}).get('ok'),'research_ok':research.get(id,{}).get('ok'),'benchmark_scope':scope,'benchmark_status':source.get('benchmark_status','not_confirmed'),'benchmark_source':source.get('source','')}
   rows.append(row)
   if kind=='text':baseline[provider][0]+=1;baseline[provider][1]+=int(called);baseline[provider][2]+=int(probe.get('ok') is True)
 output=ROOT/'reports/AUREN-TESTES-MODELOS-2026-10-13.csv'
 with output.open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
 summary={'date':'2026-10-13','catalog_routes':len(models)-1,'operation_rows':len(rows),'baseline_by_provider':dict(baseline),'active_tasks':{task:len(models_for(task)) for task in ('chat','code','documents','research','image','speech','transcribe')},'effective_chat_orders':{m:ordered_models('chat',m) for m in ('ether','impeto','insight','arquiteto')},'zero_price_calls':sum(r.get('status')=='called' for r in zero.values()),'zero_price_pass':sum(r.get('ok') is True for r in zero.values()),'zero_price_image_skips':sum(r.get('status')=='not_called' for r in zero.values()),'source_routes':len(sources['routes']),'unique_sources':len({r['source'] for r in sources['routes']}),'evaluation_leads':sum(r['benchmark_status']=='evaluation_section_found_unreviewed' for r in sources['routes'])}
 (ROOT/'reports/AUREN-TESTES-RESUMO-2026-10-13.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
