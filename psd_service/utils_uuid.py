import hashlib
import uuid


def check_if_valid_uuid(query_uuid):
    if type(query_uuid) is not str:
        return False
    supported_versions = (4, 5, 3, 1)
    for version in supported_versions:
        try:
            result = str(uuid.UUID(query_uuid, version=version)) == query_uuid
            if result:
                return result
        except ValueError:
            pass
    return False


def generate_uuid():
    return str(uuid.uuid4())


def generate_uuid_from_str(string):
    salt = 'user id'  # do not change, this is equivalent to namespace in uuid5
    hash_digit = hashlib.sha1((salt + string).encode()).digest()
    uuid_obj = uuid.UUID(bytes=hash_digit[:16], version=5)
    return str(uuid_obj)
