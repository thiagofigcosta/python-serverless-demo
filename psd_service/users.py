import hashlib
import logging
import os
from datetime import datetime as dt

from botocore.exceptions import ClientError

import psd_service.utils_dynamo as dynamo_u
import psd_service.utils_uuid as uuid_u
from psd_service.exceptions import NotFoundException, CannotSaveException, BadCredentialsException, ConcurrencyException

DYNAMODB_USERS = os.getenv('DYNAMODB_USERS')
dynamodb = dynamo_u.get_dynamo_client()

DEFAULT_BALANCE = 500.0

logger = logging.getLogger()


def generate_salt():
    random_uuid = uuid_u.generate_uuid()
    salt = hashlib.sha256(random_uuid.encode()).hexdigest()
    return salt


def generate_password_hash(password, salt):
    fixed_salt = 'Remember, all I’m offering is the truth. Nothing more.'  # cannot change
    salty = fixed_salt + password + salt
    return hashlib.sha256(salty.encode()).hexdigest()


def create_user(username, password, name, surname):
    user_id = uuid_u.generate_uuid_from_str(username)  # makes it unique
    salt = generate_salt()
    user = {
        'id': user_id,
        'username': username,
        'passwordHash': generate_password_hash(password, salt),
        'salt': salt,
        'name': name,
        'surname': surname,
        'createdAtUTC': dt.utcnow().isoformat(),
        'verifiedAccount': False,
        'balance': DEFAULT_BALANCE,
        'version': 0
    }
    dynamo_item = dynamo_u.encode_item_for_dynamo(user)
    condition_expression = 'attribute_not_exists(id)'
    try:
        response = dynamodb.put_item(TableName=DYNAMODB_USERS, Item=dynamo_item,
                                     ConditionExpression=condition_expression)
        dynamo_u.assert_valid_dynamo_put_response(response, object_name='User')
        return user_id
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            raise CannotSaveException(e)
        raise e


def get_user_from_id(user_id, get_sensitive_info=False):
    try:
        response = dynamodb.get_item(TableName=DYNAMODB_USERS, Key={'id': {'S': user_id}})
        user = dynamo_u.get_item_from_dynamo_response_or_fail(response, object_name='User')
        if get_sensitive_info:
            return user
        else:
            non_sensitive_keys = ['id', 'username', 'name', 'surname', 'verifiedAccount', 'balance', 'version']
            user_with_filtered_data = {}
            for key in non_sensitive_keys:
                user_with_filtered_data[key] = user[key]
            return user_with_filtered_data
    except ClientError as e:
        logger.error(e.response['Error']['Message'])
        raise NotFoundException(f'User with id {user_id} does not exists')


def get_user_from_username(username):
    response = dynamodb.scan(
        TableName=DYNAMODB_USERS,
        ScanFilter={
            'username': {
                'AttributeValueList': [{'S': username}],
                'ComparisonOperator': 'EQ'
            }
        }
    )
    try:
        items = dynamo_u.get_items_from_dynamo_response_or_fail(response, object_name='User')
        return items[0]
    except:
        raise NotFoundException(f'User with username {username} does not exists')


def get_all_user_ids():
    response = dynamodb.scan(TableName=DYNAMODB_USERS)
    users = []
    try:
        users = dynamo_u.get_items_from_dynamo_response_or_fail(response, object_name='Users')
    except:
        pass  # Explicitly ignoring
    users = [user['id'] for user in users]  # removing other fields
    return users


def auth_user_and_get_token(username, password):
    user = get_user_from_username(username)
    computed_hash = generate_password_hash(password, user['salt'])

    if not computed_hash == user['passwordHash']:
        raise BadCredentialsException('username and/or password does not match')
    return 'a_super_safe_token'


def store_user(user, version):
    dynamo_item = dynamo_u.encode_item_for_dynamo(user)
    try:
        dynamodb.put_item(
            TableName=DYNAMODB_USERS,
            Item=dynamo_item,
            ExpressionAttributeValues={
                ':version': {'N': str(version)}
            },
            ConditionExpression='version = :version'
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == 'ConditionalCheckFailedException':
            raise ConcurrencyException("User has been already modified")
        else:
            raise e
