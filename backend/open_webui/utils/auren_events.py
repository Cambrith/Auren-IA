"""Isolate repeated generations of one Auren response, including its DB events."""
import asyncio
from collections import OrderedDict
from uuid import UUID

_active = OrderedDict()
_locks = OrderedDict()

def lock(info):
    key=scope(info)
    if key not in _locks: _locks[key]=asyncio.Lock()
    _locks.move_to_end(key)
    while len(_locks)>4096:_locks.popitem(last=False)
    return _locks[key]

def scope(info):
    return tuple(str(info.get(k,'')) for k in ('user_id','chat_id','message_id'))

async def begin(info, request_id):
    try: UUID(request_id)
    except (ValueError,TypeError,AttributeError):return
    async with lock(info):
        info['auren_request_id']=request_id
        key=scope(info)
        _active[key]=request_id
        _active.move_to_end(key)
        while len(_active)>4096:_active.popitem(last=False)

def admit(info, event):
    request_id=info.get('auren_request_id')
    if not request_id:return event
    if _active.get(scope(info))!=request_id:return None
    data=event.get('data')
    if data is None and event.get('type')=='chat:tasks:cancel':data={}
    return {**event,'data':{**data,'auren_request_id':request_id}} if isinstance(data,dict) else event


def scoped(emitter, info, on_cancel=None):
    if not info.get('auren_request_id'):return emitter
    async def forward(event):
        async with lock(info):
            accepted=admit(info,event)
            if accepted is not None:
                if accepted.get('type')=='chat:tasks:cancel':
                    _active.pop(scope(info),None)
                    if on_cancel is not None:await on_cancel()
                return await emitter(accepted)
    return forward
