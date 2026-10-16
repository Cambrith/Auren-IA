"""Local bridge URL guard, authenticated API shape, no real provider calls."""
import unittest
from unittest.mock import AsyncMock,patch
from fastapi import HTTPException
from pydantic import ValidationError
from open_webui.routers import auren

class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_remote_or_disguised_hosts_never_receive_bridge_token(self):
        for url in ('https://remote.example/v1','http://127.0.0.1:123@remote.example/v1','http://127.0.0.1:bad/v1'):
            async def config(key):return [url] if key=='openai.api_base_urls' else ['test-token']
            with patch.object(auren.Config,'get',side_effect=config),patch.object(auren.httpx,'AsyncClient') as client:
                with self.assertRaises(HTTPException) as error:await auren.bridge_request('GET','/auren/state')
                self.assertEqual(error.exception.status_code,503);client.assert_not_called()
    async def test_invalid_image_prompt_rejected_before_bridge(self):
        for prompt in (' ','x'*12001):
            with patch.object(auren,'bridge_request',new_callable=AsyncMock) as bridge:
                with self.assertRaises(HTTPException):await auren.generate_image(auren.ImageForm(model='test',prompt=prompt),user=object())
                bridge.assert_not_called()
    async def test_credential_repr_is_redacted(self):
        form=auren.CredentialForm(provider='nvidia',key='private-test-secret')
        self.assertNotIn('private-test-secret',repr(form))
    async def test_image_test_uses_explicit_cost_gate(self):
        with patch.object(auren,'bridge_request',new_callable=AsyncMock,return_value={'files':[]}) as bridge:
            await auren.generate_image(auren.ImageForm(model='test',prompt='A blue sphere'),user=object())
            body=bridge.call_args.args[2]
            self.assertIs(body['cavren_billing_confirmed'],False)
            self.assertTrue(body['lunvri_image_generation'])
            self.assertIs(body['stream'],False)

    async def test_multifield_credentials_are_redacted_and_forwarded_only_to_bridge(self):
        form=auren.CredentialForm(provider='canva',fields={'key':'synthetic-secret','client_id':'synthetic-client'})
        self.assertNotIn('synthetic-secret',repr(form));self.assertNotIn('synthetic-client',repr(form))
        with patch.object(auren,'bridge_request',new_callable=AsyncMock,return_value={'saved':True}) as bridge:
            await auren.provider(form,user=object())
            self.assertEqual(bridge.call_args.args[2]['fields'],{'key':'synthetic-secret','client_id':'synthetic-client'})

    async def test_connection_validation_and_oauth_use_authenticated_bridge(self):
        with patch.object(auren,'bridge_request',new_callable=AsyncMock,return_value={}) as bridge:
            await auren.validate_connection(auren.ConnectionForm(provider='canva'),user=object())
            self.assertEqual(bridge.call_args.args,('POST','/auren/connections/validate',{'provider':'canva'}))
            await auren.start_canva(user=object())
            self.assertEqual(bridge.call_args.args,('POST','/auren/oauth/canva/start',{}))

if __name__=='__main__':unittest.main()
