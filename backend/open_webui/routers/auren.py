"""Authenticated access to the local engine; no provider secrets enter the WebUI DB."""
import httpx
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, SecretStr
from open_webui.models.config import Config
from open_webui.utils.auth import get_admin_user, get_verified_user

router=APIRouter()

async def bridge_request(method,path,payload=None):
    urls=await Config.get('openai.api_base_urls')
    keys=await Config.get('openai.api_keys')
    try:
        parsed = urlsplit(urls[0]) if urls else None
        local = parsed and parsed.scheme == 'http' and parsed.hostname == '127.0.0.1' and parsed.port and not parsed.username and not parsed.password
    except ValueError:
        local = False
    if not local or not keys:
        raise HTTPException(503,'A ponte local da Auren está indisponível.')
    try:
        async with httpx.AsyncClient(trust_env=False,timeout=600 if path=='/chat/completions' else 60) as client:
            response=await client.request(method,urls[0]+path,headers={'Authorization':'Bearer '+keys[0]},json=payload)
        body=response.json()
        if response.status_code>=400:
            raise HTTPException(response.status_code,body.get('error',{}).get('message','Falha na conexão local.'))
        return body
    except (httpx.HTTPError,ValueError):
        raise HTTPException(503,'Não foi possível consultar o motor local.') from None

@router.get('/state')
async def state(refresh:bool=False,user=Depends(get_verified_user)):
    return await bridge_request('GET','/auren/state'+('?refresh=true' if refresh else ''))

@router.post('/preferences')
async def preferences(data:dict,user=Depends(get_admin_user)):
    return await bridge_request('POST','/auren/preferences',data)

class CredentialForm(BaseModel):
    provider:str
    key:SecretStr | None = None
    fields:dict[str,SecretStr] | None = None
    free_trial:bool=False

@router.post('/provider')
async def provider(data:CredentialForm,user=Depends(get_admin_user)):
    values = {k:v.get_secret_value() for k,v in (data.fields or {}).items()}
    if data.key is not None: values['key'] = data.key.get_secret_value()
    return await bridge_request('POST','/auren/provider',{'provider':data.provider,'fields':values,'free_trial':data.free_trial})

class ImageForm(BaseModel):
    model:str
    prompt:str
    billing_confirmed:bool=False

@router.post('/images/generations')
async def generate_image(data:ImageForm,user=Depends(get_admin_user)):
    if not 1<=len(data.prompt.strip())<=12000: raise HTTPException(400,'Descreva a imagem em até 12.000 caracteres.')
    return await bridge_request('POST','/chat/completions',{'model':data.model,'stream':False,
        'lunvri_image_generation':True,'cavren_billing_confirmed':data.billing_confirmed,
        'messages':[{'role':'user','content':data.prompt}]})


class ConnectionForm(BaseModel):
    provider:str

@router.post('/connections/validate')
async def validate_connection(data:ConnectionForm,user=Depends(get_admin_user)):
    return await bridge_request('POST','/auren/connections/validate',{'provider':data.provider})

@router.post('/oauth/canva/start')
async def start_canva(user=Depends(get_admin_user)):
    return await bridge_request('POST','/auren/oauth/canva/start',{})
