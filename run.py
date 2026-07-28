"""
Social Pulse API — Application Entry Point
"""
from app import create_app
from flask_cors import CORS

app = create_app()
CORS(app, resources={r"/api/*": {"origins": "*"}})

if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", False), port=5000)
