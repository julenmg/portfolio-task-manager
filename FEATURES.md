# Secure Banking API — Resumen de Funcionalidades

## Índice
1. [Arquitectura](#arquitectura)
2. [Autenticación y Seguridad](#autenticación-y-seguridad)
3. [Control de Acceso por Roles (RBAC)](#control-de-acceso-por-roles-rbac)
4. [Gestión de Usuarios](#gestión-de-usuarios)
5. [Cuentas Bancarias](#cuentas-bancarias)
6. [Transferencias Atómicas](#transferencias-atómicas)
7. [Historial de Transacciones](#historial-de-transacciones)
8. [Cálculo de Intereses](#cálculo-de-intereses)
9. [Auditoría de Seguridad](#auditoría-de-seguridad)
10. [Interfaz Demo](#interfaz-demo)
11. [Testing](#testing)
12. [Endpoints Completos](#endpoints-completos)

---

## Arquitectura

```
app/
├── core/           # Configuración, BD, seguridad JWT
├── domain/
│   ├── auth/       # Login, dependencias JWT, esquemas
│   └── bank/       # Modelos ORM, repositorios, servicio de transferencias,
│                   # calculadora de intereses, router, excepciones
├── middleware/     # AuditMiddleware (401/403)
├── models/         # User, AuditLog
├── repositories/   # UserRepository, AuditLogRepository
├── routers/        # users, audit
├── schemas/        # Pydantic: user
└── services/       # UserService (registro)
```

**Stack:** Python 3.12 · FastAPI · SQLAlchemy 2 (async) · PostgreSQL · Alembic · bcrypt · python-jose

---

## Autenticación y Seguridad

| Característica | Detalle |
|---|---|
| Algoritmo JWT | HS256, TTL 60 min |
| Hashing contraseñas | bcrypt (coste 12) |
| Transporte token | Bearer header (`Authorization: Bearer <token>`) |
| Validación DB en cada request | El rol se lee de DB, no del token, para que los cambios sean inmediatos |
| Secret configurable | Variable `SECRET_KEY` en `.env` |

---

## Control de Acceso por Roles (RBAC)

Tres roles definidos en `app/models/user.py`:

| Rol | Valor | Permisos |
|---|---|---|
| `CUSTOMER` | `customer` | Ver/transferir solo desde sus propias cuentas |
| `BANK_TELLER` | `bank_teller` | Ver cualquier cuenta, crear cuentas, transferir entre cualesquiera |
| `ADMIN` | `admin` | Todo lo anterior + acceso a audit logs |

### Matriz de permisos por endpoint

| Endpoint | Customer | BankTeller | Admin |
|---|---|---|---|
| `POST /users/register` | ✅ | ✅ | ✅ |
| `POST /auth/login` | ✅ | ✅ | ✅ |
| `GET /bank/accounts` | ✅ (solo propias) | ✅ | ✅ |
| `GET /bank/accounts/{id}` | ✅ (solo propia) | ✅ | ✅ |
| `POST /bank/accounts` | ❌ | ✅ | ✅ |
| `POST /bank/transfers` | ✅ (solo desde propia) | ✅ | ✅ |
| `GET /bank/accounts/{id}/transactions` | ✅ (solo propia) | ✅ | ✅ |
| `GET /audit/logs` | ❌ | ❌ | ✅ |

---

## Gestión de Usuarios

### `POST /api/v1/users/register`
- Crea un usuario con rol `CUSTOMER` por defecto.
- Valida unicidad de email y username.
- Password hasheado con bcrypt antes de guardar.
- Validaciones: email válido, username 3–100 chars (alfanumérico + `-_`), password 8–128 chars.

### `POST /api/v1/auth/login`
- Acepta `username` (email) y `password` como form data (OAuth2PasswordRequestForm).
- Devuelve `{ access_token, token_type, role }`.
- Registra intento fallido en audit log (→ 401).

---

## Cuentas Bancarias

### `POST /api/v1/bank/accounts` _(BankTeller / Admin)_
- Crea una cuenta bancaria para un usuario dado.
- Número de cuenta auto-generado (`ACC` + 12 dígitos aleatorios).
- Tipos: `checking` (corriente) o `savings` (ahorro).
- Campos: `user_id`, `account_type`, `interest_rate` (0–1), `currency` (ISO 3-char).

### `GET /api/v1/bank/accounts` _(autenticado)_
- Customer: devuelve solo sus propias cuentas.
- BankTeller / Admin: devuelve todas las cuentas del sistema.

### `GET /api/v1/bank/accounts/{account_id}` _(autenticado)_
- Detalle de una cuenta concreta.
- Customer solo puede ver cuentas que le pertenecen (403 si no).

---

## Transferencias Atómicas

### `POST /api/v1/bank/transfers`

**Garantías de atomicidad:**
1. Ambas cuentas se bloquean con `SELECT … FOR UPDATE` en orden ascendente de ID para evitar deadlocks.
2. Se valida saldo suficiente antes de cualquier escritura.
3. En una sola transacción BD se generan:
   - Fila en `transfers` (estado `COMPLETED`)
   - Fila `DEBIT` en `transactions` (cuenta origen)
   - Fila `CREDIT` en `transactions` (cuenta destino)
4. Ambas filas de ledger comparten el mismo `reference_code` UUID.
5. Cualquier excepción revierte todos los cambios automáticamente.

**Errores manejados:**

| Código HTTP | Condición |
|---|---|
| 400 | Importe ≤ 0 o transferencia a la misma cuenta |
| 403 | Customer intentando transferir desde cuenta ajena |
| 404 | Cuenta origen o destino no encontrada / inactiva |
| 422 | Fondos insuficientes |

**Respuesta:**
```json
{
  "reference_code": "550e8400-e29b-41d4-a716-446655440000",
  "from_account_id": 1,
  "to_account_id": 2,
  "amount": "150.00",
  "from_balance_after": "850.00",
  "to_balance_after": "650.00"
}
```

---

## Historial de Transacciones

### `GET /api/v1/bank/accounts/{id}/transactions`

- Paginado: parámetros `limit` (default 50) y `offset` (default 0).
- Ordenado de más reciente a más antiguo.
- Cada transacción incluye: `balance_after` (saldo tras la operación), `reference_code` (UUID compartido entre DEBIT y CREDIT de la misma transferencia).

---

## Cálculo de Intereses

Módulo `app/domain/bank/interest_calculator.py`:

### Interés simple
```
I = P × r × (days / 365)
```

### Interés compuesto
```
I = P × (1 + r/n)^(n×t) − P
donde n = períodos/año, t = days/365
```

**Períodos soportados:** `daily` (365), `monthly` (12), `annually` (1).

**Método `apply_interest`:**
- Solo aplicable a cuentas de tipo `savings`.
- Valida que la cuenta existe y está activa.
- Genera un CREDIT en el ledger con la descripción del período y tipo de compounding.
- El llamador gestiona el commit de la sesión.

---

## Auditoría de Seguridad

### AuditMiddleware (`app/middleware/audit.py`)

- Se ejecuta **después** de cada request.
- Registra automáticamente toda respuesta `401` o `403`:
  - Método HTTP, ruta, IP del cliente
  - User ID (extraído del JWT si está presente, `null` si no)
  - Código de estado y motivo (`Unauthenticated access attempt` / `Unauthorized access attempt`)
- Los logs son append-only (sin UPDATE ni DELETE).
- Fallo en la escritura nunca propaga error al cliente.

### `GET /api/v1/audit/logs` _(Admin only)_
- Devuelve hasta 100 entradas (configurable con `limit` y `offset`).
- Ordenado de más reciente a más antiguo.

---

## Interfaz Demo

### Acceso
Levanta el servidor y abre `http://localhost:8000/demo`

### Secciones
| Sección | Descripción |
|---|---|
| Login | Autenticación y obtención de JWT |
| Registro | Registro de nuevos usuarios |
| Cuentas | Listado de cuentas bancarias |
| Transferir | Formulario de transferencia |
| Transacciones | Historial de movimientos |
| Nueva Cuenta | Crear cuentas (Teller/Admin) |
| Audit Logs | Registros de seguridad (Admin) |
| API Reference | Tabla de endpoints disponibles |

---

## Testing

- **Framework:** pytest + pytest-asyncio + httpx (ASGI transport)
- **Base de datos:** SQLite en memoria (aiosqlite) con StaticPool
- **Cobertura:** ≥ 90% (umbral configurado en `pyproject.toml`)

### Suites de tests

| Fichero | Qué prueba |
|---|---|
| `tests/test_auth.py` | Login: credenciales correctas/incorrectas, roles en el token |
| `tests/bank/test_transfer_service.py` | Servicio de transferencias: happy path, fondos insuficientes, cuenta inactiva, cuenta no encontrada, importes inválidos |
| `tests/bank/test_interest_calculator.py` | Interés simple/compuesto (pure), apply_interest con BD |
| `tests/bank/test_rbac.py` | RBAC completo: Customer vs Teller vs Admin en todos los endpoints |
| `tests/bank/test_audit_middleware.py` | AuditMiddleware: 401/403 generan filas, 200 no genera, campos correctos |

---

## Endpoints Completos

```
GET  /health                                → Estado del servidor
GET  /demo                                  → Interfaz demo HTML
GET  /docs                                  → Swagger UI
GET  /redoc                                 → ReDoc

POST /api/v1/users/register                 → Registro de usuario
POST /api/v1/auth/login                     → Login → JWT

POST /api/v1/bank/accounts                  → Crear cuenta (Teller/Admin)
GET  /api/v1/bank/accounts                  → Listar cuentas
GET  /api/v1/bank/accounts/{id}             → Detalle de cuenta
POST /api/v1/bank/transfers                 → Transferencia atómica
GET  /api/v1/bank/accounts/{id}/transactions → Historial de transacciones

GET  /api/v1/audit/logs                     → Audit log (Admin)
```
