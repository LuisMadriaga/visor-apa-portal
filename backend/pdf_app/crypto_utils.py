# crypto_utils.py
import json, time
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

TTL_SECONDS = 24 * 60 * 60  # 24h

def _fernet():
    return Fernet(settings.FERNET_KEY.encode() if isinstance(settings.FERNET_KEY, str) else settings.FERNET_KEY)

def make_pdf_token(rut: str, numero_biopsia: str) -> str:
    payload = {
        "rut": rut,
        "num": numero_biopsia,
        "ts": int(time.time()),
        "v": 1,
    }
    data = json.dumps(payload).encode()
    return _fernet().encrypt(data).decode()

def parse_pdf_token(token: str) -> dict:
    data = _fernet().decrypt(token.encode(), ttl=TTL_SECONDS)
    return json.loads(data.decode())
