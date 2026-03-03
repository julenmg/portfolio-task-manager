# 🏦 Secure Banking API

API REST bancaria de nivel producción construida con **FastAPI**, **SQLAlchemy async** y **PostgreSQL**. Implementa transferencias atómicas, RBAC con JWT, cálculo de intereses compuestos y auditoría de seguridad automática.

> **Demo visual:** una vez levantado el servidor, abre `http://localhost:8000/demo`
> **Swagger UI:** `http://localhost:8000/docs`

---

## ✨ Características

| Característica | Detalle |
|---|---|
| **Transferencias atómicas** | Débito + crédito + ledger en una sola transacción SQL |
| **Deadlock prevention** | Bloqueo `SELECT FOR UPDATE` en orden ascendente de ID |
| **RBAC con JWT** | Roles `customer`, `bank_teller`, `admin` validados en BD cada request |
| **Interés compuesto** | Compounding diario / mensual / anual con `Decimal` exacto |
| **Audit middleware** | Registra automáticamente todo 401 / 403 en `audit_logs` |
| **Balance no-negativo** | `CHECK (balance >= 0)` en la BD |
| **Async I/O** | `asyncpg` + SQLAlchemy async engine |
| **Migraciones** | Alembic con `transaction_per_migration=True` |
| **Tests** | 58 tests · cobertura ≥ 90 % · SQLite en memoria |

---

## 🛠️ Stack

- Python 3.12 · FastAPI 0.115 · SQLAlchemy 2.0 async · asyncpg
- Alembic · Pydantic v2 · bcrypt · python-jose (JWT HS256)
- PostgreSQL 16 (Docker Compose) · pytest-asyncio · httpx

---

## 🚀 Inicio rápido

### 1. Clonar e instalar

```bash
git clone https://github.com/julenmg/portfolio-task-manager.git
cd portfolio-task-manager
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar entorno

```bash
cp .env.example .env
# Edita .env si necesitas cambiar DATABASE_URL o SECRET_KEY
```

Contenido mínimo de `.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/task_manager
SECRET_KEY=cambia-esto-en-produccion
```

### 3. Iniciar PostgreSQL con Docker

```bash
docker compose up -d
```

### 4. Aplicar migraciones

```bash
alembic upgrade head
```

### 5. Levantar el servidor

```bash
uvicorn app.main:app --reload
```

La API está disponible en `http://localhost:8000`.

---

## 🎬 Demo paso a paso

### Opción A — Interfaz visual (recomendada)

1. Levanta el servidor: `uvicorn app.main:app --reload`
2. Abre `http://localhost:8000/demo`
3. Sigue los pasos del manual visual integrado

### Opción B — curl / Swagger

Sigue el flujo manual a continuación:

---

## 📖 Manual de uso

### Paso 1 — Registrar usuarios

```bash
# Registrar un customer
curl -X POST http://localhost:8000/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","username":"alice","password":"alice1234"}'

# Registrar otro customer
curl -X POST http://localhost:8000/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{"email":"bob@example.com","username":"bob","password":"bob1234"}'
```

> Los usuarios se registran siempre como `CUSTOMER`. Para elevar a `bank_teller` o `admin` actualiza el campo `role` directamente en la BD o con una herramienta de administración.

### Paso 2 — Login y obtener JWT

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=alice@example.com&password=alice1234" | jq -r .access_token)
echo $TOKEN
```

El token caduca en **60 minutos**.

### Paso 3 — Crear cuentas (BankTeller / Admin)

```bash
# Necesitas un token con rol bank_teller o admin
TELLER_TOKEN="..."

# Cuenta corriente para Alice (user_id=1)
curl -X POST http://localhost:8000/api/v1/bank/accounts \
  -H "Authorization: Bearer $TELLER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"account_type":"checking","currency":"EUR"}'

# Cuenta ahorro para Alice (5% anual)
curl -X POST http://localhost:8000/api/v1/bank/accounts \
  -H "Authorization: Bearer $TELLER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"account_type":"savings","interest_rate":0.05,"currency":"EUR"}'

# Cuenta corriente para Bob (user_id=2)
curl -X POST http://localhost:8000/api/v1/bank/accounts \
  -H "Authorization: Bearer $TELLER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":2,"account_type":"checking","currency":"EUR"}'
```

### Paso 4 — Ver cuentas

```bash
# Alice ve solo sus propias cuentas
curl http://localhost:8000/api/v1/bank/accounts \
  -H "Authorization: Bearer $TOKEN"

# Detalle de una cuenta concreta
curl http://localhost:8000/api/v1/bank/accounts/1 \
  -H "Authorization: Bearer $TOKEN"
```

### Paso 5 — Transferir dinero

```bash
# Transferencia de 150 € de cuenta 1 a cuenta 3
curl -X POST http://localhost:8000/api/v1/bank/transfers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "from_account_id": 1,
    "to_account_id": 3,
    "amount": "150.00",
    "description": "Pago alquiler"
  }'
