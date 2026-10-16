"""Future OpenAI/Anthropic connections; mock APIs only, no account/key changes."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
import httpx
from cavren.config import ProviderConfig,load_settings
from cavren.models import Message
from integration import lunvri_connections as connections
from integration import auren_settings as settings
from integration.lunvri_manual import PreparedChatProvider

class PreparedProviderTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.patches=[patch.object(module,'STATE',Path(self.directory.name)) for module in (connections,settings)]
        for item in self.patches:item.start()

    def tearDown(self):
        for item in reversed(self.patches):item.stop()
        self.directory.cleanup()

    def test_documents_never_supply_runtime_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory)
            documents=home/'Documentos'
            documents.mkdir()
            legacy=documents/'Chaves de API - Cavren'
            current=documents/'Chaves de API - Auren'
            custom=home/'custom-keys'
            legacy.write_text('NVIDIA_API_KEY=legacy-test-key')
            current.write_text('NVIDIA_API_KEY=auren-test-key')
            custom.write_text('NVIDIA_API_KEY=custom-test-key')
            with patch.object(connections,'STATE',home),patch.object(connections,'worker_env',return_value={}),patch.object(connections.Path,'home',return_value=home),patch.dict(connections.os.environ,{'LUNVRI_CREDENTIALS_FILE':str(custom)},clear=True),patch('integration.auren_credentials.remember_credentials'),patch('integration.auren_credentials.AurenVault') as vault:
                vault.return_value.get.return_value=''
                self.assertNotIn('NVIDIA_API_KEY',connections.credentials_env())
                vault.return_value.get.return_value='vault-test-key'
                self.assertEqual(connections.credentials_env()['NVIDIA_API_KEY'],'vault-test-key')
                renamed=current.rename(home/'renamed-keys')
                self.assertEqual(connections.credentials_env()['NVIDIA_API_KEY'],'vault-test-key')
                for file in (legacy,renamed,custom): file.unlink()
                self.assertEqual(connections.credentials_env()['NVIDIA_API_KEY'],'vault-test-key')

    def test_vault_overrides_stale_provider_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(connections,'STATE',Path(directory)),patch.object(connections,'worker_env',return_value={'NVIDIA_API_KEY':'stale-test-key'}),patch('integration.auren_credentials.remember_credentials'),patch('integration.auren_credentials.AurenVault') as vault:
                vault.return_value.get.return_value='vault-test-key'
                self.assertEqual(connections.credentials_env()['NVIDIA_API_KEY'],'vault-test-key')

    def test_two_connections_have_no_key_by_default(self):
        config=connections.connection_settings({'UNRELATED':'present'})
        for name in ('openai','anthropic'):
            self.assertIn(name,config.providers);self.assertFalse(config.providers[name].api_key)
    def test_environment_and_document_do_not_auto_activate_new_providers(self):
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'keys';file.write_text('OPENAI_API_KEY=not-used-secret\nANTHROPIC_API_KEY=not-used-secret')
            with patch.object(connections,'STATE',Path(directory)),patch.object(connections,'worker_env',return_value={'OPENAI_API_KEY':'env-secret'}),patch.dict(connections.os.environ,{'LUNVRI_CREDENTIALS_FILE':str(file)}),patch('integration.auren_credentials.remember_credentials'),patch('integration.auren_credentials.AurenVault') as vault:
                vault.return_value.get.return_value=''
                env=connections.credentials_env()
                self.assertNotIn('OPENAI_API_KEY',env);self.assertNotIn('ANTHROPIC_API_KEY',env)
    def test_openai_supported_chat_filter_is_conservative_and_paid(self):
        model=connections.public_model('openai',{'id':'gpt-4o'})
        self.assertEqual(model['cavren']['price_kind'],'paid')
        for name in ('whisper-1','gpt-image-1','gpt-4o-audio-preview','gpt-5-codex','text-embedding-3-small'):
            self.assertIsNone(connections.public_model('openai',{'id':name}))
    def test_anthropic_native_catalog_headers_and_capabilities(self):
        seen=[]
        def response(request):
            seen.append(request)
            return httpx.Response(200,json={'data':[{'id':'claude-sonnet-test','display_name':'Claude Sonnet Test','max_input_tokens':200000,'max_tokens':8192,'capabilities':{'image_input':{'supported':True}}}]})
        original=httpx.Client
        with patch.object(connections.httpx,'Client',side_effect=lambda **kw:original(transport=httpx.MockTransport(response),**kw)):
            models,state=connections.discover('anthropic',ProviderConfig('anthropic','','https://api.anthropic.com/v1','ANTHROPIC_API_KEY','test-secret'))
        self.assertTrue(state['connected']);self.assertEqual(seen[0].headers['anthropic-version'],'2023-06-01')
        self.assertEqual(seen[0].headers['x-api-key'],'test-secret');self.assertNotIn('test-secret',str(seen[0].url))
        self.assertTrue(models[0]['cavren']['capabilities']['vision']);self.assertFalse(models[0]['cavren']['capabilities']['pdf'])
        self.assertEqual(models[0]['cavren']['price_kind'],'paid')
    def test_new_cards_have_vault_keys_and_native_chat_endpoints(self):
        expected = {'deepseek': ('DEEPSEEK_API_KEY', 'https://api.deepseek.com/v1'),
                    'huggingface': ('HUGGINGFACE_API_KEY', 'https://router.huggingface.co/v1'),
                    'xai': ('XAI_API_KEY', 'https://api.x.ai/v1')}
        config = connections.connection_settings({'UNRELATED': 'present'})
        for provider, (key, url) in expected.items():
            self.assertEqual(settings.PROVIDER_KEYS[provider], key)
            self.assertEqual(config.providers[provider].base_url, url)
            self.assertFalse(config.providers[provider].api_key)
            body = PreparedChatProvider(ProviderConfig(provider, 'synthetic-chat', url, key, 'synthetic'),
                                        load_settings({}), MagicMock())._payload([Message('user', 'Hello')], stream=True)
            self.assertEqual(body['model'], 'synthetic-chat')
            self.assertNotIn('reasoning_effort', body)

    def test_paid_metadata_cannot_be_promoted_by_old_free_evidence(self):
        for provider, name in (('deepseek', 'deepseek-chat'), ('xai', 'grok-4'), ('openai', 'gpt-4o'), ('anthropic', 'claude-test')):
            model = connections.public_model(provider, {'id': name})
            with patch('integration.auren_validation.model_evidence', return_value={'status':'passed','safety':'zero_price_cap'}), patch('integration.auren_validation.verified', return_value=True), patch('integration.auren_tasks.task_evidence', return_value={}):
                connections.validated_catalog([model])
            self.assertEqual(model['cavren']['price_kind'], 'paid')
        hf = connections.public_model('huggingface', {'id':'Qwen/test', 'providers':[{'is_free':True}]})
        self.assertEqual(hf['cavren']['price_kind'], 'unknown')
        self.assertIsNone(connections.public_model('xai', {'id':'grok-imagine-image'}))

    def test_documented_future_models_are_visible_but_not_runnable(self):
        with patch('integration.auren_tasks.task_evidence', return_value={}):
            models = connections.validated_catalog([])
        self.assertEqual({m['cavren']['provider'] for m in models}, {'anthropic', 'xai'})
        self.assertTrue(all(m['cavren']['available'] is False for m in models))
        self.assertTrue(all(m['cavren']['price_kind'] == 'paid' for m in models))
        self.assertTrue(all(m['cavren']['catalog_source'] == 'documentation' for m in models))
        with patch('integration.auren_tasks.task_evidence', return_value={}):
            connections.validated_catalog(models)
        self.assertEqual(len(models), 5)

    def test_direct_paid_routes_require_explicit_manual_billing(self):
        from integration.auren_fallback import candidates
        config = connections.connection_settings({key:'synthetic' for key in ('DEEPSEEK_API_KEY','XAI_API_KEY','OPENAI_API_KEY','ANTHROPIC_API_KEY')})
        job = {'mode_id':'ether', 'mode_options':{'manual_route':'','billing_confirmed':False},
               'messages':[{'role':'user','content':'Hello'}], 'max_tokens':64}
        for provider, name in (('deepseek','deepseek-chat'), ('xai','grok-4.7'), ('openai','gpt-4o'), ('anthropic','claude-sonnet-5-5')):
            model = connections.public_model(provider, {'id':name,'context_length':128000})
            job['mode_options'] = {'manual_route':model['cavren']['route_id'], 'billing_confirmed':False}
            self.assertEqual(candidates(job, [model], config, {}), [])
            job['mode_options']['billing_confirmed'] = True
            self.assertEqual([m['id'] for m in candidates(job, [model], config, {})], [model['id']])
            job['mode_options']['manual_route'] = ''
            self.assertEqual(candidates(job, [model], config, {}), [])

    def test_openai_uses_current_chat_token_limit(self):
        config=ProviderConfig('openai','gpt-4o','https://api.openai.com/v1','OPENAI_API_KEY','test-secret')
        provider=PreparedChatProvider(config,load_settings({}),MagicMock())
        body=provider._payload([Message('user','Hello')],stream=True)
        self.assertIn('max_completion_tokens',body);self.assertNotIn('max_tokens',body)
        self.assertNotIn('test-secret',json.dumps(body))

    def test_groq_uses_model_specific_reasoning_contract_and_current_limit(self):
        for name in ('openai/gpt-oss-120b','openai/gpt-oss-20b','qwen/qwen3.8-27b'):
            config=ProviderConfig('groq',name,'https://api.groq.com/openai/v1','GROQ_API_KEY','synthetic')
            body=PreparedChatProvider(config,load_settings({}),MagicMock(),reasoning_hidden=True)._payload([Message('user','Synthetic')],stream=True)
            self.assertIn('max_completion_tokens',body)
            self.assertNotIn('max_tokens',body)
            if name.startswith('openai/'):
                self.assertNotIn('reasoning_format',body)
                self.assertIs(body['include_reasoning'],False)
            else:
                self.assertEqual(body['reasoning_format'],'hidden')
                self.assertNotIn('include_reasoning',body)

class ZeroPriceTests(unittest.TestCase):
    def test_price_cap_is_enforced_only_for_free_openrouter_requests(self):
        config=ProviderConfig('openrouter','paid-advertised-model','https://openrouter.ai/api/v1','OPENROUTER_API_KEY','synthetic')
        settings=load_settings({})
        body=PreparedChatProvider(config,settings,MagicMock(),free_only=True)._payload([Message('user','Synthetic')],stream=False)
        self.assertEqual(body['provider']['max_price'],{'prompt':0,'completion':0,'request':0,'image':0})
        manual=PreparedChatProvider(config,settings,MagicMock())._payload([Message('user','Synthetic')],stream=False)
        self.assertNotIn('provider',manual)

if __name__=='__main__':unittest.main()
