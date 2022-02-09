import unittest

from psd_service import utils_uuid as uuid_u


class UtilsUUIDTest(unittest.TestCase):

    def setUp(self, *args, **kwargs):
        pass  # nothing to create

    def tearDown(self, *args, **kwargs):
        pass  # nothing to flush or destroy

    def test_check_if_valid_uuid(self, *args, **kwargs):
        response_uuid_v1 = uuid_u.check_if_valid_uuid('480a34b2-537b-11ec-bf63-0242ac130002')
        self.assertTrue(response_uuid_v1)

        response_uuid_v4 = uuid_u.check_if_valid_uuid('4af4de19-255d-447a-bccd-a1dd34ca7ef6')
        self.assertTrue(response_uuid_v4)

        response_non_uuid = uuid_u.check_if_valid_uuid('something else')
        self.assertFalse(response_non_uuid)

    def test_generate_uuid(self, *args, **kwargs):
        uuid_1 = uuid_u.generate_uuid()
        uuid_2 = uuid_u.generate_uuid()
        self.assertEqual(36, len(uuid_1))
        self.assertEqual(36, len(uuid_2))
        self.assertNotEqual(uuid_1, uuid_2)
        self.assertTrue(uuid_u.check_if_valid_uuid(uuid_1))
        self.assertTrue(uuid_u.check_if_valid_uuid(uuid_2))

    def test_generate_uuid_from_str(self, *args, **kwargs):
        base = 'some string'
        expected_uuid = 'b0a99b29-a664-5401-baaa-554c04ef667b'
        uuid = uuid_u.generate_uuid_from_str(base)
        self.assertEqual(36, len(uuid))
        self.assertTrue(uuid_u.check_if_valid_uuid(uuid))
        self.assertEqual(expected_uuid, uuid)


if __name__ == '__main__':
    unittest.main()
