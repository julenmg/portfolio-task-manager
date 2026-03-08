# Casos de uso — Secure Banking API

Descripción de los flujos principales del sistema agrupados por actor.

---

## Actores

| Actor | Rol en el sistema | Permisos clave |
|---|---|---|
| **Customer** | Titular de cuenta bancaria | Ver y operar sus propias cuentas |
| **BankTeller** | Empleado de banca | Ver y operar cualquier cuenta, crear cuentas |
| **Admin** | Administrador del sistema | Acceso total + audit logs |

---

## UC-01 — Registro de usuario

**Actor:** cualquiera (anónimo)
**Precondición:** el servidor está en marcha
**Resultado:** usuario creado con rol `customer`

### Flujo principal

1. El cliente envía `POST /api/v1/users/register` con `email`, `username` y `password`.
2. El sistema valida el formato del email (RFC) y que la contraseña tenga al menos 8 caracteres.
3. El sistema comprueba que no exista ya un usuario con ese email o username.
4. El sistema almacena la contraseña con bcrypt (factor 12) y devuelve `201 Created` con el perfil del usuario.

### Flujos alternativos

| Condición | Respuesta |
|---|---|
| Email ya registrado | `409 Conflict – Email already registered` |
| Username ya usado | `409 Conflict – Username already taken` |
| Password < 8 chars | `422 Unprocessable Entity` |
| Email inválido | `422 Unprocessable Entity` |

```bash
curl -X POST http://localhost:8000/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@bank.com","username":"alice","password":"alice1234"}'
# → 201 {"id":1,"email":"alice@bank.com","username":"alice","role":"customer","is_active":true}
```

---

## UC-02 — Login y obtención de JWT

**Actor:** usuario registrado
**Precondición:** UC-01 completado
**Resultado:** token JWT válido 60 min

### Flujo principal

1. El cliente envía `POST /api/v1/auth/login` con `username` (email) y `password` en `application/x-www-form-urlencoded`.
2. El sistema localiza el usuario por email.
3. El sistema verifica la contraseña con `bcrypt.checkpw`.
4. El sistema comprueba que la cuenta esté activa (`is_active=true`).
5. El sistema genera un JWT HS256 con `sub` (user_id), `role` y `exp` (60 min).
6. Devuelve `200 OK` con `access_token`, `token_type` y `role`.

### Flujos alternativos

| Condición | Respuesta |
|---|---|
| Email no encontrado | `401 Unauthorized – Incorrect email or password` |
| Password incorrecta | `401 Unauthorized – Incorrect email or password` |
| Cuenta desactivada | `403 Forbidden – Account is disabled` |

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=alice@bank.com&password=alice1234" | jq -r .access_token)
```

---

## UC-03 — Crear cuenta bancaria

**Actor:** BankTeller, Admin
**Precondición:** JWT con rol `bank_teller` o `admin`
**Resultado:** nueva cuenta bancaria asociada a un usuario

### Flujo principal

1. El teller envía `POST /api/v1/bank/accounts` con `user_id`, `account_type`, `interest_rate` y `currency`.
2. El sistema valida el rol (403 si es Customer).
3. El sistema genera un número de cuenta único (`ACC` + 12 dígitos aleatorios).
4. Devuelve `201 Created` con los datos de la cuenta (saldo inicial 0.00).

### Tipos de cuenta

| Tipo | Descripción | Interest rate |
|---|---|---|
| `checking` | Cuenta corriente | Normalmente 0 % |
| `savings` | Cuenta de ahorro | Configurable (ej. 5 % anual) |

```bash
curl -X POST http://localhost:8000/api/v1/bank/accounts \
  -H "Authorization: Bearer $TELLER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"account_type":"savings","interest_rate":0.05,"currency":"EUR"}'
# → 201 {"id":1,"account_number":"ACC482910374821","account_type":"savings","balance":"0.00",...}
```

---

## UC-04 — Ver cuentas bancarias

**Actor:** cualquier usuario autenticado
**Precondición:** JWT válido
**Resultado:** lista de cuentas según el rol

### Flujo principal

1. El cliente envía `GET /api/v1/bank/accounts` con el Bearer token.
2. Si el rol es `customer`: el sistema devuelve solo las cuentas donde `user_id` coincide con el `sub` del token.
3. Si el rol es `bank_teller` o `admin`: el sistema devuelve todas las cuentas.

```bash
# Customer — ve solo sus cuentas
curl http://localhost:8000/api/v1/bank/accounts \
  -H "Authorization: Bearer $ALICE_TOKEN"

# Admin — ve todas las cuentas
curl http://localhost:8000/api/v1/bank/accounts \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## UC-05 — Transferencia entre cuentas

