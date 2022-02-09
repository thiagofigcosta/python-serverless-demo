import unittest
from decimal import Decimal
from unittest import mock

from botocore.exceptions import ClientError

from psd_service.exceptions import CannotSaveException, NotFoundException

GLOBAL_MOCKED_KWARGS = {}


# This function is a lambda wrapper that serves to call a mock_function with joined arguments from the original
# function to be mocked with custom arguments
def call(_callable, **_mocked_custom_kwargs):
    return lambda *args, **kwargs: _callable(*args, **kwargs, **_mocked_custom_kwargs, **GLOBAL_MOCKED_KWARGS)


class MockedBoto3(object):
    # A class to store the mocked functions in an organized way

    class Dynamodb(object):

        @staticmethod
        def Table(*args, **kwargs):
            return MockedBoto3.DynamoTable

        @staticmethod
        def put_item(*args, **kwargs):
            return MockedBoto3.DynamoTable.put_item(*args, **kwargs)

    class DynamoTable(object):

        @staticmethod
        def put_item(*args, **kwargs):
            kwargs.update(GLOBAL_MOCKED_KWARGS)
            mocked_scenario = kwargs.pop('mocked_scenario', 'success')
            if mocked_scenario == 'success':
                return {'ResponseMetadata': {'HTTPStatusCode': 200}}
            elif mocked_scenario == 'duplicated':
                response = {'Error': {'Code': 'ConditionalCheckFailedException'}}
                raise ClientError(response, 'put')
            else:
                return {'ResponseMetadata': {'HTTPStatusCode': 400}}

    @staticmethod
    def resource(*args, **kwargs):
        resource_name = args[0]
        if resource_name == 'dynamodb':
            return MockedBoto3.Dynamodb

    @staticmethod
    def client(*args, **kwargs):
        resource_name = args[0]
        if resource_name == 'dynamodb':
            return MockedBoto3.Dynamodb


from psd_service import utils_dynamo as dynamo_u


class UtilsDynamoTest(unittest.TestCase):

    def setUp(self, *args, **kwargs):
        pass  # nothing to create

    def tearDown(self, *args, **kwargs):
        pass  # nothing to flush or destroy

    @mock.patch('boto3.resource', side_effect=call(MockedBoto3.resource))
    @mock.patch('boto3.client', side_effect=call(MockedBoto3.client))
    def test_get_dynamo_client(self, *args, **kwargs):
        dynamo_cls = dynamo_u.get_dynamo_client()
        dynamo_instance = dynamo_cls()
        self.assertIsInstance(dynamo_instance, MockedBoto3.Dynamodb)

    def test_encode_item_for_dynamo(self, *args, **kwargs):
        item = {
            'field 0': 'a string',
            'field 1': 8,
            'field 2': 3.1415,
            'field 3': False
        }
        expected_dynamo_item = {'field 0': {'S': 'a string'},
                                'field 1': {'N': '8'},
                                'field 2': {'N': '3.1415'},
                                'field 3': {'BOOL': False}}
        dynamo_item = dynamo_u.encode_item_for_dynamo(item)
        self.assertEqual(expected_dynamo_item, dynamo_item)

    def test_decode_item_from_dynamo(self, *args, **kwargs):
        dynamo_item = {'field 0': {'S': 'a string'},
                       'field 1': {'N': '8'},
                       'field 2': {'N': '3.1415'},
                       'field 3': {'BOOL': False}}
        expected_item = {
            'field 0': 'a string',
            'field 1': 8,
            'field 2': 3.1415,
            'field 3': False
        }

        item = dynamo_u.decode_item_from_dynamo(dynamo_item)
        self.assertEqual(expected_item, item)

    def test_assert_valid_dynamo_put_response(self, *args, **kwargs):
        good_response = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        bad_response_0 = {'ResponseMetadata': {'HTTPStatusCode': 400}}
        bad_response_1 = {'ResponseMetadata': {}}

        dynamo_u.assert_valid_dynamo_put_response(good_response)  # do not throws
        self.assertRaises(CannotSaveException, dynamo_u.assert_valid_dynamo_put_response, bad_response_0)
        self.assertRaises(CannotSaveException, dynamo_u.assert_valid_dynamo_put_response, bad_response_1)

    def test_get_items_from_dynamo_response_or_fail_when_fail(self, *args, **kwargs):
        response_empty = {'Count': 0, 'Items': []}
        response_invalid = {'Something else': 0}
        self.assertRaises(NotFoundException, dynamo_u.get_items_from_dynamo_response_or_fail, response_empty)
        self.assertRaises(NotFoundException, dynamo_u.get_items_from_dynamo_response_or_fail, response_invalid)

    def test_get_items_from_dynamo_response_or_fail_when_success(self, *args, **kwargs):
        expected_object_1 = {'Field': 'Area', 'Value': 9}
        response = {'Count': 1, 'Items': [dynamo_u.encode_item_for_dynamo(expected_object_1)]}
        item_1 = dynamo_u.get_items_from_dynamo_response_or_fail(response)
        self.assertEqual(1, len(item_1))
        self.assertEqual(expected_object_1, item_1[0])

        expected_object_2_float = {'Field': 'Area', 'Value': 9.23, 'extra': [9, 3.14]}
        expected_object_2_decimal = {'Field': 'Area', 'Value': Decimal(9.23), 'extra': [Decimal(9), Decimal(3.14)]}
        response = {'Count': 2, 'Items': [dynamo_u.encode_item_for_dynamo(expected_object_1),
                                          dynamo_u.encode_item_for_dynamo(expected_object_2_decimal)]}

        item_3 = dynamo_u.get_items_from_dynamo_response_or_fail(response)
        self.assertEqual(2, len(item_3))
        self.assertEqual(expected_object_1, item_3[0])
        self.assertTrue(expected_object_2_float, item_3[1])
        self.assertTrue(type(item_3[1]['Value']) is float)

    def test_get_item_from_dynamo_response_or_fail_when_fail(self, *args, **kwargs):
        response_empty = {}
        response_invalid = {'Something else': 0}
        self.assertRaises(NotFoundException, dynamo_u.get_item_from_dynamo_response_or_fail, response_empty)
        self.assertRaises(NotFoundException, dynamo_u.get_item_from_dynamo_response_or_fail, response_invalid)

    def test_get_item_from_dynamo_response_or_fail_when_success(self, *args, **kwargs):
        expected_object_1 = {'Field': 'Area', 'Value': 9}
        response = {'Item': dynamo_u.encode_item_for_dynamo(expected_object_1)}
        item_1 = dynamo_u.get_item_from_dynamo_response_or_fail(response)
        self.assertEqual(expected_object_1, item_1)

        expected_object_2_float = {'Field': 'Area', 'Value': 9.23, 'extra': [9, 3.14]}
        expected_object_2_decimal = {'Field': 'Area', 'Value': Decimal(9.23), 'extra': [Decimal(9), Decimal(3.14)]}
        response = {'Item': dynamo_u.encode_item_for_dynamo(expected_object_2_decimal)}

        item_3 = dynamo_u.get_item_from_dynamo_response_or_fail(response)
        self.assertTrue(expected_object_2_float, item_3)
        self.assertTrue(type(item_3['Value']) is float)


if __name__ == '__main__':
    unittest.main()
