# test_token_flow.py
import os
import json
import time
import requests
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    raise ValueError("⚠️ No se encontró FERNET_KEY")

fernet = Fernet(FERNET_KEY.encode())

# 🔹 CONFIGURACIÓN
RUT = "9895722-7"
BASE_URL = "http://172.16.8.194:8080"

# 🔹 PASO 1: Generar token
payload = {
    "rut": RUT,
    "ts": int(time.time()),
    "type": "access",
    "v": 1,
}
data = json.dumps(payload).encode()
token = fernet.encrypt(data).decode()

print("=" * 70)
print("🔐 TEST DE TOKEN CIFRADO")
print("=" * 70)
print(f"\n1️⃣  RUT original: {RUT}")
print(f"2️⃣  Token generado: {token[:50]}...")

# 🔹 PASO 2: Validar token
print(f"\n3️⃣  Validando token en: {BASE_URL}/api/validate-access/")
try:
    response = requests.get(
        f"{BASE_URL}/api/validate-access/",
        params={"token": token},
        timeout=10
    )
    print(f"    Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"    ✅ Token válido")
        print(f"    ✅ RUT descifrado: {data.get('rut')}")
        rut_descifrado = data.get('rut')
    else:
        print(f"    ❌ Error: {response.text}")
        exit(1)
        
except Exception as e:
    print(f"    ❌ Error de conexión: {e}")
    exit(1)

# 🔹 PASO 3: Buscar informes
print(f"\n4️⃣  Buscando informes en: {BASE_URL}/api/informes-list/{rut_descifrado}/")
try:
    response = requests.get(
        f"{BASE_URL}/api/informes-list/{rut_descifrado}/",
        timeout=10
    )
    print(f"    Status: {response.status_code}")
    
    if response.status_code == 200:
        informes = response.json()
        print(f"    ✅ Informes encontrados: {len(informes)}")
        
        if informes:
            print("\n📋 DETALLES DE INFORMES:")
            for i, inf in enumerate(informes, 1):
                print(f"\n    Informe {i}:")
                print(f"      • Biopsia: {inf.get('numero_biopsia')}")
                print(f"      • Nombre: {inf.get('nombre')}")
                print(f"      • Fecha: {inf.get('fecha')}")
        else:
            print("\n    ⚠️  No hay informes para este RUT en la base de datos")
            print(f"    💡 Verifica que el RUT '{rut_descifrado}' tenga biopsias registradas")
    else:
        print(f"    ❌ Error: {response.text}")
        
except Exception as e:
    print(f"    ❌ Error de conexión: {e}")

print("\n" + "=" * 70)
print(f"\n👉 URL de prueba:\n{BASE_URL}/?token={token}")
print("\n" + "=" * 70 + "\n")