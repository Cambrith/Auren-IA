import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timezone,timedelta
from integration import auren_validation as validation

class EvidencePolicy(unittest.TestCase):
    def test_old_measurement_requires_current_trial_and_same_credential_revision(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(validation,'STATE',Path(directory)):
            root=Path(directory);date=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
            record={'id':'cavren:cohere:tested','kind':'text','status':'working','cost':'free_with_limits','safety':'configured_trial','verified_at':date,'samples':[{'ok':True,'semantic_check':True}]}
            (root/'validation_results.json').write_text(json.dumps({'records':{'text:'+record['id']:record}}))
            policy=root/'provider_policy.json';policy.write_text('{"cohere_trial":true}')
            self.assertTrue(validation.verified(record['id'],'text'))
            policy.write_text('{"cohere_trial":false}')
            self.assertFalse(validation.verified(record['id'],'text'))
            policy.write_text(json.dumps({'cohere_trial':True,'validation_not_before':{'cohere':datetime.now(timezone.utc).isoformat()}}))
            self.assertFalse(validation.verified(record['id'],'text'))

    def test_failure_with_new_key_cannot_reuse_success_from_old_key(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(validation,'STATE',Path(directory)):
            root=Path(directory);now=datetime.now(timezone.utc);old=(now-timedelta(hours=2)).isoformat();revision=(now-timedelta(hours=1)).isoformat()
            record={'id':'cavren:cohere:tested','kind':'text','status':'working','cost':'free_with_limits','safety':'configured_trial','verified_at':now.isoformat(),'samples':[{'ok':True,'date':old},{'ok':False,'date':now.isoformat()}]}
            (root/'validation_results.json').write_text(json.dumps({'records':{'text:'+record['id']:record}}))
            (root/'provider_policy.json').write_text(json.dumps({'cohere_trial':True,'validation_not_before':{'cohere':revision}}))
            self.assertFalse(validation.verified(record['id'],'text'))

class ConfirmedFreePlans(unittest.TestCase):
    def test_gemini_groq_and_ollama_require_current_confirmation(self):
        for provider in ('gemini','groq','ollama'):
            with tempfile.TemporaryDirectory() as directory,patch.object(validation,'STATE',Path(directory)):
                root=Path(directory);date=datetime.now(timezone.utc).isoformat();id='cavren:'+provider+':tested'
                row={'id':id,'kind':'text','status':'working','cost':'free_with_limits','safety':'configured_free_plan','verified_at':date,'samples':[{'ok':True,'semantic_check':True}]}
                (root/'validation_results.json').write_text(json.dumps({'records':{'text:'+id:row}}))
                policy=root/'provider_policy.json';policy.write_text('{}')
                self.assertFalse(validation.verified(id,'text'))
                policy.write_text(json.dumps({provider+'_free_plan':True}))
                self.assertTrue(validation.verified(id,'text'))

class CategoryEvidence(unittest.TestCase):
    def test_category_store_discards_response_and_secret_fields(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(validation,'STATE',Path(directory)):
            validation.save_category('cavren:groq:test','code',{'ok':True,'date':datetime.now(timezone.utc).isoformat(),'code':'ok','seconds':1,'api_key':'synthetic-secret','response':'private-response','prompt':'private-prompt'})
            text=(Path(directory)/'validation_categories.json').read_text()
            self.assertNotIn('synthetic-secret',text);self.assertNotIn('private-response',text);self.assertNotIn('private-prompt',text)
            self.assertEqual((Path(directory)/'validation_categories.json').stat().st_mode&0o777,0o600)
            with self.assertRaises(ValueError):validation.save_category('id','video',{})

    def test_category_probe_cannot_outlive_credential_revision(self):
        from integration import auren_tasks as tasks
        with tempfile.TemporaryDirectory() as directory,patch.object(tasks,'STATE',Path(directory)),patch.object(tasks,'task_evidence',return_value={}),patch.object(tasks,'verified',return_value=True):
            root=Path(directory)
            row={'id':'cavren:groq:test','task':'code','ok':True,'date':'2026-10-12T12:00:00+00:00'}
            (root/'validation_categories.json').write_text(json.dumps({'records':{'code:'+row['id']:row}}))
            (root/'provider_policy.json').write_text('{}')
            self.assertEqual(tasks.models_for('code'),[row['id']])
            (root/'provider_policy.json').write_text(json.dumps({'validation_not_before':{'groq':'2026-10-13T12:00:00+00:00'}}))
            self.assertEqual(tasks.models_for('code'),[])
