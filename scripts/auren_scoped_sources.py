"""Public-source lookup for the frozen Gemini/Groq inventory, without inference."""
import json, re, csv, concurrent.futures
from pathlib import Path
from auren_benchmark_sources import source_for, fetch
from datetime import datetime,timezone
RUN=Path('reports/auren-gemini-groq-2026-10-14-r2')
def main():
 snap=json.loads((RUN/'snapshot.json').read_text()); rows=[]
 for key,info in snap['models'].items():
  provider,model=key.split(':',1)
  source,scope=source_for({'provider':provider,'model_id':model})
  if provider=='gemini':
   cards={'gemini-3.5-flash-lite':'gemini-3-5-flash-lite','gemini-3.8-flash':'gemini-3-8-flash','gemini-3-flash':'gemini-3-flash','gemini-3.8':'gemini-3-8-audio','gemini-3.5':'gemini-3-5-audio','gemini-embedding':'gemini-embedding','nano-banana-2.1':'nano-banana-2-1','gemini-robotics-er-2':'gemini-robotics-er-2'}
   match=next((v for k,v in cards.items() if model.startswith(k)),None)
   if match:source='https://deepmind.google/models/model-cards/'+match+'/'
   if model.startswith('gemini-3.8') and any(s in model for s in ('tts','audio','live')):
    source='https://deepmind.google/models/model-cards/gemini-3-8-audio/';scope='audio_family_reference_not_exact_deployment'
   if model.startswith('gemini-3.5') and any(s in model for s in ('tts','audio','live')):
    source='https://deepmind.google/models/model-cards/gemini-3-5-audio/';scope='audio_family_reference_not_exact_deployment'
   if 'latest' in model:source='https://ai.google.dev/gemini-api/docs/models';scope='unresolved_alias'
  rows.append({'provider':provider,'model':model,'source':source,'scope':scope,'benchmark_status':'not_confirmed','note':'Publisher evaluations do not validate this account or deployment; aliases are not assigned another version score.'})
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
  urls=sorted({r['source'] for r in rows}); results=dict(zip(urls,pool.map(fetch,urls)))
 for row in rows:
  row.update(results[row['source']]); row['benchmark_status']='evaluation_section_found_unreviewed' if row.get('evaluation_terms') and row['scope']!='unresolved_alias' else 'not_confirmed_in_consulted_source'
 out={'checked_at':datetime.now(timezone.utc).isoformat(),'method':'Every frozen model ID has a primary-source lookup or explicit missing benchmark. Numerical comparisons are reviewed separately; section detection is not a score. No inference calls.','routes':rows}
 (RUN/'benchmark-sources-current.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print(len(rows),'model IDs researched;',len(urls),'public sources')
if __name__=='__main__':main()
