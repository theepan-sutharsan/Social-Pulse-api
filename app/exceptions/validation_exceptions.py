from app.exceptions.base_exception import APIException

class ValidationException(APIException):
    def __init__(self, errors):
        super().__init__("Validation failed", status_code=400, errors=errors)
