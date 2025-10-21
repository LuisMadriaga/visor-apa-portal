# generate_access_token.py
import os
import json
import time
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# 🔹 Carga las variables del .env
load_dotenv()

FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    raise ValueError("⚠️ No se encontró la variable FERNET_KEY en el entorno o .env")

# 🔹 Instancia el cifrador Fernet
fernet = Fernet(FERNET_KEY.encode())

# 🔹 RUT que quieres cifrar
rut = "9895722-7"  # cámbialo por el que desees probar

# 🔹 Crear el payload (igual que en crypto_utils.py)
payload = {
    "rut": rut,
    "ts": int(time.time()),
    "type": "access",
    "v": 1,
}

# 🔹 Convertir a JSON y cifrar
data = json.dumps(payload).encode()
token = fernet.encrypt(data).decode()

print("=" * 60)
print("✅ TOKEN DE ACCESO GENERADO")
print("=" * 60)
print(f"\n🔑 Token:\n{token}")
print(f"\n👉 URL completa de prueba:")
print(f"http://172.16.8.194:8080/?token={token}")
print(f"\n⏰ Válido por: 24 horas")
print(f"📅 Generado: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

