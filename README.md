# Episodic — Backend API

A production-ready FastAPI + PostgreSQL backend for **Episodic**, a youth-led chronic illness and disability literary and advocacy magazine.

---

## Project Overview

Episodic is a digital magazine where young people with chronic illnesses and disabilities can submit essays, poetry, op-eds, interviews, and visual art. This backend handles:

- User authentication (JWT)
- Contributor application and profile management
- Submission workflow (draft → submitted → editorial review → published)
- Article publication with anonymous byline support
- Issue management
- Resource directory
- Content reporting
- Newsletter subscriptions

Privacy is a first-class concern. Contributor health information (`condition_identity`) is never exposed in public API responses. Anonymous bylines are enforced at the schema level.

---

## Setup Instructions

### Local Setup

**Prerequisites:** Python 3.12+, PostgreSQL 14+

```bash
# 1. Clone and enter the directory
cd /path/to/Episodic

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your database credentials and a strong SECRET_KEY

# 5. Create the database
createdb episodic_db

# 6. Run migrations
alembic upgrade head

# 7. (Optional) Seed sample data
python seed_data.py

# 8. Start the server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

### Docker Setup

```bash
# Start all services (PostgreSQL + API)
docker-compose up --build

# Run migrations inside the container
docker-compose exec app alembic upgrade head

# Seed data
docker-compose exec app python seed_data.py
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | Async PostgreSQL URL (`postgresql+asyncpg://...`) |
| `SECRET_KEY` | Yes | — | Long random string for JWT signing. Use `openssl rand -hex 32` |
| `ALGORITHM` | No | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Refresh token lifetime |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000` | Comma-separated list of allowed CORS origins |
| `ENVIRONMENT` | No | `development` | `development` or `production` |

---

## API Endpoints

All endpoints are prefixed with `/api/v1`.

### Authentication

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/signup` | None | Create account, returns tokens |
| POST | `/auth/login` | None | Login, returns tokens |
| POST | `/auth/logout` | Bearer | Invalidate refresh token |
| POST | `/auth/refresh` | None | Exchange refresh token for new pair |
| GET | `/auth/me` | Bearer | Get current user profile |

### Users (Admin only)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/users` | Admin | List all users |
| GET | `/users/{id}` | Admin | Get user by ID |
| PATCH | `/users/{id}` | Admin | Update role or active status |
| DELETE | `/users/{id}` | Admin | Soft-delete user |

### Contributors

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/contributors` | None | List approved contributors (public profile only) |
| GET | `/contributors/{id}` | None | Get contributor public profile |
| POST | `/contributors/apply` | Bearer | Apply to become a contributor |
| GET | `/contributors/me` | Bearer | Get own full profile (includes private fields) |
| PATCH | `/contributors/me` | Bearer | Update own profile |

### Submissions

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/submissions` | Contributor+ | Create a submission (starts as draft) |
| GET | `/submissions/mine` | Bearer | List own submissions |
| GET | `/submissions/{id}` | Bearer | Get own submission detail |
| PATCH | `/submissions/{id}` | Bearer | Update draft submission |
| POST | `/submissions/{id}/submit` | Bearer | Submit draft for review |
| DELETE | `/submissions/{id}` | Bearer | Delete draft submission |

### Editorial (Editor+ only)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/editorial/submissions` | Editor+ | List all submissions (filterable) |
| GET | `/editorial/submissions/{id}` | Editor+ | Full submission detail |
| PATCH | `/editorial/submissions/{id}/status` | Editor+ | Update submission status |
| POST | `/editorial/submissions/{id}/assign` | Editor+ | Assign editor to submission |
| POST | `/editorial/submissions/{id}/notes` | Editor+ | Add editorial note |
| GET | `/editorial/submissions/{id}/notes` | Editor+ | List editorial notes |
| POST | `/editorial/submissions/{id}/publish` | Editor+ | Publish accepted submission as Article |

### Articles

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/articles` | None | List published articles (filterable) |
| GET | `/articles/featured` | None | List featured articles |
| GET | `/articles/{slug}` | None | Get article by slug |
| POST | `/articles` | Editor+ | Manually create article |
| PATCH | `/articles/{id}` | Editor+ | Update article |
| PATCH | `/articles/{id}/feature` | Editor+ | Toggle featured flag |

### Issues

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/issues` | None | List published issues |
| GET | `/issues/{slug}` | None | Get issue detail |
| POST | `/issues` | Editor+ | Create issue |
| PATCH | `/issues/{id}` | Editor+ | Update issue |
| PATCH | `/issues/{id}/status` | Editor+ | Update issue status |

### Resources

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/resources` | None | List non-hidden resources (filterable) |
| GET | `/resources/{id}` | None | Get resource |
| POST | `/resources` | Editor+ | Create resource |
| PATCH | `/resources/{id}` | Editor+ | Update resource |
| PATCH | `/resources/{id}/hide` | Editor+ | Hide/unhide resource |

### Reports

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/reports` | Bearer | Submit a content report |
| GET | `/reports` | Admin | List all reports |
| PATCH | `/reports/{id}` | Admin | Update report status/notes |

