"""Native image authenticity/face detection checks on a known non-AI graphic."""
import base64,hashlib,math,time

def probe(client,row,sample,cfg,asset,run):
 import auren_exhaustive_probe as audit
 start=time.monotonic();out={'at':audit.now(),'sample':sample,'real_call':False,'success':False,'cost_class':'unknown','fixture_kind':'programmatic_graphic_without_faces','positive_class_tested':False};raw=(asset/'vision.png').read_bytes()
 if len(raw)>=200000:return {**out,'result':'native_inline_image_size_bound','seconds':0}
 body={'input':['data:image/png;base64,'+base64.b64encode(raw).decode()]}
 if row['operation']=='deepfake_detection':body['return_image']=False
 try:
  if row['operation']=='native_visual_embeddings':
   vectors=[];out['native_call_count']=0
   for name in ['vision.png','vision.png','mask.png']:
    image=(asset/name).read_bytes();body={'messages':[{'content':{'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(image).decode()}}}]};out['real_call']=True;response=client.post(row['endpoint'],headers=audit.headers('nvidia',cfg),json=body,timeout=30);out['native_call_count']+=1;out['auxiliary_call_count']=out['native_call_count']-1;data=response.json();out.update(audit.safe_response(response,data,cfg))
    if response.status_code>=400:out['result']={400:'contract_error',401:'authentication',403:'permission_or_plan',404:'route_unavailable',410:'native_endpoint_retired',422:'contract_error',429:'rate_or_quota_limit'}.get(response.status_code,'provider_error');return out
    values=data.get('metadata') or [];vectors.append(values[0].get('embedding') if len(values)==1 else None)
   ok,code,evidence=audit.evaluate({'embeddings':vectors},'nvidia','embeddings',0);out.update(success=ok,result=code,evidence=evidence);return out
  out.update(real_call=True,input_sha256=hashlib.sha256(raw).hexdigest());response=client.post(row['endpoint'],headers=audit.headers('nvidia',cfg),json=body,timeout=30);data=response.json();out.update(audit.safe_response(response,data,cfg))
  if response.status_code>=400:out['result']={400:'contract_error',401:'authentication',403:'permission_or_plan',404:'route_unavailable',410:'native_endpoint_retired',422:'contract_error',429:'rate_or_quota_limit'}.get(response.status_code,'provider_error');return out
  predictions=data.get('data') or [];out['response_sha256']=hashlib.sha256(response.content).hexdigest()
  if len(predictions)!=1 or predictions[0].get('index')!=0 or predictions[0].get('status')!='SUCCESS':out['result']='native_prediction_schema_or_status_failed';return out
  prediction=predictions[0]
  if row['operation']=='deepfake_detection':ok=isinstance(prediction.get('bounding_boxes'),list) and not prediction['bounding_boxes'];out['face_count']=len(prediction.get('bounding_boxes',[]))
  else:
   probability=prediction.get('is_ai_generated');sources=prediction.get('possible_sources');valid=type(probability) in (int,float) and math.isfinite(probability) and 0<=probability<=1 and isinstance(sources,dict) and all(type(v) in (int,float) and math.isfinite(v) and 0<=v<=1 for v in sources.values());ok=valid and probability<.5;out.update(probability_ai_generated=probability,response_probabilities_valid=valid)
  out.update(success=ok,result='valid_native_negative_graphic_control' if ok else 'native_negative_control_check_failed')
 except Exception as error:out['result']=type(error).__name__
 finally:out['seconds']=round(time.monotonic()-start,3)
 return out
