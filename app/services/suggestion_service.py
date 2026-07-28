from app.models.suggestion_model import Suggestion

class SuggestionService:
    @staticmethod
    def get_user_suggestions(user_id: int):
        return Suggestion.query.filter_by(user_id=user_id).order_by(Suggestion.created_at.desc()).all()
