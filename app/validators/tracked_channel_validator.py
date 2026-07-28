def validate_tracked_channel(data: dict) -> list:
    errors = []
    if not data.get("channel_id", "").strip():
        errors.append("channel_id is required.")
    if not data.get("channel_name", "").strip():
        errors.append("channel_name is required.")
    return errors
