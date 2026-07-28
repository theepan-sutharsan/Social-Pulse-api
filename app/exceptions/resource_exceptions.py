from app.exceptions.base_exception import APIException

class ResourceNotFoundException(APIException):
    def __init__(self, resource_name="Resource"):
        super().__init__(f"{resource_name} not found.", status_code=404)

class DuplicateResourceException(APIException):
    def __init__(self, message="Resource already exists."):
        super().__init__(message, status_code=400)
