import json
from http.client import responses

from flask import Response

from psd_service.exceptions import BadRequestException


def generate_response(code, body):
    if type(body) is dict:
        response = json.dumps(body)
        mimetype = 'application/json'
    elif type(body) is str:
        response = body
        mimetype = 'text/html'
    else:
        raise ValueError('Invalid http response type')
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Credentials": True,
    }
    response = Response(response=response, status=code, mimetype=mimetype, headers=headers)
    return response


def generate_error_body(status=None, error_msg=None, details=None):
    if status is None and error_msg is None:
        raise AttributeError('Provide either status or error_msg')

    if isinstance(error_msg, Exception):
        error_msg = str(error_msg)
    if isinstance(details, Exception):
        details = str(details)

    error = {
        'error': f'{responses[status]}!' if error_msg is None else error_msg,
    }
    if details is not None:
        error['details'] = details
    return error


def generate_error_response(code, details=None, error_msg=None):
    body = generate_error_body(status=code, details=details, error_msg=error_msg)
    response = generate_response(code, body)
    return response


def generate_ok_response(json_body=None, msg=None):
    if json_body is None and msg is None:
        raise AttributeError('Provide either json_body or msg')
    if json_body is not None and type(json_body) is not dict:
        raise AttributeError('Provide a json_body of type dict')

    if json_body is None:
        json_body = {}
    if msg is not None:
        json_body['message'] = msg
    return generate_response(200, json_body)


def validate_request(request_data, required_fields):
    for req_field in required_fields:
        if type(req_field) is str:
            if req_field not in request_data:
                raise BadRequestException(
                    f'Expected key: `{req_field}` but request data had `{list(request_data.keys())}`')
        elif type(req_field) is list:  # OR gate
            has_at_least_one = False
            for req_conditional_field in req_field:
                if req_conditional_field in request_data:
                    has_at_least_one = True
                    break
            if not has_at_least_one:
                raise BadRequestException(
                    f'Expected one of the following keys: `{req_field}` but request data had `{list(request_data.keys())}`')


def get_common_headers_with_authorization(bearer_token=None, basic_auth=None):
    if bearer_token is not None:
        headers = {'Authorization': f'Bearer {bearer_token}'}
    elif basic_auth is not None:
        headers = {'Authorization': f'Basic {basic_auth}'}
    else:
        headers = {}
    return headers


def parse_http_response_to_json(response, allowed_responses=(200,), server_name='Server'):
    if type(allowed_responses) not in (list, tuple):
        allowed_responses = [allowed_responses]

    if response.status_code in allowed_responses:
        return response.json()
    else:
        error_msg = ''
        try:
            json_response = response.json()
            for message_carrier in ('error', 'message', 'error:'):
                try:
                    error_msg = json_response[message_carrier]
                    break
                except:
                    pass  # explicitly ignoring
        except:
            pass  # explicitly ignoring
        if error_msg != '':
            error_msg = f', {error_msg}'
        error_str = f'{server_name} returned: {response.status_code} ({responses[response.status_code]}){error_msg}'
        raise Exception(error_str)
