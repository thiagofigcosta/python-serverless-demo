import os

import requests
from flask import Flask, request

import psd_service.log as log
import psd_service.transactions as transactions
import psd_service.users as users
import psd_service.utils_http as http_u
import psd_service.utils_uuid as uuid_u
import xray
from psd_service.exceptions import NotFoundException, BadRequestException, CannotSaveException, BadCredentialsException, \
    NotEnoughBalanceException

app = Flask(__name__)
logger = log.setup_and_get_logger()

xray.configure_xray(app)


@app.route("/", methods=('GET', 'POST',))
def index():
    page = f'<h1>Index page! :D</h1>'
    page += f'<br> Env Vars: Test_1 {os.getenv("TEST_1", "`TEST_1` environment var is not set")}'
    page += f'<br> Headers: {dict(request.headers)}'
    page += f'<br> Query args: {dict(request.args)}'
    page += f'<br> Query string: {request.query_string.decode()}'
    page += f'<br> Request body: {request.json}'
    page += f'<br> Request method: {request.method}'
    try:
        res = requests.get("https://aws.amazon.com")
        if res.status_code != 200:
            raise Exception()
        page += f'<br> Aws is up'
    except:
        page += f'<br> Aws is down'

    prod_url = os.getenv('PROD_URL', None)
    if prod_url is not None:
        string_to_convert_to_lower = 'Some STRING to CONVERT remotely'
        string_converted_to_lower = 'Failed'
        try:
            query_string = f'?string={string_to_convert_to_lower.replace(" ", "%20")}'
            res = requests.get(prod_url + '/lower_case' + query_string)
            string_converted_to_lower = http_u.parse_http_response_to_json(res)['string']
        except:
            pass
        page += f'<br> Converted `{string_to_convert_to_lower}` to lower: {string_converted_to_lower}'

        string_to_convert_to_upper = 'The OTHER str to CONVERT remotely'
        string_converted_to_upper = 'Failed'
        try:
            query_string = f'?string={string_to_convert_to_upper.replace(" ", "%20")}'
            res = requests.get(prod_url + '/upper_case' + query_string)
            string_converted_to_upper = http_u.parse_http_response_to_json(res)['string']
        except:
            pass
        page += f'<br> Converted `{string_to_convert_to_upper}` to upper: {string_converted_to_upper}'

    return page


@app.route("/users/<string:user_id>", methods=('GET',))
def get_user(user_id):
    if user_id is None or not uuid_u.check_if_valid_uuid(user_id):
        return http_u.generate_error_response(400, 'Provide a valid user id!')

    logger.debug(f'Received get user for `{user_id}`')

    try:
        user = users.get_user_from_id(user_id)
        return http_u.generate_ok_response(user)
    except NotFoundException as e:
        return http_u.generate_error_response(404, e)
    except Exception as e:
        logger.error(f'{e}')
        return http_u.generate_error_response(500)


@app.route("/users", methods=('POST',))
def create_user():
    request_body = request.json
    required_fields = ['name', 'surname', 'username', 'password']
    try:
        http_u.validate_request(request_body, required_fields)
    except BadRequestException as e:
        return http_u.generate_error_response(400, e)
    except Exception as e:
        logger.error(f'{e}')
        return http_u.generate_error_response(500)

    name = request_body['name']
    surname = request_body['surname']
    username = request_body['username']
    password = request_body['password']

    logger.debug(f'Received get user for `{username}`')

    try:
        user_id = users.create_user(username, password, name, surname)
        return http_u.generate_ok_response({'user_id': user_id}, msg='User created successfully!')
    except CannotSaveException as e:
        return http_u.generate_error_response(409, 'User already exists')
    except Exception as e:
        logger.error(f'{e}')
        return http_u.generate_error_response(500)


@app.route("/user_ids", methods=('GET',))
def get_all_user():
    logger.debug(f'Received get all users')

    try:
        user_ids = users.get_all_user_ids()
        response = {
            'user_ids': user_ids
        }
        return http_u.generate_ok_response(response)
    except Exception as e:
        logger.error(f'{e}')
        return http_u.generate_error_response(500)


