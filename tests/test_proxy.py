import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
import newsbot


class ProxyTests(unittest.TestCase):
    def test_key_stays_in_header_and_editor_rules_are_sent(self):
        decision = {k: '' for k in newsbot.ARTICLE_SCHEMA['required']}
        decision['publish'] = False
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({'choices': [{'message': {'content': json.dumps(decision)}}]}).encode()
        with patch.dict(os.environ, {'NEWS_API_BASE': 'http://proxy.test/v1/', 'NEWS_API_KEY': 'test-private'}), \
                patch.object(newsbot.requests, 'post', return_value=response) as post:
            self.assertEqual(newsbot.write_article_proxy({'source_name': 'test', 'title': 'test'}, 'source', []), decision)
            args, kwargs = post.call_args
            self.assertEqual(args[0], 'http://proxy.test/v1/chat/completions')
            self.assertEqual(kwargs['headers']['Authorization'], 'Bearer test-private')
            self.assertNotIn('test-private', json.dumps(kwargs['json']))
            self.assertEqual(kwargs['json']['messages'][0]['content'], newsbot.SYSTEM_PROMPT)

    def test_proxy_outage_falls_back_to_gemini(self):
        # Bilgisayardaki CLIProxy kapalıyken bulut turu boşa gitmesin: Gemini yazar
        def collect(_, path):
            Path(path).write_text(json.dumps({'today': '05.11.2026', 'recent_titles': [],
                'queue': [{'key': 'unseen', 'source_name': 'test', 'title': 'test', 'text': 'source'}]}))
        decision = {k: '' for k in newsbot.ARTICLE_SCHEMA['required']}
        with patch.dict(os.environ, {'NEWS_API_BASE': 'http://proxy.test/v1', 'NEWS_API_KEY': 'test',
                                    'GEMINI_API_KEY': 'backup'}, clear=True), \
                patch.object(newsbot, 'collect_queue', side_effect=collect), \
                patch.object(newsbot, 'write_article_proxy', side_effect=requests.ConnectionError()), \
                patch.object(newsbot, 'write_article_gemini', return_value=decision) as gemini, \
                patch.object(newsbot, 'save_decisions') as save:
            newsbot.auto_run(1)
            gemini.assert_called_once()
            save.assert_called_once()
    def test_json_inside_code_fence_is_read(self):
        self.assertEqual(newsbot.json_from_text('```json\n{"publish": false}\n```'), {'publish': False})
        self.assertEqual(newsbot.json_from_text('İşte karar: {"a": 1} tamam'), {'a': 1})


if __name__ == '__main__':
    unittest.main()
