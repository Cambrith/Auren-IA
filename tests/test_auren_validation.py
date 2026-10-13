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
