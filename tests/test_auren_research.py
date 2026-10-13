import json
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from cavren.errors import CavrenError
from integration.auren_research import model_plan, plan


class BoundedPlanner(unittest.TestCase):
    def run_planner(self, calls, prompt='Pesquise limites Cohere com fontes oficiais', deadline=None):
        config = SimpleNamespace(name='cohere', model='tested', api_key='synthetic-key')
        record = {'ok': True, 'model': 'cavren:cohere:tested'}
        requests = []

        def respond(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={'message': {'tool_calls': calls}})

        with patch('integration.auren_tasks.task_evidence', return_value={'agent_research_planner': record}), patch('integration.auren_validation.verified', return_value=True), httpx.Client(transport=httpx.MockTransport(respond)) as client:
            result = model_plan(client, config, prompt, deadline if deadline is not None else time.monotonic() + 10)
        return result, requests

    @staticmethod
    def call(query, name='search_docs'):
        return {'function': {'name': name, 'arguments': json.dumps({'query': query})}}

    def test_only_bounded_verified_search_is_exposed(self):
        (queries, domains, planned), requests = self.run_planner([self.call('site:docs.cohere.com API trial rate limits')])
        self.assertTrue(planned)
        self.assertEqual(len(queries), 1)
        self.assertEqual(domains, ('docs.cohere.com',))
        self.assertEqual([tool['function']['name'] for tool in requests[0]['tools']], ['search_docs'])

    def test_other_tools_untrusted_domains_and_excess_calls_fall_back(self):
        prompt = 'Pesquise limites Cohere com fontes oficiais'
        for calls in ([self.call('site:docs.cohere.com limits', 'execute_code')], [self.call('site:evil.example limits')], [self.call('site:docs.cohere.com limits')] * 4):
            with self.subTest(calls=calls):
                result, _ = self.run_planner(calls, prompt)
                self.assertEqual(result, (*plan(prompt), False))

    def test_expired_deadline_prevents_call(self):
        with self.assertRaises(CavrenError):
            self.run_planner([], deadline=time.monotonic() - 1)
