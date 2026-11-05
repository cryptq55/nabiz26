import unittest
from unittest.mock import patch

import media
import newsbot


class PhotoSubjectTests(unittest.TestCase):
    def test_generic_accident_does_not_search_for_unrelated_foreign_photo(self):
        article = {'title': 'Sivrihisar yolunda işçi servisi devrildi',
                   'image_query': ['traffic accident', 'trafik kazası', 'Eskişehir']}
        with patch.object(media, '_ordered') as search:
            self.assertIsNone(newsbot.archive_image(article, 'test'))
            search.assert_not_called()

    def test_named_subject_must_appear_in_the_article(self):
        self.assertEqual(media.subject_queries(
            ['Ayşe Ünlüce', 'Kazım Kurt', 'Eskişehir okul'],
            'Ayşe Ünlüce, Kurtuluş Kapalı Pazar Yeri’ni ziyaret etti.'), ['Ayşe Ünlüce'])

    def test_specific_product_or_building_remains_eligible(self):
        text = 'Togg T10F tanıtımı Ahmet Sezer Ortaokulu yakınında yapıldı.'
        self.assertEqual(media.subject_queries(['Togg T10F', 'Ahmet Sezer Ortaokulu'], text),
                         ['Togg T10F', 'Ahmet Sezer Ortaokulu'])


if __name__ == '__main__':
    unittest.main()
