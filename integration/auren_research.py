"""Bounded source search; explicit official-provider requests stay on those domains."""
import re
from urllib.parse import urlparse

OFFICIAL_DOMAINS={
    'cohere':'docs.cohere.com', 'cloudflare':'developers.cloudflare.com',
    'mistral':'docs.mistral.ai', 'openrouter':'openrouter.ai',
    'nvidia':'docs.nvidia.com', 'gemini':'ai.google.dev',
    'openai':'platform.openai.com', 'anthropic':'docs.anthropic.com',
}

def plan(prompt):
    prompt=re.sub(r'<documento_dados>.*?</documento_dados>', '', prompt, flags=re.S).strip()
    text=prompt.casefold()
    official=any(term in text for term in ('fontes oficiais','documentação oficial','documentacao oficial'))
    domains=[domain for name,domain in OFFICIAL_DOMAINS.items() if re.search(r'\b'+re.escape(name)+r'\b',text)] if official else []
    if domains:
        topic='pricing free trial rate limits' if any(term in text for term in ('cota','gratuit','preço','preco','custo','limite')) else prompt
        return [f'site:{domain} {topic}' for domain in domains[:3]], tuple(domains[:3])
    return [prompt,prompt+' documentação oficial',prompt+' evidências limitações'], ()

def accepts(source, domains):
    if not domains:return True
    host=(urlparse(source['url']).hostname or '').casefold()
    return any(host==domain or host.endswith('.'+domain) for domain in domains)


def model_plan(client, config, prompt, deadline):
    """One verified Cohere tool-planning call; only bounded web queries are allowed."""
    import json,time
    from integration.auren_tasks import task_evidence
    from integration.auren_validation import verified
    from cavren.errors import CavrenError
    from cavren.providers import http_error
    base,domains=plan(prompt)
    record=task_evidence().get('agent_research_planner',{})
    if config.name!='cohere' or not record.get('ok') or record.get('model')!='cavren:cohere:'+config.model or not verified(record['model'],'text'):
        return base,domains,False
    remaining=deadline-time.monotonic()
    if remaining<=0:raise CavrenError('timeout','O prazo da pesquisa foi atingido.')
    prompt=re.sub(r'<documento_dados>.*?</documento_dados>', '', prompt, flags=re.S).strip()
    instructions='Planeje até três consultas curtas de pesquisa usando somente search_docs. Não execute ações externas nem código.'
    if domains:instructions+=' Use consultas curtas em inglês para estes sites de documentação técnica, com site: para estes domínios oficiais: '+', '.join(domains)+'.'
    if domains and any(term in prompt.casefold() for term in ('cota','gratuit','preço','preco','custo','limite')):
        instructions+=' Inclua o nome do provedor e termos concretos como API trial rate limits pricing; evite a consulta genérica free tier.'
    response=client.post('https://api.cohere.com/v2/chat',headers={'Authorization':'Bearer '+config.api_key},
                        json={'model':config.model,'messages':[{'role':'system','content':instructions},{'role':'user','content':prompt}],
                              'tools':[{'type':'function','function':{'name':'search_docs','description':'Busca documentação e fontes na web. Entrada: consulta curta de pesquisa.',
                                       'parameters':{'type':'object','properties':{'query':{'type':'string'}},'required':['query']}}}],
                              'max_tokens':512},timeout=min(remaining,45))
    if response.status_code!=200:raise http_error(response.status_code,provider='cohere')
    queries=[]
    try:
        calls=response.json().get('message',{}).get('tool_calls',[])
        if len(calls)>3:raise ValueError()
        for call in calls:
            function=call.get('function',{})
            value=json.loads(function['arguments'])
            query=value.get('query')
            if function.get('name')!='search_docs' or set(value)!={'query'} or not isinstance(query,str) or not 1<=len(query)<=512:raise ValueError()
            query=query.strip()
            if domains:
                sites=re.findall(r'\bsite:([^\s]+)',query)
                if not sites or not all(site.casefold() in domains for site in sites):raise ValueError()
            if query and query not in queries:queries.append(query)
    except (KeyError,ValueError,AttributeError,TypeError):return base,domains,False
    return (queries,domains,True) if queries else (base,domains,False)
