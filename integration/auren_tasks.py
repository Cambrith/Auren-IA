"""Auren task definitions and conservative local intent detection.

Task execution remains separate from Cavren's chat/fim/agentic enum.
"""
import json
import re
from integration.auren_validation import STATE, verified, evidence

DEFINITIONS = {
 'chat': {'id':'chat','name':'Conversar','description':'Ideias, dúvidas e textos.','output':'text'},
 'image': {'id':'image','name':'Gerar imagens','description':'Criar imagens com geradores medidos.','output':'image'},
 'documents': {'id':'documents','name':'Analisar documentos','description':'Ler e responder sobre anexos.','output':'text'},
 'code': {'id':'code','name':'Gerar código','description':'Produzir e revisar código; execução não incluída.','output':'text'},
 'research': {'id':'research','name':'Pesquisa aprofundada','description':'Pesquisar em etapas e sintetizar fontes.','output':'text'},
 'speech': {'id':'speech','name':'Gerar voz','description':'Narrar texto em português com a voz validada.','output':'audio'},
 'transcribe': {'id':'transcribe','name':'Transcrever áudio','description':'Converter áudio anexado em texto.','output':'text'},
}

def task_evidence():
    try:return json.loads((STATE/'validation_tasks.json').read_text()).get('tasks',{})
    except (OSError,ValueError,AttributeError):return {}

def models_for(task):
    if task in ('chat','image'):
        kind='image' if task=='image' else 'text'
        return [r['id'] for r in evidence().values() if r.get('kind')==kind and verified(r['id'],kind)]
    tested=task_evidence()
    if task=='speech':
        record=tested.get('speech',{})
        return [record['model']] if record.get('ok') and verified(record.get('model',''),'speech') else []
    if task=='transcribe':return list({r['model'] for k,r in tested.items() if k.startswith('transcribe_') and r.get('ok') and verified(r['model'],'transcribe')})
    record=tested.get(task,{})
    result=[record['model']] if record.get('ok') and verified(record.get('model',''),'text') else []
    # Category-specific real probes extend the legacy single-model evidence.
    try:
        from datetime import datetime
        probes=json.loads((STATE/'validation_categories.json').read_text()).get('records',{})
        revisions=json.loads((STATE/'provider_policy.json').read_text()).get('validation_not_before',{})
        for row in probes.values():
            id=row.get('id',''); provider=id.removeprefix('cavren:').split(':',1)[0]
            if row.get('task')!=task or row.get('ok') is not True or not verified(id,'text'):continue
            if revisions.get(provider) and datetime.fromisoformat(row['date'])<datetime.fromisoformat(revisions[provider]):continue
            if id not in result:result.append(id)
    except (OSError,ValueError,KeyError,TypeError,AttributeError):pass
    return result


def tasks():
    tested=task_evidence()
    result=[]
    for key,definition in DEFINITIONS.items():
        usable=any(record.get('kind')==('image' if key=='image' else 'text') and verified(record['id'],record['kind']) for record in evidence().values()) if key in ('chat','image') else tested.get(key,{}).get('ok') is True
        if usable and models_for(key): result.append({**definition,'model_ids':models_for(key),'verified':True,'tested_at':tested.get(key,{}).get('date')})
    if result:result.insert(0,{'id':'auto','name':'Automática','description':'Detectar a intenção entre tarefas gratuitas verificadas.','output':'auto','verified':True})
    return result

def intent_text(prompt):
    """Normalize instructions only; quoted/document/code payloads are untrusted data."""
    import unicodedata
    text=re.sub(r'<documento_dados>.*?</documento_dados>|```.*?```|`[^`]*`|"[^"\n]*"|“[^”]*”|\'[^\'\n]*\'', ' ', prompt, flags=re.S|re.I)
    return ''.join(c for c in unicodedata.normalize('NFD',text.casefold()) if not unicodedata.combining(c)).strip()


def automatic_context(prompt, task):
    text=intent_text(prompt)
    text=re.sub(r'\bnao\s+(?:seja\s+)?(?:breve|rapido|rapida|detalhado|detalhada)\b',' ',text)
    fast=bool(re.search(r'\b(rapid[oa]|rapidamente|rascunho|seja breve|resposta curta|objetivamente|resuma em|em poucas palavras|quick|brief)\b',text))
    detailed=bool(re.search(r'\b(detalhad[oa]|passo a passo|profundamente|alta definicao|justifique|evidencias|demonstre|prove|analise criticamente|trade.?offs?|step by step)\b',text))
    engineering=bool(re.search(r'\b(arquitetura de software|api|backend|frontend|banco de dados|debug|depuracao|refator|software|sistema distribuido)\w*',text))
    profile='rapid' if fast and not detailed else 'detailed' if detailed and not fast else 'balanced'
    mode={'code':'arquiteto','documents':'insight','research':'insight'}.get(task, 'arquiteto' if engineering else 'impeto' if fast and not detailed else 'insight' if detailed and not fast else 'ether')
    return mode,profile