@app.route("/auth", methods=('POST',))
def auth():
    request_body = request.json
    required_fields = ['username', 'password']
    try:
        http_u.validate_request(request_body, required_fields)
    except BadRequestException as e:
        return http_u.generate_error_response(400, e)
    except Exception as e:
        logger.error(f'{e}')
        return http_u.generate_error_response(500)

    username = request_body['username']
    password = request_body['password']

    logger.debug(f'Received login `{username}`')

    try:
        token = users.auth_user_and_get_token(username, password)
        return http_u.generate_ok_response({'token': token}, msg='User authenticated successfully!')
    except BadCredentialsException as e:
        return http_u.generate_error_response(403, e)
    except Exception as e:
        logger.error(f'{e}')
        return http_u.generate_error_response(500)


@app.route("/transfer", methods=('POST',))
def make_transfer():
    request_body = request.json
    required_fields = ['src_user_id', 'dst_user_id', 'amount']
    try:
        http_u.validate_request(request_body, required_fields)
    except BadRequestException as e:
        return http_u.generate_error_response(400, e)
    except Exception as e:
        logger.error(f'{e}')
        return http_u.generate_error_response(500)

    src_user_id = request_body['src_user_id']
    dst_user_id = request_body['dst_user_id']
    amount = request_body['amount']

    if not uuid_u.check_if_valid_uuid(dst_user_id):
        return http_u.generate_error_response(400, 'Provide a valid dst user id!')

    if not uuid_u.check_if_valid_uuid(src_user_id):
        return http_u.generate_error_response(400, 'Provide a valid src user id!')

    if src_user_id == dst_user_id:
        return http_u.generate_error_response(400, 'Provide distinct user ids!')

    if type(amount) not in (int, float):
        return http_u.generate_error_response(400, 'Provide a amount!')

    logger.debug(f'Received transaction request of `{amount}` from `{src_user_id}` to `{dst_user_id}`')

    try:
        src_user = users.get_user_from_id(src_user_id)
        dst_user = users.get_user_from_id(dst_user_id)
        transaction = transactions.make_transfer(src_user, dst_user, amount)
        return http_u.generate_ok_response(transaction, msg='Transaction was successful!')
    except NotFoundException as e:
        return http_u.generate_error_response(404, e)
    except NotEnoughBalanceException as e:
        return http_u.generate_error_response(401, e)
    except Exception as e:
        logger.error(f'{type(e)}-{e}')
        return http_u.generate_error_response(500)


@app.route("/users/<string:user_id>/transfers", methods=('GET',))
def get_user_transfers(user_id):
    if user_id is None or not uuid_u.check_if_valid_uuid(user_id):
        return http_u.generate_error_response(400, 'Provide a valid user id!')

    logger.debug(f'Received get user transfers for `{user_id}`')

    try:
        user_transfers = transactions.get_user_transfers(user_id)
        response = {
            'transactions': user_transfers
        }
        return http_u.generate_ok_response(response)
    except NotFoundException as e:
        return http_u.generate_error_response(404, e)
    except Exception as e:
        logger.error(f'{e}')
        return http_u.generate_error_response(500)


@app.route("/lower_case", methods=('GET',))
def to_lower():
    query_params = dict(request.args)
    if 'string' not in query_params:
        return http_u.generate_error_response(400, 'Provide a string!')

    string = query_params['string']

    try:
        response = {
            'string': string.lower()
        }
        return http_u.generate_ok_response(response)
    except NotFoundException as e:
        return http_u.generate_error_response(404, e)
    except Exception as e:
        logger.error(f'{e}')
        return http_u.generate_error_response(500)


@app.route("/upper_case", methods=('GET',))
def to_upper():
    query_params = dict(request.args)
    if 'string' not in query_params:
        return http_u.generate_error_response(400, 'Provide a string!')

    string = query_params['string']

    try:
        response = {
            'string': string.upper()
        }
        return http_u.generate_ok_response(response)
    except NotFoundException as e:
        return http_u.generate_error_response(404, e)
    except Exception as e:
        logger.error(f'{e}')
        return http_u.generate_error_response(500)
