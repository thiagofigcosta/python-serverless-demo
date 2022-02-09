import os
import time
from datetime import datetime as dt

from botocore.exceptions import ClientError

import psd_service.users as users
import psd_service.utils_dynamo as dynamo_u
import psd_service.utils_uuid as uuid_u
from psd_service.exceptions import NotEnoughBalanceException, NotFoundException

DYNAMODB_TRANSACTIONS = os.getenv('DYNAMODB_TRANSACTIONS')
dynamodb = dynamo_u.get_dynamo_client()


def register_transaction(src_user_id, dst_user_id, amount):
    transfer_id = uuid_u.generate_uuid()
    transfer = {
        'id': transfer_id,
        'srcUserId': src_user_id,
        'dstUserId': dst_user_id,
        'amount': amount,
        'occurredAtUTC': dt.utcnow().isoformat()
    }
    dynamo_item = dynamo_u.encode_item_for_dynamo(transfer)
    condition_expression = 'attribute_not_exists(id)'
    try:
        response = dynamodb.put_item(TableName=DYNAMODB_TRANSACTIONS, Item=dynamo_item,
                                     ConditionExpression=condition_expression)
        dynamo_u.assert_valid_dynamo_put_response(response, object_name='User')
        return transfer
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            time.sleep(1)
            return register_transaction(src_user_id, dst_user_id, amount)
        else:
            raise e


def make_transfer(src_user, dst_user, amount):
    src_user_version = src_user['version']
    if src_user['balance'] - amount >= 0:
        src_user['balance'] -= amount
    else:
        raise NotEnoughBalanceException(f"User {src_user['id']} does not have enough balance")

    src_user['version'] += 1
    users.store_user(src_user, src_user_version)

    while True:
        try:
            dst_user_version = dst_user['version']
            dst_user['balance'] += amount
            dst_user['version'] += 1
            users.store_user(dst_user, dst_user_version)
            break
        except:
            # The correct thing to do would be to publish this into a queue
            try:
                time.sleep(1)
            except:
                pass
            dst_user = users.get_user_from_id(dst_user['id'])

    return register_transaction(src_user['id'], dst_user['id'], amount)


def get_user_transfers(user_id):
    items = []
    response = dynamodb.scan(
        TableName=DYNAMODB_TRANSACTIONS,
        ScanFilter={
            'srcUserId': {
                'AttributeValueList': [{'S': user_id}],
                'ComparisonOperator': 'EQ'
            }
        }
    )
    try:
        items += dynamo_u.get_items_from_dynamo_response_or_fail(response, object_name='Transactions')
    except NotFoundException:
        pass  # Explicitly ignoring

    response = dynamodb.scan(
        TableName=DYNAMODB_TRANSACTIONS,
        ScanFilter={
            'dstUserId': {
                'AttributeValueList': [{'S': user_id}],
                'ComparisonOperator': 'EQ'
            }
        }
    )
    try:
        items += dynamo_u.get_items_from_dynamo_response_or_fail(response, object_name='Transactions')
    except NotFoundException:
        pass  # Explicitly ignoring

    return items
