from app.models.user_model import User
from app.extensions import db

class AuthService:
    @staticmethod
    def get_user_by_id(user_id: int):
        return User.query.get(user_id)

    @staticmethod
    def get_user_by_email(email: str):
        return User.query.filter_by(email=email.strip().lower()).first()
