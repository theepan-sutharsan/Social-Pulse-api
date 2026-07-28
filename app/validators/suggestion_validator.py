from app.constants.suggestion_types import ALL_SUGGESTION_TYPES

def validate_suggestion_request(data: dict) -> list:
    errors = []
    stype = data.get("type")
    if not stype or stype not in ALL_SUGGESTION_TYPES:
        errors.append(f"Invalid suggestion type. Must be one of: {', '.join(ALL_SUGGESTION_TYPES)}")
    account_id = data.get("connected_account_id")
    channel_id = data.get("tracked_channel_id")
    if not account_id and not channel_id:
        errors.append("Either connected_account_id or tracked_channel_id must be specified.")
    if account_id and channel_id:
        errors.append("Specify only one of connected_account_id or tracked_channel_id.")
    return errors
