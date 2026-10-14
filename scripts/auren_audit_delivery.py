"""Evidence-only conditional profile review; never edits production route policy."""
import collections,csv,json,os,statistics,sys,tempfile
from pathlib import Path
import auren_exhaustive_probe as audit

def failure_kind(row):
    if row['status']=='not_tested':return 'operation_not_called_or_native_contract_not_confirmed'
    if row['status']=='valid':return 'criterion_passed'
    if row['status']=='partial_validity':return 'limited_output_validity'
    statuses=[s.get('http_status') for s in row['evidence'][-row['required_samples']:]]
    if 402 in statuses:return 'credit_or_payment_required'
    if 429 in statuses:return 'rate_or_quota_limit_observed_not_total_quota_measurement'
    if any(s in [401,403] for s in statuses):return 'authentication_or_permission_denied'
    if any(s in [404,410] for s in statuses):return 'route_unavailable_or_retired'
    if any(s in [400,422] for s in statuses):return 'native_contract_or_provider_precondition_requires_review'
    if any(s and s>=500 for s in statuses):return 'provider_server_error'
    if row['status']=='inconclusive':return 'incomplete_transport_output_or_test'
    return 'synthetic_content_criterion_failed'

def deliver(run):
    doc=audit.read(run/'complete.json');rows=doc['rows'];bench=audit.read(run/'benchmarks-reviewed.json',{});cards={v['model']:v for v in bench.get('models',[])}
    for row in rows:
        row['observed_result_kind']=failure_kind(row)
        name=row['requested_model'];card=cards.get(name)
        if card:
            row['publisher_benchmark_reference']={**card,'deployment_equivalence_confirmed':False,'locally_reproduced':False,'claim_scope':'Exact publisher model name only; not a score of this provider deployment or successful inference.'}
        else:row['publisher_benchmark_reference']=None
    audit.atomic(run/'complete.json',doc)
    fields=list(dict.fromkeys(key for row in rows for key in row if key!='evidence'))
    fd,tmp=tempfile.mkstemp(dir=run,prefix='.complete-csv-')
    with os.fdopen(fd,'w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows({key:json.dumps(value,ensure_ascii=False) if isinstance(value,(dict,list)) else value for key,value in row.items() if key!='evidence'} for row in rows)
        handle.flush();os.fsync(handle.fileno())
    os.replace(tmp,run/'complete.csv')
    definitions=audit.read(audit.ROOT/'src/lib/utils/aurenProfiles.json');profiles=[]
    from integration.auren_routing import MODE_ROUTES
    from integration.auren_tasks import models_for
    op_map={'chat':'text','code':'code','documents':'documents','research':'text','image':'image','speech':'speech','transcribe':'transcribe'}
    valid={row['key']:row for row in rows if row['success']}
    for task,definition in definitions.items():
        if task=='auto':continue
        current=set(models_for(task));op=op_map[task]
        for profile in definition['profiles']:
            ordered=list(MODE_ROUTES.get(profile['id'],())) if task in ['chat','code','documents','research'] else [v.removeprefix('cavren:') for v in sorted(current)]
            checked=[]
            for route in ordered:
                row=valid.get(route+'::'+op)
                if not row:continue
                checked.append({'route':route,'operation':op,'evidence_key':row['key'],'currently_eligible_by_existing_policy':'cavren:'+route in current,'reported_cost_class':row['cost_class'],'median_probe_seconds':statistics.median(row['sample_times_seconds']),'free_access_proven':row['free_access_proven_in_probe'],'limits':'Small synthetic criterion only; no broad quality, stability or quota claim.'})
            api_candidates=[{'route':row['provider']+':'+row['requested_model'],'evidence_key':row['key'],'cost_class':row['cost_class'],'native_language':row.get('native_language'),'required_before_use':'Confirm exact production adapter, price, language and remaining account allowance.'} for row in rows if row['success'] and row['operation']==op and 'cavren:'+row['provider']+':'+row['requested_model'] not in current]
            note='Keep current order; retain only rows satisfying the existing policy and current native operation evidence. Do not promote paid or unknown-cost candidates automatically.'
            if task=='research':note+=' Search, citations and retrieval pipeline require their own end-to-end evidence; text probe alone does not validate research.'
            if task=='documents':note+=' Native PDF support remains separate from extracted-text document handling.'
            if task=='speech':note+=' Vox requires verified pt-BR voice and independent Portuguese ASR, not English-only synthesis.'
            if task=='transcribe':note+=' Match explicit Portuguese/English/detection requirement to tested languages; no inference of multilingual coverage.'
            profiles.append({'task':task,'id':profile['id'],'name':profile['name'],'description':profile['description'],'conditional_existing_candidates':checked,'additional_api_candidates':api_candidates,'recommendation':note,'production_changed':False})
    audit.atomic(run/'profile-recommendations.json',{'at':audit.now(),'profiles':profiles,'count':len(profiles),'methodology':'23 existing profile definitions, task-native criteria, existing policy eligibility and observed timing. No universal quality ranking; no production promotion.'})
    lines=['# Auren — revisão condicional dos 23 perfis','', 'A ordem e os nomes existentes foram preservados. Os resultados abaixo orientam uma decisão posterior; nenhum perfil ou adaptador de produção foi alterado. Uma resposta sintética curta não mede qualidade ampla nem prova gratuidade ou cota.','', '| Tarefa | Perfil | Rotas atuais com operação aprovada | Observação |','|---|---|---|---|']
    for p in profiles:
        names=', '.join(v['route'] for v in p['conditional_existing_candidates']) or 'Nenhuma confirmada nesta rodada entre as preferências atuais'
        lines.append('| '+p['task']+' | '+p['name']+' | '+names+' | '+('Exige evidência própria de busca e fontes' if p['task']=='research' else 'Conferir idioma e operação de áudio' if p['task'] in ['speech','transcribe'] else 'Critério sintético limitado; aplicar política existente')+' |')
    lines+=['','As alternativas adicionais estão registradas integralmente em profile-recommendations.json, incluindo custo desconhecido e compatibilidade a confirmar. Benchmarks publicados em benchmarks-reviewed.json descrevem o modelo e o método do editor; não demonstram qualidade, pesos equivalentes ou acesso dessa implantação.','', 'Nenhum modelo passou a integrar o automático por ter retornado HTTP 200.']
    (run/'PROFILE-REVIEW.md').write_text('\n'.join(lines)+'\n')
    categories=collections.Counter(row['observed_result_kind'] for row in rows);audit.atomic(run/'result-kinds.json',{'at':audit.now(),'operations':len(rows),'observed_result_kinds':dict(categories),'publisher_cards_reviewed':len(cards),'profile_count':len(profiles),'scope_exhaustive_certified':False})
    print(json.dumps({'profiles':len(profiles),'categories':dict(categories)},ensure_ascii=False))

if __name__=='__main__':deliver(Path(sys.argv[1]))
