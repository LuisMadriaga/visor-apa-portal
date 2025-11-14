import os
import json
import time
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# =====================================================
# 1️⃣ Cargar variables de entorno desde .env
# =====================================================
load_dotenv()

FERNET_KEY = os.getenv("FERNET_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://examenes.falp.org/visor_apa_portal_2").rstrip("/")

if not FERNET_KEY:
    raise ValueError("⚠️ No se encontró la variable FERNET_KEY en el entorno o .env")

# =====================================================
# 2️⃣ Crear instancia Fernet
# =====================================================
try:
    fernet = Fernet(FERNET_KEY.encode())
except Exception as e:
    raise ValueError(f"❌ Error al inicializar Fernet: {e}")

# =====================================================
# 3️⃣ Datos del payload (idéntico a crypto_utils.py)
# =====================================================
rut = input("👉 Ingrese el RUT para generar token (ej: 12345678-9): ").strip() or "9895722-7"

payload = {
    "rut": rut,
    "ts": int(time.time()),
    "type": "access",
    "v": 1,
}

# =====================================================
# 4️⃣ Cifrar payload y generar token
# =====================================================
data = json.dumps(payload).encode()
token = fernet.encrypt(data).decode()

# =====================================================
# 5️⃣ Imprimir resultados
# =====================================================
print("=" * 70)
print("✅ TOKEN DE ACCESO GENERADO CORRECTAMENTE")
print("=" * 70)
print(f"🔑 Token cifrado:\n{token}\n")
print(f"🌐 URL completa de acceso:\n{FRONTEND_URL}/?token={token}\n")
print("⏰ Vigencia: 24 horas")
print(f"📅 Generado el: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)
