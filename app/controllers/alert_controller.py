"""
Social Pulse API — Alert Controller (stretch)
"""
from flask import jsonify
from flask_jwt_extended import get_current_user
from app.extensions import db
from app.models.alert_model import Alert
from app.utils import utc_now


def get_alerts():
    user = get_current_user()
    alerts = Alert.query.filter_by(user_id=user.id).order_by(Alert.created_at.desc()).all()
    return jsonify({"alerts": [a.to_dict() for a in alerts]}), 200


def mark_alert_read(alert_id: int):
    user = get_current_user()
    alert = Alert.query.get(alert_id)
    if not alert:
        return jsonify({"error": "Alert not found."}), 404
    if alert.user_id != user.id:
        return jsonify({"error": "Forbidden."}), 403

    alert.is_read = True
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Update failed: {str(e)}"}), 500

    return jsonify({"message": "Alert marked as read.", "alert": alert.to_dict()}), 200
