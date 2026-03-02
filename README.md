# Secure Banking API

A production-ready REST API for a secure banking system built with **FastAPI**, **SQLAlchemy (async)**, and **PostgreSQL**. Designed with strict financial-data guarantees: atomic transfers, immutable audit ledger, and database-level balance constraints.

---

## Features

| Feature | Detail |
|---|---|
| **Atomic transfers** | Debit + credit + ledger entries in one SQL transaction — all or nothing |
| **Deadlock prevention** | Rows locked with `SELECT FOR UPDATE` in ascending ID order |
| **Non-negative balance** | `CHECK (balance >= 0)` enforced at the database level |
| **Audit ledger** | Every balance change generates an immutable `transactions` entry |
| **Compound interest** | Monthly / daily / annual compounding with full `Decimal` precision |
| **Async I/O** | `asyncpg` driver + SQLAlchemy async engine for high concurrency |
| **Schema migrations** | Alembic with `transaction_per_migration=True` — DDL always atomic |

---

## Tech Stack

- **Python 3.12** — language
- **FastAPI 0.115** — web framework / OpenAPI docs at `/docs`
- **SQLAlchemy 2.0 (async)** — ORM + explicit `begin()` transaction control
- **asyncpg** — async PostgreSQL driver
- **Alembic** — database migrations
- **Pydantic v2** — request/response validation
- **bcrypt** — password hashing
- **PostgreSQL 16** — primary database (Docker Compose)
- **pytest-asyncio + httpx** — async test suite, SQLite in-memory for tests

---

## Architecture

```
app/
├── core/
│   ├── config.py          # Pydantic-settings (DATABASE_URL, SECRET_KEY…)
│   └── database.py        # Async engine, Base, get_db → begin() per request
│
├── domain/
│   └── bank/
│       ├── models.py          # BankAccount · Transaction (ledger) · Transfer
│       ├── schemas.py         # Pydantic request / response models
│       ├── exceptions.py      # Typed domain errors (InsufficientFunds…)
│       ├── repository.py      # AccountRepository (with FOR UPDATE) ·
│       │                      # TransactionRepository · TransferRepository
│       ├── transfer_service.py  # Atomic debit/credit in one session
│       ├── interest_calculator.py  # Simple & compound interest (pure + DB)
│       └── router.py          # POST /bank/accounts · POST /bank/transfers
│
├── models/
│   └── user.py            # User ORM model (owns bank accounts)
│
├── routers/
│   └── users.py           # POST /users/register
│
├── repositories/
│   └── user_repository.py
│
├── schemas/
│   └── user.py
│
├── services/
│   └── user_service.py
│
└── main.py                # FastAPI app ("Secure Banking API")

migrations/
├── env.py                             # Async Alembic runner
└── versions/
    ├── 0000_create_users_table.py     # users table
    └── 0001_create_bank_tables.py     # bank_accounts · transactions · transfers
                                       #   + CHECK (balance >= 0)
```

---

## Database Schema

```
users
 └─< bank_accounts  (user_id FK, CHECK balance >= 0)
       └─< transactions  (account_id FK — immutable ledger)
       └─< transfers     (from/to account_id FK, CHECK from ≠ to)
```

### Atomicity contract

A single transfer produces exactly **three writes** inside one transaction:

```
BEGIN
  UPDATE bank_accounts SET balance = balance - :amount WHERE id = :from_id  -- debit
  UPDATE bank_accounts SET balance = balance + :amount WHERE id = :to_id    -- credit
  INSERT INTO transactions (account_id, type, …) VALUES (:from_id, 'DEBIT', …)
  INSERT INTO transactions (account_id, type, …) VALUES (:to_id,   'CREDIT', …)
  INSERT INTO transfers (reference_code, status, …) VALUES (:uuid, 'COMPLETED', …)
COMMIT   ← auto by get_db begin() on clean exit
ROLLBACK ← auto by get_db begin() on any exception
```

---

## API Endpoints

### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |

### Users

| Method | Path | Body | Description |
|---|---|---|---|
| `POST` | `/api/v1/users/register` | `email, username, password` | Create a user |

### Bank accounts

| Method | Path | Body | Description |
|---|---|---|---|
| `POST` | `/api/v1/bank/accounts` | `user_id, account_type, interest_rate?, currency?` | Open an account |

### Transfers

| Method | Path | Body | Description |
|---|---|---|---|
| `POST` | `/api/v1/bank/transfers` | `from_account_id, to_account_id, amount, description?` | Atomic transfer |

Interactive docs available at **`http://localhost:8000/docs`** once the server is running.

---

## Getting Started

### 1. Clone & install

```bash
git clone https://github.com/julenmg/portfolio-task-manager.git
cd portfolio-task-manager
python -m virtualenv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# edit .env if needed (DATABASE_URL, SECRET_KEY)
```

### 3. Start PostgreSQL

```bash
docker compose up -d
```

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Start the API

```bash
uvicorn app.main:app --reload
```

The API is now live at `http://localhost:8000`.

---

## Running Tests

Tests use an **SQLite in-memory database** — no Docker required.

```bash
pytest tests/ -v
```

Coverage report is generated automatically. Current status:

- **41 tests · 0 failures · ≥ 92 % coverage**

### Test layout

```
tests/
├── conftest.py                   # SQLite engine, db_session, client fixtures
├── bank/
│   ├── conftest.py               # BankAccount fixtures
│   ├── test_transfer_service.py  # 14 cases — atomic transfers + error paths
│   └── test_interest_calculator.py  # 17 cases — pure math + DB apply
└── (user registration tests live here if re-enabled)
```

---

## Interest Calculation

### Simple interest

```
I = P × r × (days / 365)
```

### Compound interest

```
I = P × (1 + r/n)^(n × days/365) − P
```

| Period | `n` |
|---|---|
| `daily` | 365 |
| `monthly` | 12 |
| `annually` | 1 |

All arithmetic uses Python's `decimal.Decimal` for exact financial precision.

---

## License

MIT
