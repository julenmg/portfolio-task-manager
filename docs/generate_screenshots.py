"""
Generate SVG screenshots that replicate the look of the banking demo UI.
Run from the project root: python docs/generate_screenshots.py
Output: docs/screenshots/*.svg
"""

import os

OUT = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(OUT, exist_ok=True)

# ── Shared palette (matches index.html CSS variables) ─────────────────────
BG = "#0f1117"
SURFACE = "#1a1d27"
SURFACE2 = "#232636"
BORDER = "#2e3347"
ACCENT = "#5b8dee"
ACCENT2 = "#7c3aed"
GREEN = "#22c55e"
RED = "#ef4444"
YELLOW = "#f59e0b"
TEXT = "#e2e8f0"
MUTED = "#94a3b8"

W, H = 1200, 800
SIDEBAR_W = 220


def svg_header(title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'style="font-family:Segoe UI,system-ui,sans-serif">\n'
        f'<rect width="{W}" height="{H}" fill="{BG}"/>\n'
        f'<!-- {title} -->\n'
    )


def svg_footer() -> str:
    return "</svg>\n"


def sidebar(active: str) -> str:
    items = [
        ("🔑", "Login", "login"),
        ("✏️", "Registro", "register"),
        ("💳", "Cuentas", "accounts"),
        ("↔️", "Transferir", "transfer"),
        ("📋", "Transacciones", "transactions"),
        ("➕", "Nueva Cuenta", "create-account"),
        ("🔍", "Audit Logs", "audit"),
        ("📡", "API Reference", "api"),
    ]
    out = f'<rect x="0" y="0" width="{SIDEBAR_W}" height="{H}" fill="{SURFACE}" stroke="{BORDER}" stroke-width="1"/>\n'
    # logo
    out += f'<text x="16" y="36" fill="{ACCENT}" font-size="16" font-weight="700">🏦 BankingAPI</text>\n'
    out += f'<text x="16" y="52" fill="{MUTED}" font-size="10">Demo Interface v1.0</text>\n'
    out += f'<line x1="0" y1="62" x2="{SIDEBAR_W}" y2="62" stroke="{BORDER}"/>\n'

    sections = {"login": "CUENTA", "accounts": "BANCA", "create-account": "ADMIN", "api": "AYUDA"}
    y = 76
    for icon, label, key in items:
        if key in sections:
            out += f'<text x="16" y="{y}" fill="{MUTED}" font-size="9" font-weight="600">{sections[key]}</text>\n'
            y += 18
        bg = ACCENT if key == active else "none"
        tc = "#fff" if key == active else TEXT
        if key != active:
            out += f'<rect x="8" y="{y-14}" width="{SIDEBAR_W-16}" height="28" rx="6" fill="none"/>\n'
        else:
            out += f'<rect x="8" y="{y-14}" width="{SIDEBAR_W-16}" height="28" rx="6" fill="{bg}"/>\n'
        out += f'<text x="28" y="{y+4}" fill="{tc}" font-size="13">{icon} {label}</text>\n'
        y += 34
    return out


def card(x: int, y: int, w: int, h: int, title: str = "") -> str:
    out = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{SURFACE}" stroke="{BORDER}" stroke-width="1"/>\n'
    if title:
        out += f'<text x="{x+20}" y="{y+28}" fill="{TEXT}" font-size="13" font-weight="600">{title}</text>\n'
    return out


def label_input(x: int, y: int, w: int, label: str, value: str = "", placeholder: str = "") -> str:
    out = f'<text x="{x}" y="{y}" fill="{MUTED}" font-size="11" font-weight="500">{label}</text>\n'
    out += f'<rect x="{x}" y="{y+6}" width="{w}" height="34" rx="7" fill="{SURFACE2}" stroke="{BORDER}" stroke-width="1"/>\n'
    displayed = value if value else placeholder
    colour = TEXT if value else MUTED
    out += f'<text x="{x+10}" y="{y+28}" fill="{colour}" font-size="12">{displayed}</text>\n'
    return out


