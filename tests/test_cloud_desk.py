import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import requests

import newsbot


class CloudDeskTests(unittest.TestCase):
    def test_missing_credentials_does_not_collect_or_consume_sources(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(newsbot, "collect_queue") as collect:
            with self.assertRaisesRegex(RuntimeError, "API_KEY"):
                newsbot.auto_run(2)
            collect.assert_not_called()

    def test_model_failure_leaves_unprocessed_source_unseen(self):
        first = {"key": "first", "source_name": "test", "title": "ilk", "text": "metin"}
        second = {**first, "key": "second", "title": "ikinci"}
        decision = {"publish": False, "skip_reason": "eski haber", "title": "", "spot": "",
                    "body": "", "category": "Gündem", "district": "Merkez", "tags": [],
                    "importance": 1, "reel": False, "image_query": []}

        def collect(_, path):
            Path(path).write_text(json.dumps({"today": "05.11.2026", "recent_titles": [],
                                             "queue": [first, second]}))

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            articles = root / "articles"
            articles.mkdir()
            with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only"}, clear=True), \
                    patch.object(newsbot, "ROOT", root), \
                    patch.object(newsbot, "ARTICLES_DIR", articles), \
                    patch.object(newsbot, "SEEN_FILE", root / "seen.json"), \
                    patch.object(newsbot, "collect_queue", side_effect=collect), \
                    patch.object(newsbot, "write_article_gemini",
                                 side_effect=[decision, RuntimeError("Gemini hız sınırı")]):
                newsbot.auto_run(2)
                seen = json.loads((root / "seen.json").read_text())
                self.assertIn("first", seen)
                self.assertNotIn("second", seen)

    def test_http_error_cannot_include_key_in_request_url(self):
        key = "test-only-private-value"

        def fail(url, **kwargs):
            request = requests.Request("POST", url, params=kwargs.get("params"),
                                       headers=kwargs.get("headers")).prepare()
            response = requests.Response()
            response.status_code = 403
            response.url = request.url
            response.request = request
            return response

        with patch.dict(os.environ, {"GEMINI_API_KEY": key}), \
                patch.object(newsbot.requests, "post", side_effect=fail):
            with self.assertRaises(requests.HTTPError) as error:
                newsbot.write_article_gemini({"source_name": "test", "title": "test"}, "text", [])
            self.assertNotIn(key, str(error.exception))
            self.assertNotIn(key, error.exception.request.url)
            self.assertEqual(error.exception.request.headers["x-goog-api-key"], key)

    def test_temporary_overload_is_retried_before_giving_up(self):
        failed = requests.Response()
        failed.status_code = 503
        success = requests.Response()
        success.status_code = 200
        decision = {field: None for field in newsbot.ARTICLE_SCHEMA['required']}
        success._content = json.dumps({'candidates': [{'content': {'parts': [
            {'text': json.dumps(decision)}]}}]}).encode()
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-only'}), \
                patch.object(newsbot.requests, 'post', side_effect=[failed, failed, success]), \
                patch.object(newsbot.time, 'sleep'):
            result = newsbot.write_article_gemini({'source_name': 'test', 'title': 'test'}, 'text', [])
            self.assertEqual(result, decision)

    def test_total_model_outage_fails_without_saving_decisions(self):
        def collect(_, path):
            Path(path).write_text(json.dumps({'today': '05.11.2026', 'recent_titles': [],
                'queue': [{'key': 'unseen', 'source_name': 'test', 'title': 'test', 'text': 'text'}]}))
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-only'}, clear=True), \
                patch.object(newsbot, 'collect_queue', side_effect=collect), \
                patch.object(newsbot, 'write_article_gemini', side_effect=RuntimeError('Gemini hız sınırı')), \
                patch.object(newsbot, 'save_decisions') as save:
            with self.assertRaisesRegex(RuntimeError, 'hiçbir kaynağı'):
                newsbot.auto_run(1)
            save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