INTENT_RULES = (
 ('image', r'\b(crie|criar|gere|gerar|desenhe|ilustre|faca|renderize|create|generate|draw)\b.{0,100}?\b(imagem|imagens|foto|ilustracao|desenho|retrato|logo|paisagem|cartaz|banner|poster|image|picture)\b'),
 ('research', r'\b(pesquise|pesquisar|busque na web|procure na internet|investigue|pesquisa aprofundada|pesquisa agentica|agente de pesquisa|deep research|search the web|research)\b'),
 ('code', r'\b(crie|gere|implemente|escreva|corrija|desenvolva|depure|refatore|revise|debug|write|implement|fix)\b.{0,100}?\b(codigo|funcao|script|programa|python|javascript|typescript|sql|api|backend|frontend|bug|code|function)\b'),
 ('documents', r'\b(analise|resuma|leia|extraia|compare|sintetize|summarize|read|analyze)\b.{0,100}?\b(documentos?|pdf|arquivos?|anexos?|planilha|contrato|document|attachment)\b'),
 ('speech', r'\b(gere|crie|faca|produza|narre|leia em voz alta|converta.{0,60}em voz|generate|create)\b(?:.{0,100}?\b(voz|narracao|voice|speech)\b)?'),
 ('transcribe', r'\b(transcreva|transcrever|transcribe|converta.{0,60}(audio|gravacao).{0,30}(texto|text))\b'),
)


def classify(prompt, messages):
    """Explainable local rules; no extra API call or probabilistic confidence claim."""
    text=intent_text(prompt)
    latest=next((m for m in reversed(messages) if m.get('role')=='user'),{})
    content=latest.get('content',[])
    has_audio=isinstance(content,list) and any(p.get('type')=='input_audio' for p in content)
    # Explanations, hypothetical instructions and negated clauses must not create media.
    explanation=r'\b(explique|como funciona|como (posso|faco|criar|gerar|implementar)|o que (e|significa)|qual a diferenca|compare os conceitos|how to|explain)\b'
    if re.search(explanation,text):
        return {'task':'chat','reason':'explanation','matches':[]}
    clauses=re.split(r'[.;!?\n]|\bmas\b',text)
    positive=[c for c in clauses if not re.search(r'\b(nao|nunca|sem|do not|dont)\b.{0,35}\b(crie|gere|faca|desenhe|ilustre|draw|pesquise|transcreva|narre|escreva|implemente|gerar|criar|quero|preciso|gostaria|generate|create)\b',c) and not re.match(r'\s*(se |caso |quando |if )',c)]
    instructions=' . '.join(positive)
    matches=[]
    for task,pattern in INTENT_RULES:
        # Voice needs an explicit output request; generic "crie" alone is insufficient.
        if task=='speech' and not re.search(r'\b(voz|narracao|voice|speech|narre)\b',instructions):continue
        if re.search(pattern,instructions):matches.append(task)
    if not matches and re.search(r'\b(quero|preciso de|gostaria de)\s+(?:uma?\s+)?(?:imagem|ilustracao|foto|retrato|logo)\b',instructions):matches=['image']
    if not matches and re.search(r'\b(desenhe|ilustre|draw)\b',instructions):matches=['image']
    if not matches and re.fullmatch(r'(continue(?: a resposta| de onde parou)?|corrija isso|ajuste isso|melhore isso|complete o codigo)[.! ]*',instructions):
        users=[m for m in messages if m.get('role')=='user']
        if len(users)>1:
            previous=users[-2].get('content','')
            if isinstance(previous,list):previous=' '.join(p.get('text','') for p in previous if p.get('type')=='text')
            prior=classify(previous,[])
            if prior['task'] in ('code','documents','research'):
                return dict(prior,reason='text_continuation')
    if has_audio and not matches and re.search(r'\b(para texto|em texto|o que foi dito)\b',instructions):matches=['transcribe']
    if not matches and isinstance(content, list):
        types = {part.get('type') for part in content}
        if 'input_file' in types or any('<documento_dados>' in p.get('text', '').casefold() for p in content):
            return {'task':'documents','reason':'document_attachment','matches':[]}
        if types.intersection({'image_url','input_video','input_audio'}):
            return {'task':'chat','reason':'media_attachment','matches':[]}
    unsupported=bool(re.search(r'\b(gere|crie|faca|execute|rode)\b.{0,70}\b(video|musica|comando|terminal)\b',instructions))
    if unsupported:return {'task':'chat','reason':'unsupported','matches':matches}
    if len(matches)!=1:return {'task':'chat','reason':'ambiguous' if matches else 'conversation','matches':matches}
    return {'task':matches[0],'reason':'explicit_request','matches':matches}


def detect(prompt, messages):
    return classify(prompt,messages)['task']


def recommended(task, mode='ether', profile=None, required=()):
    if task == 'image':
        from integration.auren_images import rank
        try:
            from integration.auren_settings import preferences
            eligible = set(models_for('image'))
            models = json.loads((STATE/'models.json').read_text()).get('models', [])
            choices = [m for m in models if m['id'] in eligible and m.get('cavren', {}).get('provider') == 'aihorde']
            job = {'auren_image_profile': profile or 'balanced',
                   'auren_image_preferred_route': preferences().get('image_model_id', '').removeprefix('cavren:')}
            if choices: return min(choices, key=lambda m: rank(m['cavren'], job))['id']
        except (OSError, ValueError, KeyError, TypeError):
            pass
    if task in ('chat','code','documents','research'):
        from integration.auren_routing import ordered_models
        choices=ordered_models(task,mode,required)
        if choices:return choices[0]
    if task=='transcribe' and profile in ('auto','pt','en'):
        # Cohere requires a declared language. Keep Mistral for detection.
        choices=models_for(task)
        providers=('mistral',) if profile=='auto' else ('cohere','mistral')
        for provider in providers:
            match=next((id for id in choices if id.startswith('cavren:'+provider+':')),None)
            if match:return match
    tested=task_evidence(); suggested=tested.get(task,{}).get('model')
    if suggested in models_for(task):return suggested
    from integration.auren_validation import measured_seconds
    choices=sorted(models_for(task),key=lambda id:(measured_seconds(id,'image' if task=='image' else task) or 9999,id))
    return choices[0] if choices else None