```

Respuesta:
```json
{
  "reference_code": "550e8400-e29b-41d4-a716-446655440000",
  "from_account_id": 1,
  "to_account_id": 3,
  "amount": "150.00",
  "from_balance_after": "850.00",
  "to_balance_after": "650.00"
}
```

### Paso 6 — Consultar transacciones

```bash
curl "http://localhost:8000/api/v1/bank/accounts/1/transactions?limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

### Paso 7 — Ver audit logs (Admin)

```bash
ADMIN_TOKEN="..."
curl http://localhost:8000/api/v1/audit/logs \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## 📡 Referencia de endpoints

```
GET  /health                                    → Health check
GET  /demo                                      → Interfaz demo HTML
GET  /docs                                      → Swagger UI
GET  /redoc                                     → ReDoc

POST /api/v1/users/register                     → Registrar usuario
POST /api/v1/auth/login                         → Login → JWT

POST /api/v1/bank/accounts                      → Crear cuenta (Teller/Admin)
GET  /api/v1/bank/accounts                      → Listar cuentas
GET  /api/v1/bank/accounts/{id}                 → Detalle de cuenta
POST /api/v1/bank/transfers                     → Transferencia atómica
GET  /api/v1/bank/accounts/{id}/transactions    → Historial de movimientos

GET  /api/v1/audit/logs                         → Audit log (Admin)
```

---

## 🔐 RBAC — Control de acceso

| Endpoint | Customer | BankTeller | Admin |
|---|---|---|---|
| Registro / Login | ✅ | ✅ | ✅ |
| Ver cuentas | ✅ solo propias | ✅ todas | ✅ todas |
| Crear cuenta | ❌ | ✅ | ✅ |
| Transferir | ✅ solo desde propia | ✅ cualquiera | ✅ cualquiera |
| Ver transacciones | ✅ solo propias | ✅ cualquiera | ✅ cualquiera |
| Audit logs | ❌ | ❌ | ✅ |

---

## 🗃️ Esquema de base de datos

```
users
 └─< bank_accounts   (user_id FK · CHECK balance >= 0)
       └─< transactions  (ledger inmutable: DEBIT / CREDIT)
       └─< transfers     (envelope: from_id, to_id, status, reference_code)
audit_logs           (append-only · FK user_id nullable)
```

### Garantía de atomicidad por transferencia

```sql
BEGIN
  SELECT … FOR UPDATE  -- bloquea ambas filas en orden ID ascendente
  UPDATE bank_accounts SET balance = balance - :amount  -- débito
  UPDATE bank_accounts SET balance = balance + :amount  -- crédito
  INSERT INTO transactions (type='DEBIT',  reference_code=:uuid, …)
  INSERT INTO transactions (type='CREDIT', reference_code=:uuid, …)
  INSERT INTO transfers (status='COMPLETED', reference_code=:uuid, …)
COMMIT   -- automático al salir del contexto get_db sin excepción
ROLLBACK -- automático ante cualquier excepción
```

---

## 🧪 Tests

```bash
# Ejecutar todos los tests con cobertura
pytest

# Solo un módulo
pytest tests/bank/test_transfer_service.py -v
```

**Estado actual:** 58 tests · 0 fallos · cobertura ≥ 90 %

| Suite | Tests | Qué cubre |
|---|---|---|
| `test_auth.py` | 4 | Login correcto/incorrecto, roles |
| `test_transfer_service.py` | 13 | Transferencias: happy path + 8 casos de error |
| `test_interest_calculator.py` | 13 | Interés simple/compuesto + apply con BD |
| `test_rbac.py` | 20 | Permisos de cada rol en todos los endpoints |
| `test_audit_middleware.py` | 8 | Audit logs 401/403, campos, user_id |

---

## 📁 Estructura del proyecto

```
portfolio-task-manager/
├── app/
│   ├── core/           # config, database, security (JWT)
│   ├── domain/
│   │   ├── auth/       # login router, JWT dependencies, schemas
│   │   └── bank/       # models, repository, transfer_service,
│   │                   # interest_calculator, router, exceptions
│   ├── middleware/     # AuditMiddleware
│   ├── models/         # User, AuditLog
│   ├── repositories/   # UserRepository, AuditLogRepository
│   ├── routers/        # users, audit
│   ├── schemas/        # Pydantic user schemas
│   ├── services/       # UserService
│   └── main.py
├── frontend/
│   └── index.html      # Interfaz demo SPA
├── migrations/         # Alembic versions
├── tests/
│   ├── conftest.py
│   └── bank/
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
├── FEATURES.md         # Resumen detallado de funcionalidades
└── README.md           # Este archivo
```

---

## 📜 Licencia

MIT
