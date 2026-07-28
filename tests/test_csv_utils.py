"""
Social Pulse API — CSV Utility Tests
"""
import io
import pytest
from unittest.mock import MagicMock


def test_rows_to_csv_response():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    os.environ.setdefault("DB_NAME", "social_pulse_test")
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
    os.environ.setdefault("FLASK_DEBUG", "0")
    from app import create_app
    from app.config import Config
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        JWT_SECRET_KEY = "test-secret-key"
    app = create_app(TestConfig)
    with app.app_context():
        from app.utils.csv_utils import rows_to_csv_response
        headers = ["name", "value"]
        rows = [["Alice", "100"], ["Bob", "200"]]
        resp = rows_to_csv_response("test.csv", headers, rows)
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type
        content = resp.get_data(as_text=True)
        assert "name,value" in content
        assert "Alice,100" in content


def test_parse_csv_file_valid():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    os.environ.setdefault("DB_NAME", "social_pulse_test")
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
    os.environ.setdefault("FLASK_DEBUG", "0")
    from app import create_app
    from app.config import Config
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        JWT_SECRET_KEY = "test-secret-key"
    app = create_app(TestConfig)
    with app.app_context():
        from app.utils.csv_utils import parse_csv_file
        csv_content = b"channel_id,channel_name,niche\nUC123,Test Channel,Tech\n"
        mock_file = MagicMock()
        mock_file.read.return_value = csv_content
        rows, errors = parse_csv_file(mock_file, ["channel_id", "channel_name", "niche"])
        assert errors == []
        assert len(rows) == 1
        assert rows[0]["channel_id"] == "UC123"


def test_parse_csv_file_missing_columns():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    os.environ.setdefault("DB_NAME", "social_pulse_test")
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
    os.environ.setdefault("FLASK_DEBUG", "0")
    from app import create_app
    from app.config import Config
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        JWT_SECRET_KEY = "test-secret-key"
    app = create_app(TestConfig)
    with app.app_context():
        from app.utils.csv_utils import parse_csv_file
        csv_content = b"channel_id,channel_name\nUC123,Test Channel\n"
        mock_file = MagicMock()
        mock_file.read.return_value = csv_content
        rows, errors = parse_csv_file(mock_file, ["channel_id", "channel_name", "niche"])
        assert len(errors) > 0
        assert "niche" in errors[0]