**Actor:** cualquier usuario autenticado
**Precondición:** ambas cuentas existen, activas y la origen tiene fondos suficientes
**Resultado:** transferencia atómica completada con ledger doble

### Flujo principal

1. El cliente envía `POST /api/v1/bank/transfers` con `from_account_id`, `to_account_id`, `amount` y `description` opcional.
2. Si el rol es `customer`, el sistema verifica que la cuenta origen le pertenezca.
3. El sistema abre una transacción SQL:
   - Bloquea ambas cuentas con `SELECT FOR UPDATE` en orden ascendente de ID (deadlock prevention).
   - Descuenta el importe de la cuenta origen.
   - Abona el importe en la cuenta destino.
   - Inserta un registro `DEBIT` en transactions para la cuenta origen.
   - Inserta un registro `CREDIT` en transactions para la cuenta destino.
   - Inserta un registro en `transfers` con `status=COMPLETED` y un `reference_code` UUID único.
4. El sistema hace commit.
5. Devuelve `200 OK` con los saldos resultantes y el `reference_code`.

### Flujos alternativos

| Condición | Respuesta |
|---|---|
| Cuenta no existe | `404 Not Found` |
| Cuenta inactiva | `404 Not Found` |
| Fondos insuficientes | `422 Unprocessable Entity` |
| `from_account_id == to_account_id` | `400 Bad Request` |
| `amount <= 0` | `400 Bad Request` |
| Customer transfiere desde cuenta ajena | `403 Forbidden` |

```bash
curl -X POST http://localhost:8000/api/v1/bank/transfers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"from_account_id":1,"to_account_id":2,"amount":"250.00","description":"Pago factura"}'
# → 200 {"reference_code":"uuid...","from_balance_after":"750.00","to_balance_after":"750.00",...}
```

---

## UC-06 — Consultar historial de transacciones

**Actor:** cualquier usuario autenticado
**Precondición:** la cuenta existe
**Resultado:** listado de movimientos ordenados por fecha descendente

### Flujo principal

1. El cliente envía `GET /api/v1/bank/accounts/{id}/transactions?limit=50&offset=0`.
2. El sistema comprueba que la cuenta exista.
3. Si el rol es `customer`, verifica que la cuenta le pertenezca.
4. Devuelve los registros del ledger con tipo (`DEBIT`/`CREDIT`), importe, saldo tras la operación, descripción y referencia.

```bash
curl "http://localhost:8000/api/v1/bank/accounts/1/transactions?limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

---

## UC-07 — Ver audit logs (Admin)

**Actor:** Admin
**Precondición:** JWT con rol `admin`
**Resultado:** listado de eventos de seguridad (401/403)

### Flujo principal

1. El admin envía `GET /api/v1/audit/logs?limit=50`.
2. El sistema comprueba el rol (403 si no es admin).
3. Devuelve los registros de `audit_logs`: método HTTP, ruta, IP, user_id, código de estado y motivo.

El **AuditMiddleware** registra automáticamente toda respuesta con código `401` o `403`, incluyendo:
- Ruta y método solicitados
- IP del cliente
- User ID extraído del token (si era válido pero sin permisos)
- Motivo del rechazo

```bash
curl http://localhost:8000/api/v1/audit/logs \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## UC-08 — Cálculo de interés compuesto (servicio interno)

**Actor:** sistema (llamada programática)
**Resultado:** nuevos saldos con interés aplicado

El módulo `interest_calculator.py` expone tres frecuencias de compounding:

| Frecuencia | Fórmula aplicada |
|---|---|
| `daily` | `P · (1 + r/365)^days` |
| `monthly` | `P · (1 + r/12)^months` |
| `annually` | `P · (1 + r)^years` |

Los cálculos usan `Decimal` para precisión exacta sin errores de punto flotante.

---

## Matriz de permisos completa

| Operación | Customer | BankTeller | Admin |
|---|:---:|:---:|:---:|
| Registrarse | ✅ | ✅ | ✅ |
| Login | ✅ | ✅ | ✅ |
| Ver sus cuentas | ✅ | ✅ | ✅ |
| Ver todas las cuentas | ❌ | ✅ | ✅ |
| Crear cuenta | ❌ | ✅ | ✅ |
| Transferir desde cuenta propia | ✅ | ✅ | ✅ |
| Transferir desde cualquier cuenta | ❌ | ✅ | ✅ |
| Ver sus transacciones | ✅ | ✅ | ✅ |
| Ver transacciones de cualquier cuenta | ❌ | ✅ | ✅ |
| Audit logs | ❌ | ❌ | ✅ |
