import asyncio
import unittest
from uuid import uuid4
from open_webui.utils.auren_events import begin,admit,scoped

class EventScope(unittest.IsolatedAsyncioTestCase):
    async def test_cancellation_persists_once_and_blocks_late_events_until_new_request(self):
        info={'user_id':'cancel-test','chat_id':'own','message_id':'response'}
        first=str(uuid4());await begin(info,first)
        sent=[];persisted=[]
        async def emitter(event):sent.append(event)
        async def persist():persisted.append(True)
        forward=scoped(emitter,info,persist)
        await forward({'type':'chat:tasks:cancel'})
        self.assertEqual(sent[0]['data']['auren_request_id'],first)
        for kind in ('files','status','chat:completion','chat:tasks:cancel'):
            await forward({'type':kind,'data':{}})
        self.assertEqual(len(sent),1);self.assertEqual(persisted,[True])
        await begin(info,str(uuid4()))
        await forward({'type':'status','data':{}})
        self.assertEqual(len(sent),2)

    async def test_replacement_blocks_old_files_and_completion(self):
        info={'user_id':'test-user','chat_id':'test-chat','message_id':'test-message'}
        old=dict(info);new=dict(info)
        first=str(uuid4());second=str(uuid4())
        await begin(old,first)
        self.assertEqual(admit(old,{'type':'files','data':{'files':[]}})['data']['auren_request_id'],first)
        await begin(new,second)
        for kind in ('status','chat:message:files','chat:completion','response:completion'):
            self.assertIsNone(admit(old,{'type':kind,'data':{}}))
            self.assertEqual(admit(new,{'type':kind,'data':{}})['data']['auren_request_id'],second)
    async def test_other_messages_and_legacy_events_are_preserved(self):
        event={'type':'status','data':{'description':'test'}}
        self.assertEqual(admit({'message_id':'legacy'},event),event)
        a={'user_id':'test','chat_id':'chat','message_id':'a'};b={**a,'message_id':'b'}
        await begin(a,str(uuid4()));await begin(b,str(uuid4()))
        self.assertIsNotNone(admit(a,event));self.assertIsNotNone(admit(b,event))

    async def test_replacement_waits_for_old_db_event_then_blocks_later_events(self):
        old={'user_id':'isolated','chat_id':'db','message_id':'same'};new=dict(old)
        await begin(old,str(uuid4()))
        started=asyncio.Event();release=asyncio.Event();saved=[]
        async def emitter(event):
            started.set();await release.wait();saved.append(event)
        forward=scoped(emitter,old)
        pending=asyncio.create_task(forward({'type':'files','data':{'files':[]}}))
        await started.wait()
        replacement=asyncio.create_task(begin(new,str(uuid4())))
        await asyncio.sleep(0)
        self.assertFalse(replacement.done())
        release.set();await pending;await replacement
        await forward({'type':'files','data':{'files':['stale']}})
        self.assertEqual(len(saved),1)
