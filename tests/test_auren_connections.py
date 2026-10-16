"""Connection credentials, ordering and probe contracts; synthetic values only."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from integration import auren_settings as settings, auren_credentials as credentials
from integration import auren_connection_validation as validation
from integration import auren_canva_oauth as oauth
from integration.auren_connection_registry import CONNECTIONS
from scripts.auren_connection_inventory import parse_inventory, configured_fields

class Vault:
    def __init__(self,values=None,fail=''):
        self.values=dict(values or {});self.fail=fail
    def get(self,name): return self.values.get(name,'')
    def set(self,name,value):
        if name==self.fail: raise OSError('synthetic failure')
        self.values[name]=value
    def delete(self,name): self.values.pop(name,None)

class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.stack=contextlib.ExitStack()
        for obj in (settings,credentials): self.stack.enter_context(patch.object(obj,'STATE',self.root))
        self.stack.enter_context(patch.object(settings,'catalog',return_value=[]))
    def tearDown(self): self.stack.close();self.temp.cleanup()
    def test_exact_30_unique_connections_and_oauth_fields(self):
        self.assertEqual(len(CONNECTIONS),30)
        self.assertEqual(len(set(settings.PROVIDER_KEYS.values())),30)
        self.assertEqual(CONNECTIONS['cloudflare'].name,'Cloudflare Workers AI')
        self.assertEqual(CONNECTIONS['canva'].kind,'oauth')
        self.assertEqual([f.id for f in CONNECTIONS['canva'].extra],['client_id','redirect_uri'])
        self.assertEqual(CONNECTIONS['huggingface'].name,'Hugging Face Inference Providers')
    def test_order_roundtrip_uses_ids_and_keeps_image_preferences(self):
        settings.save_preferences({'image_width':768})
        order=list(reversed(CONNECTIONS))
        result=settings.save_preferences({'connection_order':order})
        self.assertEqual(settings.preferences()['connection_order'],order)
        self.assertEqual(result['image_width'],768)
        self.assertEqual((self.root/'auren_preferences.json').stat().st_mode&0o777,0o600)
    def test_order_rejects_unknown_duplicate_and_non_ids_without_overwrite(self):
        before=settings.save_preferences({'connection_order':['canva','openai']})
        for value in (None,{},['canva','canva'],['unknown'],[{}],[True]):
            with self.subTest(value=value),self.assertRaises(ValueError):settings.save_preferences({'connection_order':value})
            self.assertEqual(settings.preferences(),before)
    def test_order_is_independent_of_missing_saved_image_catalog_entry(self):
        settings.atomic_json(self.root/'auren_preferences.json',{'image_model_id':'removed-model'})
        self.assertEqual(settings.save_preferences({'connection_order':['openai']})['image_model_id'],'removed-model')
    def test_partial_bundle_preserves_other_fields_and_unrelated_secrets(self):
        vault=Vault({'CANVA_CLIENT_SECRET':'synthetic-secret','CANVA_CLIENT_ID':'synthetic-id','OTHER':'untouched'})
        settings.save_connection('canva',{'redirect_uri':oauth.DEFAULT_REDIRECT},vault)
        self.assertEqual(vault.get('CANVA_CLIENT_SECRET'),'synthetic-secret')
        self.assertEqual(vault.get('CANVA_CLIENT_ID'),'synthetic-id');self.assertEqual(vault.get('OTHER'),'untouched')
        for file in self.root.iterdir():self.assertNotIn('synthetic-secret',file.read_text())
    def test_bundle_failure_rolls_back_all_fields_and_metadata(self):
        settings.atomic_json(self.root/'provider_policy.json',{'unrelated':True})
        vault=Vault({'CLOUDFLARE_API_TOKEN':'synthetic-old'},fail='CLOUDFLARE_ACCOUNT_ID')
        with self.assertRaises(OSError):settings.save_connection('cloudflare',{'key':'synthetic-new','account_id':'a'*32},vault)
        self.assertEqual(vault.get('CLOUDFLARE_API_TOKEN'),'synthetic-old')
        self.assertEqual(json.loads((self.root/'provider_policy.json').read_text()),{'unrelated':True})
        self.assertFalse((self.root/'credential_inventory.json').exists())
    def test_new_credential_invalidates_previous_check(self):
        settings.atomic_json(self.root/'connection_checks.json',{'voyage':{'status':'success','reason':'ok'}})
        settings.save_connection('voyage',{'key':'synthetic-new'},Vault())
        self.assertNotIn('voyage',validation.validation_results())
    def test_connection_fields_do_not_accept_arbitrary_vault_names(self):
        vault=Vault({'OTHER':'untouched'})
        for id,values in [('canva',{'OPENAI_API_KEY':'synthetic'}),('openai',{'key':'x x x x x'}),('bedrock',{'region':'bad/region'}),('cloudflare',{'account_id':'bad'})]:
            with self.assertRaises(ValueError):settings.save_connection(id,values,vault)
        self.assertEqual(vault.values,{'OTHER':'untouched'})
    def test_public_state_never_contains_credentials_and_preserves_ids(self):
        from types import SimpleNamespace
        with patch.object(settings,'connection_settings',return_value=SimpleNamespace(providers={})):
            state=settings.public_state()
        self.assertEqual({c['id'] for c in state['connections']},set(CONNECTIONS))
        canva=next(c for c in state['connections'] if c['id']=='canva')
        self.assertEqual(canva['count'],0);self.assertEqual(canva['auth_kind'],'oauth')
        self.assertEqual([f['id'] for f in canva['fields']],['key','client_id','redirect_uri'])
    def test_inventory_heading_fields_and_no_missing_value_invention(self):
        result=parse_inventory('Canva Connect\nClient ID: synthetic-client\nClient secret: synthetic-secret\nRedirect URL: ainda falta configurar\nAmazon Bedrock\nAPI Key: synthetic-bedrock\nCloudfare\nChave de API: synthetic-token\nAssembly AI API\nAPI Key: synthetic-assembly')
        self.assertEqual(result['canva'],{'client_id':'synthetic-client','key':'synthetic-secret'})
        self.assertEqual(result['bedrock'],{'key':'synthetic-bedrock'})
        self.assertNotIn('account_id',result['cloudflare']);self.assertIn('assemblyai',result)

    def test_configured_fields_never_supply_api_keys_or_tokens(self):
        vault=Vault({'CLOUDFLARE_API_TOKEN':'synthetic-old','CLOUDFLARE_ACCOUNT_ID':'a'*32,
                     'ANTHROPIC_API_KEY':'synthetic-old','CANVA_ACCESS_TOKEN':'synthetic-old'})
        self.assertEqual(configured_fields('anthropic',{},vault),{})
        self.assertEqual(configured_fields('cloudflare',{'key':'synthetic-new'},vault),{'key':'synthetic-new','account_id':'a'*32})
        self.assertEqual(configured_fields('canva',{},vault),{})

    def test_import_of_unchanged_oauth_client_preserves_existing_tokens(self):
        from scripts import auren_connection_inventory as inventory
        document=self.root/'synthetic-inventory.txt'
        document.write_text('Canva Connect\nClient ID: synthetic-client\nClient secret: synthetic-secret')
        vault=Vault({'CANVA_CLIENT_ID':'synthetic-client','CANVA_CLIENT_SECRET':'synthetic-secret','CANVA_ACCESS_TOKEN':'synthetic-access'})
        settings.atomic_json(self.root/'provider_policy.json',{'connection_credentials_updated':{'canva':'2026-10-15T00:00:00Z'}})
        output=io.StringIO()
        with patch('sys.argv',['inventory','--document',str(document),'--rotated-confirmed','--import-vault']),patch.object(credentials,'AurenVault',return_value=vault),patch.object(settings,'save_connection') as save,contextlib.redirect_stdout(output):
            inventory.main()
        save.assert_not_called()
        self.assertEqual(vault.get('CANVA_ACCESS_TOKEN'),'synthetic-access')
        self.assertNotIn('synthetic-',output.getvalue())

    def test_each_probe_uses_official_auth_and_does_not_reveal_response(self):
        for id,spec in CONNECTIONS.items():
            seen=[]
            def respond(request):
                seen.append(request)
                if 'auren-invalid' in str(dict(request.headers)):return httpx.Response(401,json={})
                return httpx.Response(200,json={'data':[{'id':'nvidia/nemotron-3-embed-1b','embedding':[0.0]}],
                    'models':[{'name':'gemma4:31b'}],'choices':[{'message':{'content':'Hi'}}],
                    'availableBalance':'0','balanceCents':0,'modelSummaries':[],
                    'api_key_blocked':False,'api_key_disabled':False,'team_blocked':False,'acls':['api-key:model:*'],
                    'success':True,'result':[], 'sensitive_response':'must-not-appear'})
            with self.subTest(id=id),httpx.Client(transport=httpx.MockTransport(respond)) as client:
                result=validation.probe(id,{'key':'synthetic-key','access_token':'synthetic-access','account_id':'a'*32,'region':'us-east-1'},client,allow_inference=True)
                self.assertEqual(result,('success','inference_ok' if id in ('nvidia','ollama') else 'account_ok' if id=='hyperbolic' else 'ok'))
                if seen:
                    self.assertEqual(seen[0].url.scheme,'https')
                    self.assertNotIn('synthetic-key',str(seen[0].url));self.assertNotIn('synthetic-access',str(seen[0].url))
                    self.assertNotIn('chat/completions',seen[0].url.path)
                    if id=='assemblyai':self.assertEqual(seen[0].headers['Authorization'],'synthetic-key')
                    if id=='deepgram':self.assertEqual(seen[0].headers['Authorization'],'Token synthetic-key')
                    if id=='anthropic':self.assertEqual(seen[0].headers['x-api-key'],'synthetic-key')
                    if id=='canva':self.assertEqual(seen[0].headers['Authorization'],'Bearer synthetic-access')
                    if id=='voyage':self.assertEqual(json.loads(seen[0].content)['input'],['test'])
    def test_public_models_do_not_validate_authentication(self):
        with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'data':[]}))) as client:
            self.assertEqual(validation.probe('deepinfra',{'key':'synthetic'},client),('pending','public_catalog'))

    def test_inference_checks_use_listed_models_and_bounded_output(self):
        for provider in ('nvidia','ollama'):
            seen=[]
            def respond(request):
                seen.append(request)
                if request.method=='GET':
                    return httpx.Response(200,json={'data':[{'id':'nvidia/nemotron-3-embed-1b'}],'models':[{'name':'gemma4:31b'}]})
                return httpx.Response(200,json={'data':[{'embedding':[0.0]}],'choices':[{'message':{'content':'Hi'}}]})
            with self.subTest(provider=provider),httpx.Client(transport=httpx.MockTransport(respond)) as client:
                self.assertEqual(validation.probe(provider,{'key':'synthetic'},client,allow_inference=True),('success','inference_ok'))
            self.assertEqual(len(seen),2)
            body=json.loads(seen[1].content)
            if provider=='nvidia':
                self.assertEqual(body['input'],['test']);self.assertEqual(body['input_type'],'query')
            else:
                self.assertEqual(body['max_tokens'],1);self.assertEqual(body['messages'],[{'role':'user','content':'Hi'}])
            seen=[]
            with httpx.Client(transport=httpx.MockTransport(lambda r: (seen.append(r) or httpx.Response(200,json={'data':[],'models':[]})))) as client:
                self.assertEqual(validation.probe(provider,{'key':'synthetic'},client,allow_inference=True),('incompatible','endpoint'))
            self.assertEqual(len(seen),1)

    def test_xai_blocked_flag_is_failure_even_with_http_200(self):
        for flag in ('api_key_blocked','api_key_disabled','team_blocked'):
            data={'api_key_blocked':False,'api_key_disabled':False,'team_blocked':False,'acls':[]}
            data[flag]=True
            with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=data))) as client:
                self.assertEqual(validation.probe('xai',{'key':'synthetic'},client),('failed','account_blocked'))

    def test_new_account_contracts_reject_empty_responses(self):
        for provider in ('xai','novita','hyperbolic','cloudflare','bedrock'):
            with self.subTest(provider=provider),httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={}))) as client:
                self.assertEqual(validation.probe(provider,{'key':'synthetic','account_id':'a'*32,'region':'us-east-1'},client),('failed','invalid_response'))

    def test_current_cartesia_auth_and_regional_bedrock_no_generation(self):
        seen=[]
        def respond(request):
            seen.append(request)
            return httpx.Response(401,json={}) if 'auren-invalid' in request.headers.get('Authorization','') else httpx.Response(200,json={'modelSummaries':[]})
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            self.assertEqual(validation.probe('bedrock',{'key':'synthetic','region':'us-east-1'},client),('success','ok'))
            self.assertEqual(validation.probe('cartesia',{'key':'synthetic'},client),('success','ok'))
        self.assertEqual(seen[0].url.host,'bedrock.us-east-1.amazonaws.com')
        self.assertEqual(seen[0].url.path,'/foundation-models')
        self.assertTrue(all(r.method=='GET' for r in seen))
        self.assertEqual(seen[-1].headers['Authorization'],'Bearer synthetic')
        self.assertEqual(seen[-1].headers['Cartesia-Version'],'2026-08-14')

    def test_broken_embedding_or_chat_payload_does_not_validate(self):
        for provider in ('nvidia','ollama'):
            def respond(request):
                if request.method=='GET':return httpx.Response(200,json={'data':[{'id':'nvidia/nemotron-3-embed-1b'}],'models':[{'name':'gemma4:31b'}]})
                return httpx.Response(200,json={'data':[{}],'choices':[{'message':{'content':''}}]})
            with self.subTest(provider=provider),httpx.Client(transport=httpx.MockTransport(respond)) as client:
                self.assertEqual(validation.probe(provider,{'key':'synthetic'},client,allow_inference=True),('failed','invalid_response'))
    def test_statuses_are_sanitized_and_missing_inputs_never_call_network(self):
        for id,values,reason in [('bedrock',{'key':'synthetic'},'missing_region'),('cloudflare',{'key':'synthetic'},'missing_account_id'),('canva',{'key':'synthetic'},'oauth_required')]:
            with patch.object(validation.httpx,'Client') as client:
                result=validation.validate_connection(id,values=values)
                client.return_value.__enter__.return_value.get.assert_not_called()
                self.assertEqual(result['reason'],reason)
        for code,status,reason in [(401,'failed','auth_error'),(403,'failed','auth_error'),(429,'failed','rate_limit'),(404,'incompatible','endpoint'),(503,'failed','unavailable')]:
            original=httpx.Client
            def respond(r):return httpx.Response(code,json={'error':'synthetic-secret-response'})
            with patch.object(validation.httpx,'Client',side_effect=lambda **kw:original(transport=httpx.MockTransport(respond),**kw)):
                output=io.StringIO()
                with contextlib.redirect_stdout(output),contextlib.redirect_stderr(output):result=validation.validate_connection('openai',values={'key':'synthetic'})
                self.assertEqual((result['status'],result['reason']),(status,reason))
                self.assertNotIn('synthetic',json.dumps(result));self.assertEqual(output.getvalue(),'')
        self.assertNotIn('synthetic', (self.root/'connection_checks.json').read_text())
    def test_rotation_guard_never_opens_http_client_or_reads_vault(self):
        with patch.object(validation,'AurenVault') as vault,patch.object(validation.httpx,'Client') as client:
            result=validation.validate_connection('openai',rotated=False)
        self.assertEqual(result['reason'],'rotation_required');client.assert_not_called();vault.assert_not_called()
    def test_oauth_redirect_rejects_remote_urls_tokens_and_unexpected_paths(self):
        for uri in ('https://evil.example/oauth/canva/callback','http://127.0.0.1:8176/oauth/canva/callback?token=x','http://user@localhost:8176/oauth/canva/callback','http://localhost:8176/other'):
            with self.assertRaises(ValueError):oauth.redirect_address(uri)
        self.assertEqual(oauth.redirect_address(oauth.DEFAULT_REDIRECT).hostname,'127.0.0.1')
    def test_oauth_tokens_are_vault_only_and_rollback_on_failure(self):
        vault=Vault({'CANVA_ACCESS_TOKEN':'synthetic-old'})
        oauth.store_tokens(vault,{'access_token':'synthetic-access','refresh_token':'synthetic-refresh','expires_in':3600})
        self.assertEqual(oauth.access_token(vault),'synthetic-access');self.assertFalse(list(self.root.iterdir()))
        with self.assertRaises(ValueError):oauth.store_tokens(vault,{'access_token':'bad'})
        self.assertEqual(vault.get('CANVA_ACCESS_TOKEN'),'synthetic-access')

    def test_unconfirmed_existing_vault_is_not_used_for_validation(self):
        with patch.object(validation,'AurenVault') as vault,patch.object(validation.httpx,'Client') as client:
            result=validation.validate_connection('anthropic')
        self.assertEqual(result['reason'],'rotation_required');vault.assert_not_called();client.assert_not_called()

    def test_oauth_callback_requires_state_uses_pkce_and_stores_only_in_vault(self):
        import socket
        from urllib.parse import urlsplit,parse_qs,urlencode
        from urllib.request import urlopen
        from urllib.error import HTTPError
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        uri=f'http://127.0.0.1:{port}/oauth/canva/callback'
        vault=Vault({'CANVA_CLIENT_ID':'synthetic-client','CANVA_CLIENT_SECRET':'synthetic-secret','CANVA_REDIRECT_URI':uri})
        from unittest.mock import MagicMock
        client=MagicMock();client.post.return_value=httpx.Response(200,json={'access_token':'synthetic-access','refresh_token':'synthetic-refresh','expires_in':3600})
        with patch.object(oauth.httpx,'Client') as factory:
            factory.return_value.__enter__.return_value=client
            authorization=oauth.start(vault);params=parse_qs(urlsplit(authorization['url']).query)
            self.assertEqual(params['code_challenge_method'],['S256']);self.assertEqual(params['scope'],['profile:read'])
            self.assertNotIn('synthetic-secret',authorization['url']);self.assertNotIn('code_verifier',authorization['url'])
            with self.assertRaises(HTTPError):urlopen(uri+'?state=wrong&code=synthetic-code',timeout=3)
            client.post.assert_not_called()
            with urlopen(uri+'?'+urlencode({'state':params['state'][0],'code':'synthetic-code'}),timeout=3) as response:
                body=response.read().decode()
                self.assertEqual(response.headers['Referrer-Policy'],'no-referrer')
                self.assertNotIn('synthetic',body);self.assertIn('history.replaceState',body)
            oauth._active.join(3)
        self.assertFalse(oauth._active.is_alive());self.assertEqual(vault.get('CANVA_ACCESS_TOKEN'),'synthetic-access')
        kwargs=client.post.call_args.kwargs
        import base64,hashlib
        challenge=base64.urlsafe_b64encode(hashlib.sha256(kwargs['data']['code_verifier'].encode()).digest()).decode().rstrip('=')
        self.assertEqual(challenge,params['code_challenge'][0]);self.assertEqual(kwargs['data']['redirect_uri'],uri)
        self.assertFalse(list(self.root.iterdir()))

    def test_expired_oauth_token_refreshes_in_vault_without_files(self):
        from unittest.mock import MagicMock
        vault=Vault({'CANVA_ACCESS_TOKEN':'synthetic-expired','CANVA_REFRESH_TOKEN':'synthetic-refresh','CANVA_TOKEN_EXPIRES_AT':'0'})
        client=MagicMock();client.post.return_value=httpx.Response(200,json={'access_token':'synthetic-new','refresh_token':'synthetic-rotated','expires_in':3600})
        with patch.object(oauth.httpx,'Client') as factory:
            factory.return_value.__enter__.return_value=client
            self.assertEqual(oauth.access_token(vault),'synthetic-new')
        self.assertEqual(vault.get('CANVA_REFRESH_TOKEN'),'synthetic-rotated');self.assertFalse(list(self.root.iterdir()))

if __name__=='__main__':unittest.main()
