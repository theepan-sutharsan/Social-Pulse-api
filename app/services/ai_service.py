from app.integrations import ai_client

class AIService:
    @staticmethod
    def generate(suggestion_type, videos, account_name="", provider=None):
        return ai_client.generate_suggestion(suggestion_type, videos, account_name, provider=provider)
