"""Provider review contracts; synthetic secrets, isolated state, no paid network calls."""
import contextlib
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from integration import auren_settings as settings,auren_connection_validation as validation,lunvri_connections as connections
from integration.auren_bedrock import validate_base_url,discover
from scripts.auren_connection_inventory import parse_inventory,resolve_references
from scripts.auren_finalize_inventory import render_document
from integration.auren_connection_registry import CONNECTIONS

class Vault:
    def get(self,name):return {'OPENAI_API_KEY':'synthetic-openai','CANVA_CLIENT_ID':'synthetic-client'}.get(name,'')

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.stack=contextlib.ExitStack()
        for module in (settings,connections):self.stack.enter_context(patch.object(module,'STATE',Path(self.temp.name)))
    def tearDown(self):self.stack.close();self.temp.cleanup()

    def test_bedrock_urls_are_bound_to_aws_and_the_selected_region(self):
        base='https://bedrock-runtime.sa-east-1.amazonaws.com/openai/v1'
        self.assertEqual(validate_base_url(base,'sa-east-1'),base)
        for value in (base+'?token=synthetic',base.replace('sa-east-1','us-east-1'),base.replace('amazonaws.com','evil.example'),'http://127.0.0.1/v1'):
            with self.assertRaises(ValueError):validate_base_url(value,'sa-east-1')

    def test_metadata_never_overwrites_keys_and_references_are_provider_bound(self):
        text='Amazon Bedrock\nAPI Key: synthetic-bedrock\nBase URL: https://bedrock-runtime.sa-east-1.amazonaws.com/openai/v1\nSituação: indisponível\nRegião: sa-east-1'
        parsed=parse_inventory(text)
        self.assertEqual(parsed['bedrock']['key'],'synthetic-bedrock')
        self.assertEqual(parsed['bedrock']['region'],'sa-east-1')
        text='OpenAI API\nCredencial: cofre://OPENAI_API_KEY'
        self.assertNotIn('key',parse_inventory(text)['openai'])
        self.assertEqual(resolve_references(text,parse_inventory(text),Vault())['openai']['key'],'synthetic-openai')
        text='Anthropic API (Claude)\nCredencial: cofre://OPENAI_API_KEY'
        with self.assertRaises(ValueError):resolve_references(text,parse_inventory(text),Vault())

    def test_default_checks_never_generate_or_consume_embedding_tokens(self):
        for provider in ('nvidia','ollama','voyage'):
            seen=[]
            def respond(request):
                seen.append(request)
                self.assertEqual(request.method,'GET')
                return httpx.Response(200,json={'object':'list','data':[],'models':[]})
            with httpx.Client(transport=httpx.MockTransport(respond)) as client:
                result=validation.probe(provider,{'key':'synthetic'},client)
            self.assertEqual(result[0],'pending')
            if provider=='voyage':
                self.assertEqual(len(seen),2)
                self.assertTrue(all(r.url.path=='/v1/files' and r.url.params.get('limit')=='1' for r in seen))

    def test_voyage_authenticates_without_running_embeddings(self):
        def respond(request):
            self.assertEqual(request.method,'GET')
            self.assertEqual(request.url.path,'/v1/files')
            if request.headers['Authorization']=='Bearer synthetic':
                return httpx.Response(200,json={'object':'list','data':[]})
            return httpx.Response(401,json={})
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            self.assertEqual(validation.probe('voyage',{'key':'synthetic'},client),('success','ok'))

    def test_bedrock_discovery_does_not_return_arns_or_invoke_models(self):
        def respond(request):
            self.assertEqual(request.method,'GET');self.assertEqual(request.url.path,'/foundation-models')
            return httpx.Response(200,json={'modelSummaries':[{'modelId':'synthetic.model','modelName':'Synthetic','modelArn':'must-not-be-copied'}]})
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            models,error=discover({'key':'synthetic','region':'sa-east-1'},client)
        self.assertIsNone(error);self.assertFalse(models[0]['inference_tested']);self.assertNotIn('must-not',json.dumps(models))

    def test_new_llm_connections_use_explicit_urls_and_billing_gate(self):
        env={'CEREBRAS_API_KEY':'synthetic','DEEPINFRA_API_KEY':'synthetic','NOVITA_API_KEY':'synthetic',
             'AWS_BEARER_TOKEN_BEDROCK':'synthetic','AWS_REGION':'sa-east-1',
             'AUREN_BEDROCK_BASE_URL':'https://bedrock-runtime.sa-east-1.amazonaws.com/openai/v1'}
        configured=connections.connection_settings(env)
        for provider in ('cerebras','deepinfra','novita','bedrock'):
            self.assertEqual(configured.providers[provider].api_key,'synthetic')
            self.assertIn(provider,connections.PAID_PROVIDERS)

    def test_disabled_providers_are_not_probed_or_auto_activated(self):
        settings.atomic_json(settings.STATE/'provider_policy.json',{'provider_availability':{'xai':{'disabled':True,'reason':'account_blocked'}}})
        with patch.object(validation.httpx,'Client') as client,patch.object(validation,'AurenVault') as vault:
            result=validation.validate_connection('xai',values={'key':'synthetic'})
        self.assertEqual(result['reason'],'account_blocked');client.assert_not_called();vault.assert_not_called()
        self.assertFalse(connections.connection_settings({'XAI_API_KEY':'synthetic'}).providers['xai'].api_key)

    def test_canonical_inventory_is_alphabetical_and_contains_references_only(self):
        results={id:{'message':'Synthetic result','checked_at':None} for id in CONNECTIONS}
        text=render_document({'openai':{'key':'synthetic-secret'}},results,Vault(),'SYNTHETIC_ARCHIVE')
        headings=[line[3:] for line in text.splitlines() if line.startswith('## ')]
        self.assertEqual(headings,sorted(headings,key=str.casefold));self.assertEqual(len(headings),30)
        self.assertNotIn('synthetic-secret',text);self.assertNotIn('synthetic-openai',text)
        self.assertIn('cofre://OPENAI_API_KEY',text)

    def test_all_provider_assets_exist_and_match_the_recorded_hash(self):
        root=Path(__file__).resolve().parents[1]/'static/brand-icons'
        icons=json.loads((root/'provider-sources.json').read_text())
        self.assertEqual(set(icons),set(CONNECTIONS))
        for id,icon in icons.items():
            with self.subTest(provider=id):
                path=root/icon['file'];self.assertTrue(path.is_file())
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),icon['sha256'])
                if icon['official']:self.assertTrue(icon['source'].startswith('https://'))

    def test_every_canonical_heading_resolves_only_its_own_vault_entry(self):
        class AllVault:
            def get(self,name):return 'synthetic-'+name
        values={id:{'key':'synthetic-'+spec.key} for id,spec in CONNECTIONS.items()}
        results={id:{'message':'Synthetic result','checked_at':None} for id in CONNECTIONS}
        text=render_document(values,results,AllVault(),'SYNTHETIC_ARCHIVE')
        resolved=resolve_references(text,parse_inventory(text),AllVault())
        for id,spec in CONNECTIONS.items():
            self.assertEqual(resolved[id]['key'],'synthetic-'+spec.key)

if __name__=='__main__':unittest.main()
