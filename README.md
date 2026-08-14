# Social Pulse API

Social Pulse REST API — Flask 3.x + MySQL + JWT + Claude AI

## Setup

### 1. Prerequisites
- Python 3.12+
- MySQL 8.x running locally

### 2. Clone & Create Virtual Environment
```bash
cd api
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env and fill in your credentials:
# DB_USER, DB_PASSWORD, DB_HOST, DB_NAME
# JWT_SECRET_KEY
# YOUTUBE_API_KEY (optional — stubs work without it)
# ANTHROPIC_API_KEY (optional — stubs work without it)
```

### 4. Create MySQL Database
```sql
CREATE DATABASE social_pulse CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. Start the API
```bash
python run.py
# API runs at http://127.0.0.1:5000
```

For Railway, use the included `Procfile` (or set the service start command to
`gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 900 run:app`).
Set `CORS_ORIGINS` to the HTTPS Vercel origin and configure the Vercel build
variable `NEXT_PUBLIC_API_URL` with the HTTPS Railway public URL.

Audio transcription defaults to the `small` Faster-Whisper model for better
Tamil accuracy. Set `WHISPER_MODEL=medium` when the deployment has enough CPU
and memory for quality-first transcription.

### 6. Seed Demo Data
```bash
python seed.py
```

Demo credentials:
- **Admin:** `admin@socialpulse.test` / `Admin123`
- **Member:** `creator@socialpulse.test` / `Member123`

### 7. Run Tests
```bash
pytest tests/ -v
```

## API Endpoints

| Method | Route | Access |
|--------|-------|--------|
| POST | `/api/auth/register` | Public |
| POST | `/api/auth/login` | Public |
| POST | `/api/auth/forgot-password` | Public |
| POST | `/api/auth/reset-password` | Public |
| GET | `/api/auth/profile` | Authenticated |
| PUT | `/api/auth/profile` | Authenticated |
| GET | `/api/accounts` | Member/Admin |
| POST | `/api/accounts/youtube` | Member/Admin |
| POST | `/api/accounts/:id/sync` | Member/Admin |
| GET | `/api/tracked-channels` | Member/Admin |
| POST | `/api/tracked-channels` | Admin |
| POST | `/api/tracked-channels/import` | Admin |
| GET | `/api/tracked-channels/export` | Admin |
| GET | `/api/videos` | Member/Admin |
| GET | `/api/videos/:id/metrics` | Member/Admin |
| GET | `/api/videos/export?format=csv\|pdf` | Member/Admin |
| POST | `/api/suggestions` | Member/Admin |
| GET | `/api/suggestions/:id` | Member/Admin |
| GET | `/api/suggestions/:id/pdf` | Member/Admin |
| GET | `/api/me/dashboard` | Member/Admin |
| GET | `/api/me/dashboard/pdf` | Member/Admin |

## Key Features
- **Signature:** `suggestion_sources` many-to-many (videos ↔ suggestions)
- **AI:** Claude API (stubs to mock data without API key)
- **CSV import/export:** tracked channels (admin), videos, suggestions
- **PDF export:** suggestion reports, video reports, dashboard summary
- **OAuth:** Instagram/Facebook (Meta Graph API) + TikTok Login Kit
- **YouTube:** Public channel lookup (no OAuth)
