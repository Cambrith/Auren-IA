"""Audit public model cards for every catalog route; never call an inference API.

A card containing evaluation terms is a research lead, not a reviewed score.
Do not transfer a parent's benchmark to an unresolved alias or fine-tune.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import csv,json,re,hashlib,concurrent.futures
from datetime import datetime,timezone
import httpx
from integration.lunvri_connections import STATE,validated_catalog
from integration.auren_validation import model_evidence,verified

OWNERS={'qwen':'Qwen','meta':'meta-llama','meta-llama':'meta-llama','z-ai':'zai-org','nvidia':'nvidia','moonshotai':'moonshotai','mistralai':'mistralai','cohere':'CohereLabs','google':'google','ibm-granite':'ibm-granite','openai':'openai','minimax':'MiniMaxAI','liquid':'LiquidAI','microsoft':'microsoft','deepseek-ai':'deepseek-ai','tencent':'tencent','stepfun':'stepfun-ai','arcee-ai':'arcee-ai','nousresearch':'NousResearch','bytedance-seed':'ByteDance-Seed','xiaomi':'XiaomiMiMo','cognitivecomputations':'cognitivecomputations','inclusionai':'inclusionAI','black-forest-labs':'black-forest-labs','perceptron':'PerceptronAI','inception':'InceptionAI'}
EXACT={
 'command-a-plus-05-2026':'CohereLabs/command-a-plus-05-2026-bf16',
 'command-a-03-2025':'CohereLabs/command-a-03-2025',
 'command-r7b-12-2024':'CohereLabs/command-r7b-12-2024',
 'command-a-reasoning-08-2025':'CohereLabs/command-a-reasoning-08-2025',
 'nvidia/nemotron-3-super-120b-a12b':'nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16',
 'nvidia/nemotron-3-ultra-550b-a55b':'nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16',
 'ministral-14b-2512':'mistralai/Ministral-3-14B-Instruct-2512-BF16',
 'ministral-8b-2512':'mistralai/Ministral-3-8B-Instruct-2512',
 'ministral-3b-2512':'mistralai/Ministral-3-3B-Instruct-2512',
 'mistral-small-3.1-24b-instruct':'mistralai/Mistral-Small-3.1-24B-Instruct-2503',
 'llama-3.1-8b-instruct-fp8':'meta-llama/Llama-3.1-8B-Instruct',
 'llama-3.3-70b-instruct-fp8-fast':'meta-llama/Llama-3.3-70B-Instruct',
 'qwen3-30b-a3b-fp8':'Qwen/Qwen3-30B-A3B',
 'llama-4-scout-17b-16e-instruct':'meta-llama/Llama-4-Scout-17B-16E-Instruct',
 'gemma-4-26b-a4b-it':'google/gemma-4-26B-A4B-it',
 'gemma-4-31b-it':'google/gemma-4-31B-it',
}
INDEXES={
 'anthropic':'https://www.anthropic.com/system-cards',
 'openai':'https://openai.com/research/',
 'gemini':'https://deepmind.google/models/model-cards/',
 'groq':'https://console.groq.com/docs/models',
 'mistral':'https://docs.mistral.ai/getting-started/models/models_overview',
 'ollama':'https://ollama.com/search',
 'openrouter':'https://openrouter.ai/models',
 'aihorde':'https://github.com/Haidra-Org/AI-Horde-image-model-reference',
}

def source_for(info):
    provider=info['provider'];model=info['model_id'].removeprefix('@cf/').removesuffix(':free').removesuffix(':cloud')
    leaf=model.split('/')[-1]
    alias=leaf.endswith('latest') or model.startswith('~') or model in ('openrouter/free','openrouter/auto')
    if alias:return INDEXES.get(provider,'https://huggingface.co/models'),'unresolved_alias'
    if '/' in model:
        owner=model.split('/',1)[0]
        if owner=='anthropic':return INDEXES['anthropic'],'manufacturer_index_only'
        if owner=='openai' and not leaf.startswith('gpt-oss'):return INDEXES['openai'],'manufacturer_index_only'
    if provider=='aihorde':return INDEXES['aihorde'],'checkpoint_reference'
    if model.startswith('gemini-'):
        return 'https://deepmind.google/models/model-cards/'+leaf.replace('.','-')+'/','candidate_card'
    card=EXACT.get(model) or EXACT.get(leaf)
    if not card and '/' in model:
        owner,slug=model.split('/',1)
        if owner in OWNERS:card=OWNERS[owner]+'/'+slug
    if not card and provider=='cohere':card='CohereLabs/'+model
    if not card and provider=='mistral':card='mistralai/'+model
    if not card and provider=='zai':card='zai-org/'+model
    if card:
        scope='base_model_reference_not_exact_deployment' if any(token in model.lower() for token in ('fp8','lora','quantized')) else 'candidate_card'
        return 'https://huggingface.co/'+card,scope
    return INDEXES.get(provider,'https://huggingface.co/models'),'provider_index_only'


def fetch(url):
    try:
        request=url.replace('https://huggingface.co/','https://huggingface.co/')
        if url.startswith('https://huggingface.co/') and not url.endswith('/models'):
            request=url+'/raw/main/README.md'
        with httpx.Client(trust_env=False,follow_redirects=True,timeout=12) as client:r=client.get(request)
        text=r.text if r.status_code==200 else ''
        terms=sorted(set(re.findall(r'GPQA|MMLU(?:-Pro)?|SWE[- ]?[Bb]ench|DeepSWE|Terminal[- ]Bench|LiveCodeBench|HumanEval|IFBench|AA-LCR|HLE|GenEval|DPG[- ]Bench|WER|BLEU|COMET',text,re.I)))
        return {'http_status':r.status_code,'evaluation_terms':terms,'sha256':hashlib.sha256(text.encode()).hexdigest() if text else None}
    except httpx.HTTPError:return {'http_status':None,'evaluation_terms':[],'error':'source_unreachable'}


def main():
    models=validated_catalog(json.loads((STATE/'models.json').read_text())['models'])
    rows=[]
    for model in models:
        info=model.get('cavren',{})
        if not info.get('provider'):continue
        source,scope=source_for(info)
        rows.append({'id':model['id'],'provider':info['provider'],'model':info['model_id'],'source':source,'scope':scope,'image_only':bool(info.get('image_only')),'task_operations':info.get('task_operations',[])})
    urls=set(row['source'] for row in rows)
    cache={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures={executor.submit(fetch,url):url for url in urls}
        for future in concurrent.futures.as_completed(futures):
            cache[futures[future]]=future.result()
            if len(cache)%50==0:print('Fontes consultadas',len(cache),'de',len(urls),flush=True)
    checked=datetime.now(timezone.utc).isoformat()
    for row in rows:
        found=cache[row['source']];row.update(found)
        row['benchmark_status']='evaluation_section_found_unreviewed' if row['scope'] in ('candidate_card','base_model_reference_not_exact_deployment') and found.get('http_status')==200 and found.get('evaluation_terms') else 'not_confirmed_in_consulted_source'
        kind='image' if row['image_only'] else 'speech' if 'speech' in row['task_operations'] else 'transcribe' if 'transcribe' in row['task_operations'] else 'text'
        record=model_evidence(row['id'],kind)
        row.update(checked_at=checked,local_free_verified=verified(row['id'],kind),local_status=record.get('status','not_tested'),local_test_at=record.get('verified_at'),local_seconds=record.get('mean_seconds'))
    output=ROOT/'reports/AUREN-BENCHMARKS-INVENTARIO-2026-10-13.json'
    output.write_text(json.dumps({'checked_at':checked,'method':'Public exact/version model-card lookup; indexes and unresolved aliases explicitly identified. No provider inference calls. Evaluation terms are leads, not numeric score verification.','routes':rows},ensure_ascii=False,indent=2)+'\n')
    with output.with_suffix('.csv').open('w',newline='') as f:
        fields=['provider','model','benchmark_status','scope','source','http_status','evaluation_terms','local_free_verified','local_status','local_test_at','local_seconds','checked_at']
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader()
        for row in rows:writer.writerow({**row,'evaluation_terms':' / '.join(row['evaluation_terms'])})
    print('Inventário',len(rows),'rotas;',len(urls),'fontes públicas; seções de avaliação',sum(row['benchmark_status']=='evaluation_section_found_unreviewed' for row in rows),flush=True)

if __name__=='__main__':main()
