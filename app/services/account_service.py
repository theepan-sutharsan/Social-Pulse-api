from app.models.connected_account_model import ConnectedAccount

class AccountService:
    @staticmethod
    def get_user_accounts(user_id: int):
        return ConnectedAccount.query.filter_by(user_id=user_id).all()
