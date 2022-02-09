import json
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.types import TypeSerializer, TypeDeserializer

from psd_service.exceptions import CannotSaveException, NotFoundException

IS_OFFLINE = os.getenv('IS_OFFLINE', 'False').lower() in ('true', '1', 't', 'y', 'yes')
OFFLINE_PORT = 8032


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)


def get_dynamo_client():
    if IS_OFFLINE:
        client = boto3.client(
            'dynamodb',
            region_name='localhost',
            endpoint_url=f'http://localhost:{OFFLINE_PORT}'
        )
    else:
        client = boto3.client('dynamodb')
    return client


def encode_item_for_dynamo(item):
    parsed_item = json.loads(json.dumps(item, cls=DecimalEncoder),
                             parse_float=Decimal)  # boto3 does not allow float types :/
    serializer = TypeSerializer()
    dynamo_item = {k: serializer.serialize(v) for k, v in parsed_item.items()}
    return dynamo_item


def decode_item_from_dynamo(dynamo_item):
    deserializer = TypeDeserializer()
    parsed_item = {k: deserializer.deserialize(v) for k, v in dynamo_item.items()}
    item = json.loads(json.dumps(parsed_item, cls=DecimalEncoder))  # boto3 does not allow float types :/
    return item


def assert_valid_dynamo_put_response(response, allowed_responses=(200,), object_name=''):
    if type(allowed_responses) not in (list, tuple):
        allowed_responses = [allowed_responses]
    if 'ResponseMetadata' not in response or 'HTTPStatusCode' not in response["ResponseMetadata"] or \
            response["ResponseMetadata"]["HTTPStatusCode"] not in allowed_responses:
        if object_name is None or object_name == '':
            error_msg = 'Could not insert on dynamodb'
        else:
            error_msg = 'Could not insert {} on dynamodb'.format(object_name)
        raise CannotSaveException(error_msg)


def get_items_from_dynamo_response_or_fail(response, object_name=''):
    if ('Count' in response and response['Count'] > 0) and ('Items' in response and len(response['Items']) > 0):
        items = response['Items']
        items = [decode_item_from_dynamo(item) for item in items]
        return items
    if object_name is None or object_name == '':
        error_msg = 'Not found'
    else:
        error_msg = '{} not found'.format(object_name)
    raise NotFoundException(error_msg)


def get_item_from_dynamo_response_or_fail(response, object_name=''):
    if 'Item' in response:
        item = response['Item']
        item = decode_item_from_dynamo(item)
        return item
    if object_name is None or object_name == '':
        error_msg = 'Not found'
    else:
        error_msg = '{} not found'.format(object_name)
    raise NotFoundException(error_msg)
