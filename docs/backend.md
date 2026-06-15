# Backend — Setup & API Reference

## Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL via SQLAlchemy 2.0
- **Auth:** JWT (python-jose) + bcrypt password hashing (passlib)
- **Migrations:** Alembic
- **Python:** 3.11

---

## Local Setup

### 1. Create and activate virtualenv

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Important:** `bcrypt` must be pinned to `4.0.1`. Versions 4.1.0+ are incompatible with passlib 1.7.4 and will cause a 500 error on any password hashing call.

### 3. Configure environment

Create `backend/.env`:

```env
DATABASE_URL=postgresql://<user>:<password>@localhost/<dbname>
SECRET_KEY=<your-secret-key>
ACCESS_TOKEN_EXPIRE_MINUTES=30
MAX_FAILED_LOGIN_ATTEMPTS=5
ACCOUNT_LOCKOUT_MINUTES=30
SQL_ECHO=false   # set to true only for local debugging — never in production
```

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Start the server

```bash
uvicorn app.main:app --reload --port 8000
```

Swagger UI available at `http://localhost:8000/docs`.

---

## API Reference

### Auth

#### `POST /auth/register`

Register a new user.

**Request body:**
```json
{
  "email": "user@example.com",
  "phone": "9999999999",
  "password": "yourpassword"
}
```

**Response `201`:**
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

**Validation rules:**
- `email` — must be a valid email address
- `phone` — 10-digit Indian mobile number starting with 6–9 (leading `+91` stripped automatically)
- `password` — min 8 characters, must include uppercase, lowercase, digit, and special character (per RBI Cybersecurity Framework for NBFCs, Dec 2022)

**Errors:**
- `409` — email or phone already registered
- `422` — validation failure (invalid email, phone format, or weak password)

---

#### `POST /auth/login`

Login with email or phone number.

**Request body:**
```json
{
  "identifier": "user@example.com",
  "password": "yourpassword"
}
```

`identifier` accepts either email or phone number.

**Response `200`:**
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

**Errors:**
- `401` — invalid credentials
- `423` — account locked (too many failed attempts); response body includes how many minutes remain

---

### Users

Protected routes require `Authorization: Bearer <token>` header.

#### `GET /users/me`

Returns the profile of the currently authenticated user.

**Response `200`:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "phone": "9999999999",
  "role": "user"
}
```

---

## Security Policies

### Account Lockout (RBI Cybersecurity Framework for NBFCs, Dec 2022)

| Setting | Value | Config key |
|---------|-------|------------|
| Max failed attempts | 5 | `MAX_FAILED_LOGIN_ATTEMPTS` |
| Lockout duration | 30 minutes | `ACCOUNT_LOCKOUT_MINUTES` |

- Counter resets to 0 on successful login
- Lockout expiry is checked on every login attempt — no manual unlock needed
- Both thresholds are configurable via `.env`

---

## Known Issues / Gotchas

| Issue | Fix |
|-------|-----|
| `bcrypt` ≥ 4.1.0 causes 500 on register/login | Pin to `bcrypt==4.0.1` in requirements.txt |
| `SECRET_KEY` defaults to `dev-secret-key` | Always set a strong value in `.env` for non-local environments |