def button(x: int, y: int, w: int, label: str, colour: str = None) -> str:
    bg = colour or ACCENT
    out = f'<rect x="{x}" y="{y}" width="{w}" height="36" rx="7" fill="{bg}"/>\n'
    out += f'<text x="{x+w//2}" y="{y+22}" fill="#fff" font-size="13" font-weight="600" text-anchor="middle">{label}</text>\n'
    return out


def badge(x: int, y: int, label: str, colour: str, bg: str) -> str:
    bw = len(label) * 7 + 14
    out = f'<rect x="{x}" y="{y-12}" width="{bw}" height="18" rx="4" fill="{bg}"/>\n'
    out += f'<text x="{x+7}" y="{y}" fill="{colour}" font-size="9" font-weight="700">{label}</text>\n'
    return out


def alert_success(x: int, y: int, w: int, msg: str) -> str:
    out = f'<rect x="{x}" y="{y}" width="{w}" height="36" rx="7" fill="rgba(34,197,94,0.1)" stroke="{GREEN}" stroke-width="1"/>\n'
    out += f'<text x="{x+14}" y="{y+22}" fill="{GREEN}" font-size="12">✓ {msg}</text>\n'
    return out


# ── Screenshot 1: Login panel ─────────────────────────────────────────────
def make_login() -> str:
    s = svg_header("Login")
    s += sidebar("login")
    MX = SIDEBAR_W + 32

    s += f'<text x="{MX}" y="52" fill="{TEXT}" font-size="22" font-weight="600">🔑 Iniciar Sesión</text>\n'
    s += f'<text x="{MX}" y="72" fill="{MUTED}" font-size="13">Accede con tu email y contraseña para obtener un JWT.</text>\n'

    # credentials card
    s += card(MX, 90, 420, 240, "Credenciales")
    s += label_input(MX+20, 132, 380, "Email", "admin@demo.com")
    s += label_input(MX+20, 192, 380, "Contraseña", "••••••••")
    s += button(MX+20, 244, 100, "Entrar")

    # demo credentials card
    s += card(MX, 348, 420, 170, "Credenciales de Demo")
    rows = [
        ("Admin", "admin@demo.com", "admin1234", ACCENT2, f"rgba(124,58,237,0.15)"),
        ("Teller", "teller@demo.com", "teller1234", YELLOW, f"rgba(245,158,11,0.15)"),
        ("Customer", "alice@demo.com", "alice1234", ACCENT, f"rgba(91,141,238,0.15)"),
    ]
    for i, (role, email, pw, tc, bg) in enumerate(rows):
        ry = 394 + i * 36
        s += badge(MX+20, ry+10, role.upper(), tc, bg)
        s += f'<text x="{MX+110}" y="{ry+10}" fill="{TEXT}" font-size="11">{email}</text>\n'
        s += f'<text x="{MX+290}" y="{ry+10}" fill="{MUTED}" font-size="11">{pw}</text>\n'
        s += f'<rect x="{MX+370}" y="{ry-4}" width="42" height="20" rx="5" fill="{SURFACE2}" stroke="{BORDER}" stroke-width="1"/>\n'
        s += f'<text x="{MX+391}" y="{ry+10}" fill="{TEXT}" font-size="10" text-anchor="middle">Usar</text>\n'

    s += svg_footer()
    return s


