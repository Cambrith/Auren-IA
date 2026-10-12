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
    def test_two_connections_have_no_key_by_default(self):
        config=connections.connection_settings({'UNRELATED':'present'})
        for name in ('openai','anthropic'):
            self.assertIn(name,config.providers);self.assertFalse(config.providers[name].api_key)
    def test_environment_and_document_do_not_auto_activate_new_providers(self):
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'keys';file.write_text('OPENAI_API_KEY=not-used-secret\nANTHROPIC_API_KEY=not-used-secret')
            with patch.object(connections,'STATE',Path(directory)),patch.object(connections,'worker_env',return_value={'OPENAI_API_KEY':'env-secret'}),patch.dict(connections.os.environ,{'LUNVRI_CREDENTIALS_FILE':str(file)}),patch('cavren.credentials.SecretServiceBackend') as vault:
                vault.return_value.get.return_value=''
                env=connections.credentials_env()
                self.assertNotIn('OPENAI_API_KEY',env);self.assertNotIn('ANTHROPIC_API_KEY',env)
    def test_openai_supported_chat_filter_is_conservative_and_paid(self):
        model=connections.public_model('openai',{'id':'gpt-4o'})
        self.assertEqual(model['cavren']['price_kind'],'unknown')
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
        self.assertEqual(models[0]['cavren']['price_kind'],'unknown')
    def test_openai_uses_current_chat_token_limit(self):
        config=ProviderConfig('openai','gpt-4o','https://api.openai.com/v1','OPENAI_API_KEY','test-secret')
        provider=PreparedChatProvider(config,load_settings({}),MagicMock())
        body=provider._payload([Message('user','Hello')],stream=True)
        self.assertIn('max_completion_tokens',body);self.assertNotIn('max_tokens',body)
        self.assertNotIn('test-secret',json.dumps(body))

if __name__=='__main__':unittest.main()
