def validate_youtube_connection(data: dict) -> list:
    errors = []
    if not data.get("channel_id", "").strip():
        errors.append("channel_id is required.")
    return errors