# ── Screenshot 2: Login success (logged in) ───────────────────────────────
def make_login_success() -> str:
    s = svg_header("Login Success")
    s += sidebar("login")
    MX = SIDEBAR_W + 32

    # user badge in sidebar
    s += f'<rect x="8" y="{H-100}" width="{SIDEBAR_W-16}" height="68" rx="8" fill="{SURFACE2}"/>\n'
    s += f'<text x="20" y="{H-78}" fill="{ACCENT}" font-size="9" font-weight="700">ADMIN</text>\n'
    s += f'<text x="20" y="{H-62}" fill="{MUTED}" font-size="10">admin@demo.com</text>\n'
    s += f'<rect x="8" y="{H-44}" width="{SIDEBAR_W-16}" height="28" rx="7" fill="none" stroke="{RED}" stroke-width="1"/>\n'
    s += f'<text x="{SIDEBAR_W//2}" y="{H-26}" fill="{RED}" font-size="11" text-anchor="middle">Cerrar sesión</text>\n'

    s += f'<text x="{MX}" y="52" fill="{TEXT}" font-size="22" font-weight="600">🔑 Iniciar Sesión</text>\n'
    s += card(MX, 90, 420, 280, "Credenciales")
    s += label_input(MX+20, 132, 380, "Email", "admin@demo.com")
    s += label_input(MX+20, 192, 380, "Contraseña", "••••••••")
    s += button(MX+20, 244, 100, "Entrar")
    s += alert_success(MX+20, 290, 380, "¡Bienvenido! Rol: admin")

    # JWT token box
    s += f'<text x="{MX+20}" y="{H-420+60}" fill="{MUTED}" font-size="10">Token JWT:</text>\n'
    s += f'<rect x="{MX+20}" y="{H-410+60}" width="380" height="50" rx="7" fill="{SURFACE2}" stroke="{BORDER}" stroke-width="1"/>\n'
    s += f'<text x="{MX+28}" y="{H-390+60}" fill="{MUTED}" font-size="9" font-family="monospace">eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIi...</text>\n'

    s += svg_footer()
    return s


# ── Screenshot 3: Accounts panel ─────────────────────────────────────────
def make_accounts() -> str:
    s = svg_header("Accounts")
    s += sidebar("accounts")
    MX = SIDEBAR_W + 32

    s += f'<text x="{MX}" y="52" fill="{TEXT}" font-size="22" font-weight="600">💳 Mis Cuentas</text>\n'
    s += f'<text x="{MX}" y="72" fill="{MUTED}" font-size="13">Lista de cuentas bancarias visibles según tu rol.</text>\n'

    # table card
    cw = W - MX - 32
    s += card(MX, 90, cw, 380, "")
    s += f'<text x="{MX+20}" y="118" fill="{TEXT}" font-size="13" font-weight="600">Cuentas Bancarias</text>\n'
    s += f'<rect x="{MX+cw-110}" y="100" width="90" height="28" rx="6" fill="{SURFACE2}" stroke="{BORDER}" stroke-width="1"/>\n'
    s += f'<text x="{MX+cw-65}" y="118" fill="{TEXT}" font-size="11" text-anchor="middle">🔄 Actualizar</text>\n'

    # table header
    cols = ["ID", "Número", "Tipo", "Saldo", "Moneda", "Interés", "Estado", "Acciones"]
    col_x = [MX+20, MX+55, MX+190, MX+290, MX+390, MX+460, MX+530, MX+640]
    s += f'<rect x="{MX}" y="130" width="{cw}" height="30" fill="{SURFACE2}"/>\n'
    for i, col in enumerate(cols):
        s += f'<text x="{col_x[i]}" y="149" fill="{MUTED}" font-size="10" font-weight="600">{col.upper()}</text>\n'

    # table rows
    accounts = [
        ("1", "ACC482910374821", "savings", "5,000.00", "EUR", "5.00%", "Activa", GREEN, f"rgba(34,197,94,0.15)", ACCENT, f"rgba(91,141,238,0.15)"),
        ("2", "ACC183920571049", "checking", "1,000.00", "EUR", "0.00%", "Activa", GREEN, f"rgba(34,197,94,0.15)", GREEN, f"rgba(34,197,94,0.15)"),
        ("3", "ACC920184730291", "checking", "200.00", "EUR", "0.00%", "Inactiva", RED, f"rgba(239,68,68,0.15)", GREEN, f"rgba(34,197,94,0.15)"),
        ("4", "ACC571039284761", "savings", "12,450.00", "EUR", "3.50%", "Activa", GREEN, f"rgba(34,197,94,0.15)", ACCENT, f"rgba(91,141,238,0.15)"),
    ]
    for i, (aid, num, atype, bal, cur, rate, status, stc, stbg, ttc, ttbg) in enumerate(accounts):
        ry = 168 + i * 40
        s += f'<line x1="{MX}" y1="{ry-2}" x2="{MX+cw}" y2="{ry-2}" stroke="{BORDER}"/>\n'
        s += f'<text x="{col_x[0]}" y="{ry+16}" fill="{TEXT}" font-size="12">{aid}</text>\n'
        s += f'<text x="{col_x[1]}" y="{ry+16}" fill="{MUTED}" font-size="10" font-family="monospace">{num}</text>\n'
        s += badge(col_x[2], ry+16, atype.upper(), ttc, ttbg)
        s += f'<text x="{col_x[3]}" y="{ry+16}" fill="{TEXT}" font-size="12" font-weight="700">{bal}</text>\n'
        s += f'<text x="{col_x[4]}" y="{ry+16}" fill="{TEXT}" font-size="12">{cur}</text>\n'
        s += f'<text x="{col_x[5]}" y="{ry+16}" fill="{TEXT}" font-size="12">{rate}</text>\n'
        s += badge(col_x[6], ry+16, status.upper(), stc, stbg)
        s += f'<rect x="{col_x[7]}" y="{ry+2}" width="72" height="22" rx="5" fill="{SURFACE2}" stroke="{BORDER}" stroke-width="1"/>\n'
        s += f'<text x="{col_x[7]+36}" y="{ry+17}" fill="{TEXT}" font-size="10" text-anchor="middle">📋 Txn</text>\n'

    s += svg_footer()
    return s


