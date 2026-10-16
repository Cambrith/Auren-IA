"""Preferences/state and vault transaction tests; no real secrets or provider calls."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from integration import auren_settings as settings
from integration import auren_credentials
from integration.lunvri_connections import model_entry

IMAGE = {'id':'cavren:aihorde:test','name':'Test Image','cavren':{'provider':'aihorde','capabilities':{'image_generation':True}}}

class Vault:
    def __init__(self, existing='old', reject=False): self.value=existing; self.reject=reject
    def get(self, name): return self.value
    def set(self, name, value):
        if not (self.reject and value=='replacement'): self.value=value
    def delete(self, name): self.value=''

class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.path=patch.object(settings,'STATE',self.root);self.path.start()
        self.vault_path=patch.object(auren_credentials,'STATE',self.root);self.vault_path.start()
        self.models=patch.object(settings,'catalog',return_value=[IMAGE]);self.models.start()
    def tearDown(self): self.models.stop();self.vault_path.stop();self.path.stop();self.temp.cleanup()
    def test_preferences_roundtrip_and_permissions(self):
        value=settings.save_preferences({'image_model_id':IMAGE['id'],'image_width':768})
        self.assertEqual(value,settings.preferences());self.assertEqual(value['image_steps'],20)
        self.assertEqual((self.root/'auren_preferences.json').stat().st_mode & 0o777,0o600)
    def test_bad_preferences_never_replace_saved_data(self):
        before=settings.save_preferences({'image_model_id':IMAGE['id']})
        for value in ({'image_model_id':'chat-model'},{'image_width':513},{'image_height':True},{'image_steps':0},{'unsupported':1}):
            with self.assertRaises(ValueError):settings.save_preferences(value)
            self.assertEqual(settings.preferences(),before)
    def test_partial_legacy_preferences_keep_defaults(self):
        (self.root/'auren_preferences.json').write_text('{"image_width":768}')
        self.assertEqual(settings.preferences()['image_steps'],20)
    def test_vault_confirmation_rolls_back_key_and_keeps_policy(self):
        p=self.root/'provider_policy.json';p.write_text('{"nvidia_trial":false}')
        vault=Vault(reject=True)
        with self.assertRaises(OSError): settings.save_key('nvidia','replacement',vault,free_trial=True)
        self.assertEqual(vault.value,'old');self.assertFalse(json.loads(p.read_text())['nvidia_trial'])
    def test_policy_failure_rolls_back_vault(self):
        vault=Vault()
        with patch.object(settings,'atomic_json',side_effect=OSError('unavailable')):
            with self.assertRaises(OSError):settings.save_key('nvidia','replacement',vault,free_trial=True)
        self.assertEqual(vault.value,'old')
    def test_secure_update_only_explicit_free_trial(self):
        vault=Vault()
        settings.save_key('cohere','replacement',vault,free_trial=True)
        self.assertEqual(vault.value,'replacement')
        policy=json.loads((self.root/'provider_policy.json').read_text())
        self.assertTrue(policy['cohere_trial'])
        self.assertIn('cohere',policy['validation_not_before'])
        self.assertNotIn('replacement',json.dumps(policy))
        settings.save_key('cohere','replacement',vault)
        self.assertFalse(json.loads((self.root/'provider_policy.json').read_text())['cohere_trial'])
    def test_invalid_provider_and_key_do_not_change_vault(self):
        vault=Vault()
        for provider,key in [('missing-provider','replacement'),('nvidia','short'),('nvidia','x x x x x')]:
            with self.assertRaises(ValueError): settings.save_key(provider,key,vault)
            self.assertEqual(vault.value,'old')
    def test_state_redacts_credentials_and_distinguishes_catalog_from_generation(self):
        (self.root/'models.json').write_text(json.dumps({'providers':{'aihorde':{'connected':True,'count':1},'cohere':{'connected':False,'status':401}}}))
        config=SimpleNamespace(providers={'aihorde':SimpleNamespace(api_key='must-not-appear'), 'cohere':SimpleNamespace(api_key='another-secret')})
        with patch.object(settings,'connection_settings',return_value=config):state=settings.public_state()
        self.assertNotIn('must-not-appear',json.dumps(state));self.assertNotIn('another-secret',json.dumps(state))
        by_id={c['id']:c for c in state['connections']}
        self.assertEqual(by_id['aihorde']['state'],'catalog_available');self.assertEqual(by_id['cohere']['state'],'auth_error');self.assertEqual(by_id['groq']['state'],'unconfigured')
    def test_protocol_does_not_rename_provider_model(self):
        m=model_entry('cavren:provider:actual-model',{'label':'Actual Model','provider':'provider','provider_name':'Actual Provider','capabilities':{'vision':True}})
        self.assertEqual(m['name'],'Actual Model');self.assertEqual(m['provider'],'provider')
        self.assertEqual(m['info']['meta']['model_source'],'external')
        self.assertEqual(m['owned_by'],'openai') # existing dispatch protocol, not authorship

if __name__=='__main__':unittest.main()
