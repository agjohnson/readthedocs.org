from django.test import TestCase
import json
import base64


super_auth = base64.b64encode('super:test')
eric_auth = base64.b64encode('eric:test')


class APIBuildTests(TestCase):
    fixtures = ['eric.json', 'test_data.json']

    def test_make_build(self):
        """
        Test that a superuser can use the API
        """
        post_data = {
            "project": "/api/v1/project/1/",
            "version": "/api/v1/version/1/",
            "success": True,
            "output": "Test Output",
            "error": "Test Error",
        }
        resp = self.client.post('/api/v1/build/', data=json.dumps(post_data),
                                content_type='application/json',
                                HTTP_AUTHORIZATION='Basic %s' % super_auth)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp['location'],
                         'http://testserver/api/v1/build/1/')
        resp = self.client.get('/api/v1/build/1/', data={'format': 'json'},
                               HTTP_AUTHORIZATION='Basic %s' % super_auth)
        self.assertEqual(resp.status_code, 200)
        obj = json.loads(resp.content)
        self.assertEqual(obj['output'], 'Test Output')

    def test_make_build_with_commands(self):
        """
        Make a build and add a list of commands executed
        """
        post_data = {
            "project": 1,
            "version": 1,
            "success": True,
        }
        # Add build
        resp = self.client.post('/api/v2/build/', data=json.dumps(post_data),
                                content_type='application/json',
                                HTTP_AUTHORIZATION='Basic %s' % super_auth)
        self.assertEqual(resp.status_code, 201)
        obj = json.loads(resp.content)
        self.assertEqual(obj['id'], 1)
        resp = self.client.get('/api/v2/build/1/', data={'format': 'json'},
                               HTTP_AUTHORIZATION='Basic %s' % super_auth)
        self.assertEqual(resp.status_code, 200)
        obj = json.loads(resp.content)

        # Add build command
        post_data = {
            "build": obj['id'],
            "command": "echo test",
            "exit_code": 1,
            "output": "test",
        }
        resp = self.client.post('/api/v2/buildcommand/',
                                data=json.dumps(post_data),
                                content_type='application/json',
                                HTTP_AUTHORIZATION='Basic %s' % super_auth)
        self.assertEqual(resp.status_code, 201)
        obj = json.loads(resp.content)
        self.assertEqual(obj['id'], 1)
        resp = self.client.get('/api/v2/buildcommand/1/', data={'format': 'json'},
                               HTTP_AUTHORIZATION='Basic %s' % super_auth)
        self.assertEqual(resp.status_code, 200)
        obj = json.loads(resp.content)
        self.assertEqual(obj['output'], post_data['output'])


class APITests(TestCase):
    fixtures = ['eric.json', 'test_data.json']

    def test_make_project(self):
        """
        Test that a superuser can use the API
        """
        post_data = {"name": "awesome-project",
                     "repo": "https://github.com/ericholscher/django-kong.git"}
        resp = self.client.post('/api/v1/project/',
                                data=json.dumps(post_data),
                                content_type='application/json',
                                HTTP_AUTHORIZATION='Basic %s' % super_auth)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp['location'],
                         'http://testserver/api/v1/project/24/')
        resp = self.client.get('/api/v1/project/24/', data={'format': 'json'},
                               HTTP_AUTHORIZATION='Basic %s' % eric_auth)
        self.assertEqual(resp.status_code, 200)
        obj = json.loads(resp.content)
        self.assertEqual(obj['slug'], 'awesome-project')

    def test_invalid_make_project(self):
        """
        Test that the authentication is turned on.
        """
        post_data = {"user": "/api/v1/user/2/",
                     "name": "awesome-project-2",
                     "repo": "https://github.com/ericholscher/django-bob.git"
                     }
        resp = self.client.post(
            '/api/v1/project/', data=json.dumps(post_data),
            content_type='application/json',
            HTTP_AUTHORIZATION='Basic %s' % base64.b64encode('tester:notapass')
        )
        self.assertEqual(resp.status_code, 401)

    def test_make_project_dishonest_user(self):
        """
        Test that you can't create a project for another user
        """
        # represents dishonest data input, authentication happens for user 2
        post_data = {
            "users": ["/api/v1/user/1/"],
            "name": "awesome-project-2",
            "repo": "https://github.com/ericholscher/django-bob.git"
        }
        resp = self.client.post(
            '/api/v1/project/',
            data=json.dumps(post_data),
            content_type='application/json',
            HTTP_AUTHORIZATION='Basic %s' % base64.b64encode('tester:test')
        )
        self.assertEqual(resp.status_code, 401)

    def test_ensure_get_unauth(self):
        """
        Test that GET requests work without authenticating.
        """

        resp = self.client.get("/api/v1/project/", data={"format": "json"})
        self.assertEqual(resp.status_code, 200)

    def test_not_highest(self):
        resp = self.client.get(
            "http://testserver/api/v1/version/read-the-docs/highest/0.2.1/",
            data={"format": "json"}
        )
        self.assertEqual(resp.status_code, 200)
        obj = json.loads(resp.content)
        self.assertEqual(obj['is_highest'], False)

    def test_latest_version_highest(self):
        resp = self.client.get(
            "http://testserver/api/v1/version/read-the-docs/highest/latest/",
            data={"format": "json"}
        )
        self.assertEqual(resp.status_code, 200)
        obj = json.loads(resp.content)
        self.assertEqual(obj['is_highest'], True)

    def test_real_highest(self):
        resp = self.client.get(
            "http://testserver/api/v1/version/read-the-docs/highest/0.2.2/",
            data={"format": "json"}
        )
        self.assertEqual(resp.status_code, 200)
        obj = json.loads(resp.content)
        self.assertEqual(obj['is_highest'], True)
