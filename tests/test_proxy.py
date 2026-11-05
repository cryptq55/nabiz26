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

    def test_proxy_outage_does_not_use_gemini_or_consume_sources(self):
        def collect(_, path):
            Path(path).write_text(json.dumps({'today': '05.11.2026', 'recent_titles': [],
                'queue': [{'key': 'unseen', 'source_name': 'test', 'title': 'test', 'text': 'source'}]}))
        with patch.dict(os.environ, {'NEWS_API_BASE': 'http://proxy.test/v1', 'NEWS_API_KEY': 'test',
                                    'GEMINI_API_KEY': 'backup'}, clear=True), \
                patch.object(newsbot, 'collect_queue', side_effect=collect), \
                patch.object(newsbot, 'write_article_proxy', side_effect=requests.ConnectionError()), \
                patch.object(newsbot, 'write_article_gemini') as gemini, \
                patch.object(newsbot, 'save_decisions') as save:
            with self.assertRaisesRegex(RuntimeError, 'hiçbir kaynağı'):
                newsbot.auto_run(1)
            gemini.assert_not_called()
            save.assert_not_called()


if __name__ == '__main__':
    unittest.main()
