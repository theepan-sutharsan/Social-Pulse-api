from app.exceptions.base_exception import APIException

class InvalidCredentialsException(APIException):
    def __init__(self, message="Invalid email or password."):
        super().__init__(message, status_code=401)

class AccountDeactivatedException(APIException):
    def __init__(self, message="Account is deactivated."):
        super().__init__(message, status_code=403)