### Newsletter

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/newsletter/subscribe` | None | Subscribe email |
| POST | `/newsletter/unsubscribe` | None | Unsubscribe email |
| GET | `/newsletter/subscribers` | Admin | List all subscribers |

---

## Role Permissions

| Action | Reader | Contributor | Editor | Admin |
|---|:---:|:---:|:---:|:---:|
| View public content | ✓ | ✓ | ✓ | ✓ |
| Create submissions | — | ✓ | ✓ | ✓ |
| View own submissions | — | ✓ | ✓ | ✓ |
| View all submissions | — | — | ✓ | ✓ |
| Change submission status | — | — | ✓ | ✓ |
| Add editorial notes | — | — | ✓ | ✓ |
| Create/edit articles | — | — | ✓ | ✓ |
| Create/edit issues | — | — | ✓ | ✓ |
| Manage resources | — | — | ✓ | ✓ |
| Manage users | — | — | — | ✓ |
| View reports | — | — | — | ✓ |
| View subscriber list | — | — | — | ✓ |

---

## Example Curl Requests

### Signup
```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "mypassword123", "display_name": "Your Name"}'
```

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "mypassword123"}'
# Returns: {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}
```

### Create a Submission
```bash
TOKEN="your-access-token-here"
curl -X POST http://localhost:8000/api/v1/submissions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Living with Uncertainty",
    "category": "essay",
    "body_text": "<p>When I was diagnosed, everything changed overnight.</p>",
    "content_warnings": ["chronic illness", "medical trauma"],
    "anonymous_byline": false
  }'
```

### Submit a Draft
```bash
SUBMISSION_ID="your-submission-uuid"
curl -X POST http://localhost:8000/api/v1/submissions/$SUBMISSION_ID/submit \
  -H "Authorization: Bearer $TOKEN"
```

### Publish an Accepted Submission (Editor)
```bash
EDITOR_TOKEN="editor-access-token"
SUBMISSION_ID="accepted-submission-uuid"
curl -X POST http://localhost:8000/api/v1/editorial/submissions/$SUBMISSION_ID/publish \
  -H "Authorization: Bearer $EDITOR_TOKEN"
```

### List Published Articles (Public)
```bash
curl "http://localhost:8000/api/v1/articles?category=essay&featured=true"
```

### Get Article by Slug (Public)
```bash
curl "http://localhost:8000/api/v1/articles/the-exhaustion-no-one-sees"
```

---

## Privacy Design Notes

### Contributor Health Information
`ContributorProfile.condition_identity` is a field where contributors may record their chronic illness or disability identity. This field is:

- **Never** included in `ContributorPublic` schema (used in all public endpoints)
- **Never** included in editor-facing endpoints
- **Only** returned via `GET /contributors/me` using the `ContributorPrivate` schema
- Stored and treated as sensitive personal health information

The `condition_identity_public` flag indicates that the contributor has opted in to sharing this information. Even when `True`, the raw value is not serialized in public responses — only a boolean signal is sent so the frontend can display an appropriate badge.

### Anonymous Bylines
When `anonymous_byline=True` on an Article:
- The `byline` field in API responses shows `"Anonymous"` or the contributor's chosen `byline_name`
- The contributor's real `display_name` is **never** included in the response
- This is enforced in the `_build_article_public()` and `_build_article_internal()` functions, not just in schema definitions
- The `effective_byline` property on the `Article` model also enforces this

### Editorial Notes
Editorial notes (`EditorialNote`) are private communications between editors. They are:
- Never exposed to contributors
- Only accessible via `GET /editorial/submissions/{id}/notes` (editor+ only)

---

## Frontend Integration

### CORS
The backend accepts requests from origins listed in `ALLOWED_ORIGINS`. Update this in your `.env` to match your frontend URL.

### Token Storage
Tokens are returned in the response body as JSON. The frontend should:
- Store the `access_token` in memory (not localStorage — XSS risk)
- Store the `refresh_token` in a secure httpOnly cookie, or in memory with careful handling
- Include `Authorization: Bearer {access_token}` header on all authenticated requests
- Call `POST /auth/refresh` when receiving a 401 to get new tokens

### Public vs. Authenticated Endpoints
- Articles, issues, resources: fully public (no auth needed)
- Submissions, contributor profile `/me`: requires `contributor` role
- Editorial endpoints: requires `editor` or `admin` role
- User management, reports, subscriber list: requires `admin` role

### Pagination
List endpoints accept `skip` (offset) and `limit` query parameters. All return `{ items: [...], total: N }`.

---

## Database Migration Commands

```bash
# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Generate a new migration after model changes
alembic revision --autogenerate -m "describe your change"

# Show current migration version
alembic current

# Show migration history
alembic history
```

---

## Running Tests

```bash
# Install test dependencies (already in requirements.txt)
pip install -r requirements.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_auth.py -v

# Run with coverage
pytest --cov=app tests/
```

Tests use an in-memory SQLite database and do not require a running PostgreSQL instance.

---

## Production Checklist

- [ ] Change `SECRET_KEY` to a strong random value (`openssl rand -hex 32`)
- [ ] Set `ENVIRONMENT=production`
- [ ] Replace in-memory JWT blocklist with Redis (`app/core/security.py`)
- [ ] Integrate a real email provider in `app/services/email.py`
- [ ] Set `ALLOWED_ORIGINS` to your actual frontend domain
- [ ] Run behind a reverse proxy (nginx) with TLS
- [ ] Set up database connection pooling (PgBouncer)
- [ ] Configure log aggregation (e.g., send structured logs to Datadog / Papertrail)
- [ ] Review and tighten CORS settings
- [ ] Enable database backups
