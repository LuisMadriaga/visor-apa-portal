# backend\conexiones.py
from dotenv import load_dotenv
import pyodbc
import os

load_dotenv()

def conectar_Anatomia_Patologica():
    """Conexión a SQL Server de Anatomía Patológica (Patcore)."""
    host = os.getenv("DB_SERVER_APA")
    motor = os.getenv("DB_DRIVER_APA")
    bdname = os.getenv("DB_DATABASE_APA")
    user = os.getenv("DB_UID_APA")
    password = os.getenv("DB_PWD_APA")
    port = os.getenv("DB_PORT_APA", "1433")

    try:
        connection_string = (
            f"DRIVER={motor};"
            f"SERVER={host},{port};"
            f"DATABASE={bdname};"
            f"UID={user};"
            f"PWD={password};"
            f"TrustServerCertificate=yes;"
        )
        con = pyodbc.connect(connection_string)
        return con
    except Exception as e:
        print("❌ Error en conectar Anatomía Patológica:", e)
        return None
