import os

from aws_xray_sdk.core import patch_all
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

IS_OFFLINE = os.getenv('IS_OFFLINE', 'False').lower() in ('true', '1', 't', 'y', 'yes')


def configure_xray(app):
    if not IS_OFFLINE:
        patch_all()  # patch libs for xray. can also patch individually: aws_xray_sdk.core.patcher.patch(('requests',))

        xray_recorder.configure(service='Python Serverless Demo')  # set required SegmentName

        XRayMiddleware(app, xray_recorder)  # Instrument the Flask application
