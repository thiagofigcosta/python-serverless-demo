import json
import unittest

from psd_service import utils_http as http_u
from psd_service.exceptions import BadRequestException


class MockedHttpResponse(object):
    def __init__(self, status_code, json_content=None, headers='mocked'):
        self.status_code = status_code
        self.json_content = json_content
        self.headers = headers
        self.text = str(json_content)

    def json(self, parse_float=None):
        if type(self.json_content) is str:
            return json.loads(self.json_content, parse_float=parse_float)
        else:
            return self.json_content


class UtilsHTTPTest(unittest.TestCase):

    def setUp(self, *args, **kwargs):
        pass  # nothing to create

    def tearDown(self, *args, **kwargs):
        pass  # nothing to flush or destroy

    def test_generate_response(self, *args, **kwargs):
        expected_body = 'something'
        expected_headers = {'Access-Control-Allow-Credentials': 'True',
                            'Access-Control-Allow-Origin': '*',
                            'Content-Length': '9',
                            'Content-Type': 'text/html; charset=utf-8'}
        res = http_u.generate_response(200, expected_body)
        self.assertEqual(200, res.status_code)
        self.assertEqual(expected_headers, dict(res.headers))
        self.assertEqual('text/html', res.mimetype)
        self.assertEqual(expected_body.encode(), res.data)

        json_body = {'message': 'this is a test'}
        expected_body = '{"message": "this is a test"}'
        expected_headers['Content-Type'] = 'application/json'
        expected_headers['Content-Length'] = '29'
        res = http_u.generate_response(400, json_body)
        self.assertEqual(400, res.status_code)
        self.assertEqual(expected_headers, dict(res.headers))
        self.assertEqual('application/json', res.mimetype)
        self.assertEqual(expected_body.encode(), res.data)

    def test_generate_error_body(self, *args, **kwargs):
        self.assertRaises(AttributeError, http_u.generate_error_body)

        expected_body = {'error': 'HTTP Version Not Supported!'}
        res = http_u.generate_error_body(status=505, error_msg=None, details=None)
        self.assertEqual(expected_body, res)

        expected_body = {'error': 'Error message'}
        res = http_u.generate_error_body(status=400, error_msg='Error message', details=None)
        self.assertEqual(expected_body, res)

        expected_body = {'details': 'Error details', 'error': 'Unauthorized!'}
        res = http_u.generate_error_body(status=401, error_msg=None, details='Error details')
        self.assertEqual(expected_body, res)

        expected_body = {'details': 'Error details', 'error': 'Error'}
        res = http_u.generate_error_body(status=402, error_msg='Error', details='Error details')
        self.assertEqual(expected_body, res)

        e = Exception('This is an exception')
        expected_body = {'details': 'Error details', 'error': 'This is an exception'}
        res = http_u.generate_error_body(status=403, error_msg=e, details='Error details')
        self.assertEqual(expected_body, res)

        expected_body = {'details': 'This is an exception', 'error': 'Error'}
        res = http_u.generate_error_body(status=404, error_msg='Error', details=e)
        self.assertEqual(expected_body, res)

    def test_generate_error_response(self, *args, **kwargs):
        expected_json = {'error': 'Bad Gateway!'}

        res = http_u.generate_error_response(502, details=None, error_msg=None)
        self.assertEqual(502, res.status_code)
        self.assertEqual('application/json', res.mimetype)
        self.assertEqual(expected_json, res.json)

        expected_json = {'details': 'Error details', 'error': 'Service Unavailable!'}
        res = http_u.generate_error_response(503, details='Error details', error_msg=None)
        self.assertEqual(503, res.status_code)
        self.assertEqual('application/json', res.mimetype)
        self.assertEqual(expected_json, res.json)

        expected_json = {'details': 'Error details', 'error': 'Errors are bad'}
        res = http_u.generate_error_response(503, details='Error details', error_msg=Exception('Errors are bad'))
        self.assertEqual(503, res.status_code)
        self.assertEqual('application/json', res.mimetype)
        self.assertEqual(expected_json, res.json)

    def test_generate_ok_response(self, *args, **kwargs):
        self.assertRaises(AttributeError, http_u.generate_ok_response)
        self.assertRaises(AttributeError, http_u.generate_ok_response, 'not a dict')

        expected_json = {'message': 'a message'}
        res = http_u.generate_ok_response(None, msg='a message')
        self.assertEqual(200, res.status_code)
        self.assertEqual('application/json', res.mimetype)
        self.assertEqual(expected_json, res.json)

        expected_json = {'message': 'success', 'token': 'value'}
        res = http_u.generate_ok_response({'token': 'value'}, msg='success')
        self.assertEqual(200, res.status_code)
        self.assertEqual('application/json', res.mimetype)
        self.assertEqual(expected_json, res.json)

        expected_json = {'message': 'success'}
        res = http_u.generate_ok_response(msg='success')
        self.assertEqual(200, res.status_code)
        self.assertEqual('application/json', res.mimetype)
        self.assertEqual(expected_json, res.json)

    def test_validate_request(self, *args, **kwargs):
        request = {'mandatory key': 0, 'conditional key 1': 1, 'conditional key 2': 2}

        required_fields = ['mandatory key']
        http_u.validate_request(request, required_fields)

        required_fields = ['mandatory key', ['conditional key 1', 'conditional key 2']]
        http_u.validate_request(request, required_fields)

        required_fields = ['mandatory key', ['conditional key 1', 'conditional key 3']]
        http_u.validate_request(request, required_fields)

        required_fields = ['mandatory key', ['conditional key 2', 'conditional key 3']]
        http_u.validate_request(request, required_fields)

        required_fields = ['mandatory key 2', ['conditional key 2', 'conditional key 3']]
        self.assertRaises(BadRequestException, http_u.validate_request, request, required_fields)

        required_fields = ['mandatory key 1', ['conditional key 4', 'conditional key 3']]
        self.assertRaises(BadRequestException, http_u.validate_request, request, required_fields)

    def test_parse_http_response_to_json(self, *args, **kwargs):
        response_body = '{"message":"ok","value":17.123456789}'
        response_body_json = json.loads(response_body)
        value = 17.123456789
        response_from_server = MockedHttpResponse(200, response_body)

        response = http_u.parse_http_response_to_json(response_from_server)
        self.assertEqual(response_body_json, response)

        response = http_u.parse_http_response_to_json(response_from_server)
        self.assertEqual(value, float(response['value']))

        self.assertRaises(Exception, http_u.parse_http_response_to_json, MockedHttpResponse(400))

    def test_get_common_headers_with_authorization(self, *args, **kwargs):
        headers = http_u.get_common_headers_with_authorization()
        self.assertEqual({}, headers)

        bearer_token = 'the B token'
        expected_headers = {'Authorization': 'Bearer the B token'}
        headers = http_u.get_common_headers_with_authorization(bearer_token=bearer_token)
        self.assertEqual(expected_headers, headers)

        basic_auth = 'something in base 64'
        expected_headers = {'Authorization': 'Basic something in base 64'}
        headers = http_u.get_common_headers_with_authorization(basic_auth=basic_auth)
        self.assertEqual(expected_headers, headers)


if __name__ == '__main__':
    unittest.main()
