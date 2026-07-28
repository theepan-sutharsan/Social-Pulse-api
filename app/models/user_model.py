"""
Social Pulse API — User Model
"""
from app.extensions import db
from app.utils import utc_now
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum("admin", "member"), nullable=False, default="member")
    full_name = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    # Relationships
    connected_accounts = db.relationship(
        "ConnectedAccount", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    suggestions = db.relationship(
        "Suggestion", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    tracked_channels = db.relationship(
        "TrackedChannel", backref="added_by", lazy=True, cascade="all, delete-orphan"
    )
    alerts = db.relationship(
        "Alert", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, plain_password: str):
        self.password = generate_password_hash(plain_password)

    def check_password(self, plain_password: str) -> bool:
        return check_password_hash(self.password, plain_password)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
