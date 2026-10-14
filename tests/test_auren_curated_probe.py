import unittest
from auren_curated_flow_probe import research_checked

class ResearchCitationChecks(unittest.TestCase):
    def test_numbered_reference_is_valid_only_inside_retrieved_source_range(self):
        sources=['https://console.groq.com/docs/models']
        self.assertTrue(research_checked('O ID é openai/gpt-oss-120b [1].',sources))
        self.assertFalse(research_checked('O ID é openai/gpt-oss-120b [2].',sources))

    def test_invented_link_and_missing_content_do_not_pass(self):
        sources=['https://console.groq.com/docs/models']
        self.assertTrue(research_checked('openai/gpt-oss-120b https://console.groq.com/docs/models',sources))
        self.assertFalse(research_checked('openai/gpt-oss-120b https://example.com/fake',sources))
        self.assertFalse(research_checked('Não confirmado [1].',sources))

if __name__=='__main__':unittest.main()
