class NotFoundException(Exception):
    pass


class BadRequestException(Exception):
    pass


class CannotSaveException(Exception):
    pass


class BadCredentialsException(Exception):
    pass


class NotEnoughBalanceException(Exception):
    pass


class ConcurrencyException(Exception):
    pass
