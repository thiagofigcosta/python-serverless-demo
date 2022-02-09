import unittest
from unittest.mock import MagicMock

from psd_service import xray as xray


class XrayTest(unittest.TestCase):

    def setUp(self, *args, **kwargs):
        pass  # nothing to create

    def tearDown(self, *args, **kwargs):
        pass  # nothing to flush or destroy

    def test_configure_xray(self, *args, **kwargs):
        xray.IS_OFFLINE = False
        xray.configure_xray(MagicMock())

        xray.IS_OFFLINE = True
        xray.configure_xray(MagicMock())


if __name__ == '__main__':
    unittest.main()
