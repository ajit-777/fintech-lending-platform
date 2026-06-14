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

**Errors:**
- `409` — email or phone already registered

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

## Known Issues / Gotchas

| Issue | Fix |
|-------|-----|
| `bcrypt` ≥ 4.1.0 causes 500 on register/login | Pin to `bcrypt==4.0.1` in requirements.txt |
| `SECRET_KEY` defaults to `dev-secret-key` | Always set a strong value in `.env` for non-local environments |
