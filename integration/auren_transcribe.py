"""Documented Cohere/Mistral/Groq speech-to-text transports, with vault credentials."""
import base64
import time
from cavren.errors import CavrenError
from integration.lunvri_manual import emit
from integration.lunvri_connections import connection_settings

ROUTES={'cohere:cohere-transcribe-03-2026':'https://api.cohere.com/v2/audio/transcriptions',
        'mistral:voxtral-mini-latest':'https://api.mistral.ai/v1/audio/transcriptions',
        'groq:whisper-large-v3':'https://api.groq.com/openai/v1/audio/transcriptions',
        'groq:whisper-large-v3-turbo':'https://api.groq.com/openai/v1/audio/transcriptions'}
MIMES={'wav':'audio/wav','mp3':'audio/mpeg','mpeg':'audio/mpeg','ogg':'audio/ogg','flac':'audio/flac'}


def audio(job):
    found=[]
    for message in job['messages']:
        if message['role']!='user' or not isinstance(message['content'],list):continue
        for part in message['content']:
            if part.get('type')=='input_audio':found.append(part['input_audio'])
            elif part.get('type')!='text':raise CavrenError('input','Transcrição aceita somente um áudio e texto de orientação; remova os outros anexos explicitamente.')
    if len(found)!=1:raise CavrenError('input','Anexe exatamente um áudio para transcrever. Use outra conversa para um novo arquivo.')
    value=found[0];fmt=value.get('format')
    if fmt not in MIMES:raise CavrenError('input','Formato de áudio não integrado para transcrição.')
    try:raw=base64.b64decode(value.get('data',''),validate=True)
    except ValueError:raise CavrenError('input','Áudio inválido.') from None
    if not raw or len(raw)>20*1024*1024:raise CavrenError('input','O áudio precisa ter entre 1 byte e 20 MB.')
    return raw,fmt


def run(job, normalize_messages, *, output=emit):
    import httpx
    from integration.auren_validation import verified
    route=job['mode_options']['manual_route']
    if route not in ROUTES or not verified('cavren:'+route,'transcribe'):
        raise CavrenError('routes','Esta rota de transcrição não foi validada gratuitamente.')
    raw,fmt=audio(job); provider,model=route.split(':',1)
    cfg=connection_settings().providers[provider]
    language=job.get('auren_transcribe_language','auto')
    if language not in ('auto','pt','en'):raise CavrenError('input','Escolha Português, Inglês ou detecção automática.')
    if provider=='cohere' and language=='auto':
        raise CavrenError('input','Cohere exige um idioma explícito. Escolha Lusofonia ou Echo, ou use Mistral no perfil Escuta.')
    data={'model':model}
    if language!='auto':data['language']=language
    output({'type':'generation.task_status','state':'processing','description':'Transcrevendo áudio · '+provider+' · '+model,'generation_id':job['generation_id']})
    remaining=job.get('auren_deadline',time.monotonic()+480)-time.monotonic()
    if remaining<=0:raise CavrenError('timeout','O prazo global foi atingido.')
    with httpx.Client(trust_env=False) as client:
        response=client.post(ROUTES[route],headers={'Authorization':'Bearer '+cfg.api_key},data=data,
                             files={'file':('audio.'+fmt,raw,MIMES[fmt])},timeout=min(remaining,120))
    if response.status_code!=200:
        from cavren.providers import http_error
        raise http_error(response.status_code,provider=provider)
    text=response.json().get('text')
    if not isinstance(text,str) or not text.strip():raise CavrenError('invalid_response','O serviço não retornou uma transcrição com texto.')
    output({'type':'generation.delta','text':text,'generation_id':job['generation_id']})
    output({'type':'generation.completed','response':{'text':text,'provider':provider,'model':model,
           'public_mode':job['mode_id'],'usage':{}},'generation_id':job['generation_id']})
    return 0
