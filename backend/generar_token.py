import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# 🔹 Carga las variables del .env (para usar el mismo FERNET_KEY)
load_dotenv()

FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    raise ValueError("⚠️ No se encontró la variable FERNET_KEY en el entorno o .env")

# 🔹 Instancia el cifrador Fernet
fernet = Fernet(FERNET_KEY.encode())

# 🔹 RUT que quieres cifrar
rut = "9895722-7"  # cámbialo por el que desees probar

# 🔹 Generar el token
token = fernet.encrypt(rut.encode()).decode()

print("✅ Token generado con éxito:")
print(token)
print("\n👉 URL completa de prueba:")
print(f"http://172.16.8.194:8080/?token={token}")
