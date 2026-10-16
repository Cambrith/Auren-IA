"""AWS endpoint validation and read-only discovery. Never invokes a model."""
import re
from urllib.parse import urlsplit


def validate_base_url(value, region):
    if not re.fullmatch(r'[a-z]{2}(?:-[a-z]+)+-\d',region or ''):
        raise ValueError('Informe uma região AWS válida.')
    suffix='amazonaws.com.cn' if region.startswith('cn-') else 'amazonaws.com'
    allowed={f'https://bedrock-runtime.{region}.{suffix}/openai/v1',
             f'https://bedrock-mantle.{region}.api.aws/v1'}
    if value not in allowed: raise ValueError('A Base URL deve ser um endpoint Bedrock oficial da região escolhida, sem tokens.')
    return value


def catalogue_url(values):
    region=values.get('region','')
    if not re.fullmatch(r'[a-z]{2}(?:-[a-z]+)+-\d',region):
        raise ValueError('Região AWS ausente.')
    base=values.get('base_url') or f'https://bedrock-runtime.{region}.amazonaws.com/openai/v1'
    validate_base_url(base,region)
    if urlsplit(base).hostname.startswith('bedrock-mantle.'):
        return base+'/models'
    suffix='amazonaws.com.cn' if region.startswith('cn-') else 'amazonaws.com'
    return f'https://bedrock.{region}.{suffix}/foundation-models?byOutputModality=TEXT'


def discover(values, client):
    """Return public model metadata only; HTTP errors never escape with response bodies."""
    response=client.get(catalogue_url(values),headers={'Authorization':'Bearer '+values['key']})
    from integration.auren_connection_validation import response_payload
    payload,error=response_payload(response)
    if error:return [],error
    mantle='bedrock-mantle.' in values.get('base_url','')
    rows=payload.get('data' if mantle else 'modelSummaries') if isinstance(payload,dict) else None
    if not isinstance(rows,list):return [],('failed','invalid_response')
    models=[]
    for row in rows:
        if not isinstance(row,dict):continue
        id=row.get('id' if mantle else 'modelId')
        if not isinstance(id,str) or not re.fullmatch(r'[A-Za-z0-9._:/-]{1,200}',id):continue
        models.append({'id':id,'name':row.get('modelName',id),'provider':row.get('providerName',''),
            'input_modalities':row.get('inputModalities',[]),'output_modalities':row.get('outputModalities',[]),
            'inference_types':row.get('inferenceTypesSupported',[]),
            'endpoint_compatibility':'mantle_catalogue' if mantle else 'requires_model_api_support_check',
            'inference_tested':False})
    return models,None
