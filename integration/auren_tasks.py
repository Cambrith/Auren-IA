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
    return [record['model']] if record.get('ok') and verified(record.get('model',''),'text') else []


def tasks():
    tested=task_evidence()
    result=[]
    for key,definition in DEFINITIONS.items():
        usable=any(record.get('kind')==('image' if key=='image' else 'text') and verified(record['id'],record['kind']) for record in evidence().values()) if key in ('chat','image') else tested.get(key,{}).get('ok') is True
        if usable and models_for(key): result.append({**definition,'model_ids':models_for(key),'verified':True,'tested_at':tested.get(key,{}).get('date')})
    if result:result.insert(0,{'id':'auto','name':'Automática','description':'Detectar a intenção entre tarefas gratuitas verificadas.','output':'auto','verified':True})
    return result

def intent_text(prompt):
    text=re.sub(r'<documento_dados>.*?</documento_dados>', '', prompt, flags=re.S).casefold().strip()
    return re.sub(r'`[^`]*`|"[^"]*"', '', text)

def automatic_context(prompt, task):
    text=intent_text(prompt)
    fast=bool(re.search(r'\b(rápid[oa]|rapidamente|rascunho|seja breve|resposta curta|objetivamente)\b',text))
    detailed=bool(re.search(r'\b(detalhad[oa]|passo a passo|profundamente|alta definição|justifique com evidências)\b',text))
    profile='rapid' if fast and not detailed else 'detailed' if detailed and not fast else 'balanced'
    mode={'code':'arquiteto','documents':'insight','research':'insight'}.get(task, 'impeto' if fast and not detailed else 'insight' if detailed and not fast else 'ether')
    return mode,profile

def detect(prompt, messages):
    """Explicit creation verb + object; quotes and ambiguity default to chat."""
    text=intent_text(prompt)
    has_audio=any(isinstance(m.get('content'),list) and any(p.get('type')=='input_audio' for p in m['content']) for m in messages if m.get('role')=='user')
    if has_audio and re.search(r'\btranscreva\b',text):return 'transcribe'
    if text.startswith(('explique','o que','como funciona','qual a diferença','compare os conceitos')):return 'chat'
    rules=[('image',r'\b(crie|gere|desenhe|ilustre|faça|renderize)\b.{0,60}\b(imagem|foto|ilustração|desenho|retrato|logo|paisagem)\b'),
           ('research',r'\b(pesquisa aprofundada|pesquise profundamente|investigue com fontes|pesquise e compare|pesquise com ferramentas|pesquisa agêntica|agente de pesquisa|deep research)\b'),
           ('code',r'\b(crie|gere|implemente|escreva|corrija|desenvolva)\b.{0,70}\b(código|função|script|programa|python|javascript|typescript|sql)\b'),
           ('documents',r'\b(analise|resuma|leia|extraia)\b.{0,60}\b(documento|pdf|arquivo|anexo|planilha)\b'),
           ('speech',r'\b(gere|crie|faça|produza)\b.{0,60}\b(voz|narração)\b'),
           ('transcribe',r'\b(transcreva|transcrever)\b.{0,60}\b(áudio|audio|gravação|fala)\b')]
    matches=[task for task,pattern in rules if re.search(pattern,text)]
    return matches[0] if len(matches)==1 else 'chat'


def recommended(task, mode='ether'):
    tested=task_evidence(); suggested=tested.get(task,{}).get('model')
    if suggested and verified(suggested,'image' if task=='image' else 'speech' if task=='speech' else 'transcribe' if task=='transcribe' else 'text'):return suggested
    choices=[r for r in evidence().values() if r['kind']==('image' if task=='image' else 'text') and verified(r['id'],r['kind'])]
    if mode in ('insight','arquiteto') and task != 'image':
        curated=['nvidia/nemotron-3.5-lightning-30b-a3b','command-a-03-2025','@cf/qwen/qwen3-30b-a3b-fp8','@cf/google/gemma-4-26b-a4b-it']
        choices.sort(key=lambda r:(curated.index(r['model']) if r['model'] in curated else len(curated),r.get('mean_seconds') or 9999))
    else:choices.sort(key=lambda r:r.get('mean_seconds') or 9999)
    return choices[0]['id'] if choices else None
