"""Image operation policy shared by admission, planning and provider execution.

Catalog availability is an advertisement, never evidence of successful generation.
"""
import base64
import ipaddress
from urllib.parse import urlparse
from cavren.errors import CavrenError

PROFILES = ('rapid', 'balanced', 'detailed')
PROVIDERS = ('aihorde', 'gemini', 'openrouter')


def operations(info):
    caps = info.get('capabilities', {})
    if info.get('provider') not in PROVIDERS or not caps.get('image_generation'):
        return ()
    return ('text_to_image', 'reference') if info['provider'] in ('gemini', 'openrouter') and caps.get('vision') else ('text_to_image',)


def validate(job, info):
    operation = job.get('auren_image_operation', 'text_to_image')
    if operation not in operations(info):
        raise CavrenError('image_input', 'Este gerador não encaminha referências nesta operação. Escolha Gemini/OpenRouter com entrada de imagem compatível ou remova a referência explicitamente.')
    if job.get('auren_image_profile', 'balanced') not in PROFILES:
        raise CavrenError('image_input', 'Escolha um perfil de imagem válido.')
    for message in job['messages']:
        if isinstance(message['content'], list):
            for part in message['content']:
                if part.get('type') not in ('text', 'image_url'):
                    raise CavrenError('image_input', 'Geração de imagens aceita texto e referências compatíveis. Remova os demais anexos explicitamente.')
                if part.get('type') == 'image_url':
                    url = (part.get('image_url') or {}).get('url')
                    if not isinstance(url, str):
                        raise CavrenError('image_input', 'Referência de imagem inválida.')
                    if info['provider'] == 'gemini' and not url.startswith('data:image/'):
                        raise CavrenError('image_input', 'O adaptador Gemini exige uma imagem anexada localmente.')
                    if url.startswith('data:'):
                        try:
                            header, encoded = url.split(';base64,', 1)
                            if header not in ('data:image/png', 'data:image/jpeg', 'data:image/webp') or len(encoded) > 28_000_000:
                                raise ValueError()
                            raw=base64.b64decode(encoded, validate=True)
                            signatures={'data:image/png':raw.startswith(b'\x89PNG\r\n\x1a\n'),
                                        'data:image/jpeg':raw.startswith(b'\xff\xd8') and raw.endswith(b'\xff\xd9'),
                                        'data:image/webp':raw.startswith(b'RIFF') and raw[8:12]==b'WEBP'}
                            if len(raw)>20*1024*1024 or not signatures[header]:raise ValueError()
                        except ValueError:
                            raise CavrenError('image_input', 'Referência inválida ou maior que o limite de imagem.') from None
                    elif not url.startswith(('https://', 'http://')):
                        raise CavrenError('image_input', 'Formato da referência não integrado.')
                    else:
                        parsed=urlparse(url)
                        host=(parsed.hostname or '').casefold()
                        invalid=not host or parsed.username is not None or parsed.password is not None or host=='localhost' or host.endswith(('.localhost','.local','.internal'))
                        try:invalid=invalid or not ipaddress.ip_address(host).is_global
                        except ValueError:pass
                        if invalid:raise CavrenError('image_input','Use uma referência pública sem credenciais no URL ou anexe a imagem localmente.')
                if part.get('type') == 'image_url' and operation != 'reference':
                    raise CavrenError('image_input', 'A referência exige uma operação compatível.')
    params = job.get('auren_image_parameters', {})
    if not isinstance(params, dict) or set(params) - {'width', 'height', 'steps'}:
        raise CavrenError('image_input', 'Máscaras e estes parâmetros ainda não têm transporte integrado.')
    if params and info['provider'] != 'aihorde':
        raise CavrenError('image_input', 'Dimensões e etapas personalizadas só estão integradas ao AI Horde.')
    for key, value in params.items():
        valid = type(value) is int and (5 <= value <= 50 if key == 'steps' else value in (512, 768, 1024))
        if not valid:
            raise CavrenError('image_input', 'Parâmetro de imagem inválido: ' + key)


def rank(info, job):
    # Worker counts describe the catalog snapshot, not a live latency measurement.
    workers = info.get('image_workers')
    workers = workers if isinstance(workers, (int, float)) else 0
    preferred = info.get('route_id') == job.get('auren_image_preferred_route')
    curated = info.get('route_id') == 'aihorde:stable_diffusion'
    if job.get('auren_image_profile') == 'rapid':
        from integration.auren_validation import measured_seconds, evidence
        model_id='cavren:' + info.get('route_id', '')
        recent=evidence().get('profile:rapid:'+model_id,{})
        base=evidence().get('image:'+model_id,{})
        samples=recent.get('samples',[])[-2:]
        fresh=recent.get('verified_at','')>base.get('verified_at','')
        recent_failure=len(samples)>=2 and any(not sample.get('ok') for sample in samples) and fresh
        seconds = measured_seconds('cavren:' + info.get('route_id', ''), 'image')
        if fresh and len(samples)==2 and all(sample.get('ok') and isinstance(sample.get('seconds'),(int,float)) for sample in samples):
            seconds=sum(sample['seconds'] for sample in samples)/2
        return (1 if recent_failure else 0, 0 if seconds is not None else 1, seconds if seconds is not None else float('inf'), -workers, 0 if preferred else 1)
    if job.get('auren_image_profile') == 'detailed':
        return (0 if curated else 1, 0 if preferred else 1, -workers)
    return (0 if preferred else 1, 0 if curated else 1, -workers)