# ── Screenshot 4: Transfer panel ─────────────────────────────────────────
def make_transfer() -> str:
    s = svg_header("Transfer")
    s += sidebar("transfer")
    MX = SIDEBAR_W + 32

    s += f'<text x="{MX}" y="52" fill="{TEXT}" font-size="22" font-weight="600">↔️ Transferencia</text>\n'
    s += f'<text x="{MX}" y="72" fill="{MUTED}" font-size="13">Envía dinero entre cuentas de forma atómica.</text>\n'

    s += card(MX, 90, 460, 420, "Nueva Transferencia")
    s += label_input(MX+20, 132, 420, "ID Cuenta Origen", "1")
    s += label_input(MX+20, 192, 420, "ID Cuenta Destino", "2")
    s += label_input(MX+20, 252, 420, "Importe (EUR)", "250.00")
    s += label_input(MX+20, 312, 420, "Descripción (opcional)", "", "Pago alquiler")
    s += button(MX+20, 368, 120, "Transferir")

    # success result
    s += alert_success(MX+20, 416, 420, "Transferencia completada. Ref: 550e8400-e29b…")

    # result JSON box
    s += f'<rect x="{MX+20}" y="464" width="420" height="70" rx="7" fill="{SURFACE2}" stroke="{BORDER}" stroke-width="1"/>\n'
    json_lines = [
        '  "reference_code": "550e8400-e29b-41d4-a716-4466554400",',
        '  "from_balance_after": "750.00",',
        '  "to_balance_after": "750.00"',
    ]
    for i, line in enumerate(json_lines):
        s += f'<text x="{MX+30}" y="{482 + i * 16}" fill="{MUTED}" font-size="10" font-family="monospace">{line}</text>\n'

    s += svg_footer()
    return s


