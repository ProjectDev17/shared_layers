import jwt
import os
from utils.timestamp import now_ts, add_seconds_to_timestamp

JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret")     # usa Secrets Manager
JWT_EXP_SECS = int(os.getenv("JWT_EXP_SECS", "3600"))  # 1 h por defecto

def generate_jwt(user_id: str, email: str) -> str:
    issued_at = now_ts()                          # ✅ llama la función
    payload = {
        "user_id": user_id,
        "email": email,
        "iat": issued_at,                        # ✅ int
        "exp": issued_at + JWT_EXP_SECS,         # ✅ int + int
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def generate_jwt_refresh(user_id: str, email: str) -> str:
    issued_at = now_ts()                          # ✅ llama la función
    payload = {
        "user_id": user_id,
        "email": email,
        "iat": issued_at,
        "exp": add_seconds_to_timestamp(JWT_EXP_SECS, issued_at),   # ✅ tu helper recibe 2 args
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_jwt(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None