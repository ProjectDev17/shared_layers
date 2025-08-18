import jwt
import os
from utils.timestamp import now_ts, add_seconds_to_timestamp
import json

JWT_SECRET = os.getenv("JWT_SECRET", "sCEVRRjfDzUi8Ve7sCEVRRjfDzUi8Ve7sCEVRRjfDzUi8Ve7sCEVRRjfDzUi8Ve7")     # usa Secrets Manager
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

def decode_token(access_token):
    try:
        # Decodificar el token para obtener el payload (incluye user_id y otros datos)
        decoded_token = jwt.decode(access_token, SECRET_KEY, algorithms=['HS256'])  # Ajusta el algoritmo si usas otro
        return decoded_token
    except jwt.ExpiredSignatureError:
        # El token ha expirado
        return {
            "statusCode": 401,
            "body": json.dumps({"message": "Token has expired"})
        }
        
    except jwt.InvalidTokenError:
        # Token inválido (firma incorrecta, formato inválido, etc.)
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Invalid token."})
        }
    except Exception as e:
        print(str(e), 'decode_token')
        # Otros errores inesperados
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"Error decoding token: {str(e)}"})
        }