# ── Screenshot 5: Audit logs panel ───────────────────────────────────────
def make_audit() -> str:
    s = svg_header("Audit Logs")
    s += sidebar("audit")
    MX = SIDEBAR_W + 32

    s += f'<text x="{MX}" y="52" fill="{TEXT}" font-size="22" font-weight="600">🔍 Audit Logs</text>\n'
    s += f'<text x="{MX}" y="72" fill="{MUTED}" font-size="13">Registro de intentos no autorizados. Solo Admin.</text>\n'

    cw = W - MX - 32
    s += card(MX, 90, cw, 380, "")
    s += f'<text x="{MX+20}" y="118" fill="{TEXT}" font-size="13" font-weight="600">Registros de Auditoría</text>\n'

    cols = ["ID", "MÉTODO", "RUTA", "IP", "USER ID", "STATUS", "MOTIVO", "FECHA"]
    col_x = [MX+20, MX+50, MX+110, MX+340, MX+430, MX+510, MX+590, MX+720]
    s += f'<rect x="{MX}" y="130" width="{cw}" height="30" fill="{SURFACE2}"/>\n'
    for i, col in enumerate(cols):
        s += f'<text x="{col_x[i]}" y="149" fill="{MUTED}" font-size="10" font-weight="600">{col}</text>\n'

    logs = [
        ("1", "GET", "/api/v1/audit/logs", "192.168.1.42", "—", "401", "Token expirado", "08/03/26 10:02"),
        ("2", "POST", "/api/v1/bank/accounts", "192.168.1.15", "3", "403", "Requires role: bank_teller or admin", "08/03/26 10:05"),
        ("3", "GET", "/api/v1/bank/accounts/7", "10.0.0.11", "5", "403", "You can only view your own accounts", "08/03/26 10:08"),
        ("4", "GET", "/api/v1/audit/logs", "192.168.1.42", "—", "401", "Could not validate credentials", "08/03/26 10:11"),
    ]
    status_colours = {"401": (YELLOW, "rgba(245,158,11,0.15)"), "403": (RED, "rgba(239,68,68,0.15)")}
    method_colours = {"GET": (ACCENT, "rgba(91,141,238,0.15)"), "POST": (GREEN, "rgba(34,197,94,0.15)")}
    for i, (lid, method, path, ip, uid, code, reason, date) in enumerate(logs):
        ry = 168 + i * 46
        s += f'<line x1="{MX}" y1="{ry-2}" x2="{MX+cw}" y2="{ry-2}" stroke="{BORDER}"/>\n'
        s += f'<text x="{col_x[0]}" y="{ry+16}" fill="{TEXT}" font-size="12">{lid}</text>\n'
        mc, mbg = method_colours.get(method, (TEXT, SURFACE2))
        s += badge(col_x[1], ry+16, method, mc, mbg)
        s += f'<text x="{col_x[2]}" y="{ry+16}" fill="{MUTED}" font-size="9" font-family="monospace">{path[:30]}</text>\n'
        s += f'<text x="{col_x[3]}" y="{ry+16}" fill="{TEXT}" font-size="11">{ip}</text>\n'
        s += f'<text x="{col_x[4]}" y="{ry+16}" fill="{TEXT}" font-size="12">{uid}</text>\n'
        sc, sbg = status_colours.get(code, (TEXT, SURFACE2))
        s += badge(col_x[5], ry+16, code, sc, sbg)
        s += f'<text x="{col_x[6]}" y="{ry+16}" fill="{MUTED}" font-size="9">{reason[:30]}</text>\n'
        s += f'<text x="{col_x[7]}" y="{ry+16}" fill="{MUTED}" font-size="10">{date}</text>\n'

    s += svg_footer()
    return s


# ── Write all ─────────────────────────────────────────────────────────────
screenshots = {
    "01-login.svg": make_login(),
    "02-login-success.svg": make_login_success(),
    "03-accounts.svg": make_accounts(),
    "04-transfer.svg": make_transfer(),
    "05-audit-logs.svg": make_audit(),
}

for filename, content in screenshots.items():
    path = os.path.join(OUT, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✓ {path}")

print("\nAll screenshots generated.")
