"""NVIDIA trial TTS over its documented HTTP transport, verified in pt-BR."""
import base64,io,re,time,wave
from cavren.errors import CavrenError
from integration.lunvri_manual import emit
from integration.lunvri_connections import connection_settings
URL='https://877104f7-e885-42b9-8de8-f6e4c6303969.invocation.api.nvcf.nvidia.com/v1/audio/synthesize'
ROUTE='nvidia:magpie-tts-multilingual'

def text_input(job):
    if any(isinstance(m['content'],list) and any(p.get('type')!='text' for p in m['content']) for m in job['messages']):
        raise CavrenError('input','Gerar voz aceita texto. Remova os anexos explicitamente ou use outra tarefa.')
    text=job['prompt'].strip()
    text=re.sub(r'^(?:gere|crie|faça)\s+(?:uma?\s+)?(?:voz|narração|áudio)\s*:\s*','',text,flags=re.I)
    if not 1<=len(text)<=2000:raise CavrenError('input','Escreva o texto para narrar, em até 2.000 caracteres.')
    return text

def run(job, normalize_messages, *, output=emit):
    import httpx
    from integration.auren_validation import verified
    from integration.auren_tasks import task_evidence
    if job['mode_options']['manual_route']!=ROUTE or not verified('cavren:'+ROUTE,'speech'):
        raise CavrenError('routes','Esta rota de voz ainda não foi validada gratuitamente.')
    text=text_input(job); cfg=connection_settings().providers['nvidia'];record=task_evidence()['speech']
    output({'type':'generation.task_status','description':'Gerando voz em português · NVIDIA Magpie','generation_id':job['generation_id']})
    remaining=job.get('auren_deadline',time.monotonic()+480)-time.monotonic()
    if remaining<=0:raise CavrenError('timeout','O prazo global foi atingido.')
    with httpx.Client(trust_env=False) as client:
        response=client.post(URL,headers={'Authorization':'Bearer '+cfg.api_key},
                             data={'text':text,'language':record['language'],'voice':record['voice'],'encoding':'LINEAR_PCM','sample_rate_hz':'44100'},timeout=min(remaining,120))
    if response.status_code!=200:
        from cavren.providers import http_error
        raise http_error(response.status_code,provider='nvidia')
    try:
        stream=wave.open(io.BytesIO(response.content));valid=stream.getnframes()>0 and len(response.content)<20*1024*1024
    except (wave.Error,EOFError):valid=False
    if not valid:raise CavrenError('invalid_response','O provedor não retornou um WAV válido no limite de tamanho.')
    output({'type':'generation.files','files':[{'type':'audio','url':'data:audio/wav;base64,'+base64.b64encode(response.content).decode(),'name':'Auren-voz.wav'}],'generation_id':job['generation_id']})
    output({'type':'generation.delta','text':'Áudio gerado em português.','generation_id':job['generation_id']})
    output({'type':'generation.completed','response':{'text':'Áudio gerado em português.','provider':'nvidia','model':'magpie-tts-multilingual','public_mode':job['mode_id'],'usage':{}},'generation_id':job['generation_id']})
    return 0
