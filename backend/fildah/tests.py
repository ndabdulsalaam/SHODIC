from django.test import TestCase


class FildahPublicApiTests(TestCase):
    def test_home_endpoint_returns_brand_metadata(self):
        response = self.client.get('/home/')

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['brand']['name'], 'Fildah')
        self.assertEqual(payload['primary_product']['slug'], 'rxchat')

    def test_products_endpoint_describes_shared_auth_and_rxchat(self):
        response = self.client.get('/products/')

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['auth']['namespace'], '/auth/')
        self.assertEqual(payload['products'][0]['api_namespace'], '/rxchat/')

    def test_docs_endpoint_returns_starter_sections(self):
        response = self.client.get('/docs/')

        self.assertEqual(response.status_code, 200)
        section_slugs = {section['slug'] for section in response.json()['sections']}
        self.assertIn('overview', section_slugs)
        self.assertIn('rxchat', section_slugs)

    def test_developer_api_endpoint_lists_root_and_product_namespaces(self):
        response = self.client.get('/developers/api/')

        self.assertEqual(response.status_code, 200)
        paths = {namespace['path'] for namespace in response.json()['namespaces']}
        self.assertEqual(
            paths,
            {'/', '/auth/', '/rxchat/'},
        )
