# python/services/auth_service.py
import os
import bcrypt
import time
import uuid
import json
from typing import Optional, Dict, Any
from services.db import get_mongo_client
from services.db import get_database
from utils.hash_password import verify_password  # Usa tu función de la layer
from utils.jwt_token import generate_jwt, generate_jwt_refresh, decode_jwt  # Usa tu función de la layer
from utils.send_email import send_email
from utils.timestamp import add_hours_to_timestamp, now_ts
from utils.jwt_token import decode_token



def _get_user_collection(db_name):
    client = get_mongo_client()
    return client[db_name]["users"]

def hash_password(plain: str) -> bytes:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt())

def authenticate(email: str, password: str, db_name: str) -> Optional[Dict]:
    """
    Devuelve dict con usuario + tokens o None si la autenticación falla.
    """
    user = _get_user_collection(db_name).find_one({"email": email, "status": True})
    if not user:
        return None

    hashed_password = user.get("password")
    if not hashed_password:
        return None

    # Asegura que hashed_password sea bytes antes de verificar
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode("utf-8")

    if not verify_password(password, hashed_password.decode("utf-8")):
        return None

    # Genera access_token y refresh_token
    access_token = generate_jwt(str(user["_id"]), email)
    refresh_token = generate_jwt_refresh(str(user["_id"]), email)
    
    #Guarda en la base de datos el access_token y refresh_token
    _get_user_collection(db_name).update_one({"_id": user["_id"]}, {
        "$set": {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    })

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "_id": str(user['_id']),
            "email": email
        }
    }

def send_password_reset(email: str, db_name: str) -> bool:
    db = get_database(db_name)
    users = db["users"]
    user = users.find_one({"email": email, "status": True})
    if not user:
        return False
    
    new_token = str(uuid.uuid4())
    users.update_one(
        {"email": email},
        {"$set": {
            "validation_token": new_token,
            "validation_token_expires": add_hours_to_timestamp(1),  # 1h
            "validation_token_sent_at": now_ts()
        }}
    )

    body = f"Haz clic en el siguiente enlace para restablecer tu contraseña: https://digitalcrm.net/reset-password?token={new_token}"

    send_email(email, "Restablecer contraseña", body)
    return True

def refresh_access_token(refresh_token: str):
    if refresh_token == "":
        return None
    decoded = decode_jwt(refresh_token)
    if not decoded:
        return None
    access_token = generate_jwt(decoded["user_id"], decoded["email"])
    refresh_token = generate_jwt_refresh(decoded["user_id"], decoded["email"])
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "_id": decoded["user_id"],
            "email": decoded["email"]
        }
    }

def _get_header(headers: Dict[str, str], name: str, default: str = "") -> str:
    if not isinstance(headers, dict):
        return default
    # maneja mayúsculas/minúsculas de API Gateway/ALB
    return headers.get(name) or headers.get(name.lower()) or headers.get(name.capitalize()) or default

def authenticate_request(event: Dict[str, Any]) -> Dict[str, Any]:
    """Valida el token y retorna {'statusCode': 200, 'user_id': ..., 'user_data': ...} o un error."""
    headers = event.get("headers", {}) if isinstance(event, dict) else {}
    auth_header = _get_header(headers, "authorization", "")

    if not auth_header.startswith("Bearer "):
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid token format"})}

    access_token = auth_header.split(" ", 1)[1].strip()
    if not access_token:
        return {"statusCode": 400, "body": json.dumps({"error": "Missing access token"})}

    decoded_token = decode_token(access_token)
    if not decoded_token:
        return {"statusCode": 401, "body": json.dumps({"error": "Invalid access token"})}
    if isinstance(decoded_token, dict) and "statusCode" in decoded_token and decoded_token["statusCode"] != 200:
        # si tu decode_token ya devuelve errores con statusCode
        return decoded_token

    # intenta obtener el user_id con distintos esquemas de payload
    user_id = (
        (decoded_token.get("user") or {}).get("_id")
        if isinstance(decoded_token, dict) else None
    ) or (decoded_token.get("sub") if isinstance(decoded_token, dict) else None)

    if not user_id:
        return {"statusCode": 401, "body": json.dumps({"error": "Invalid token: missing user_id"})}

    # db_name desde el evento o variable de entorno
    db_name = (event.get("db_name") if isinstance(event, dict) else None) or os.getenv("MONGODB_DB_NAME")
    if not db_name:
        return {"statusCode": 500, "body": json.dumps({"error": "Missing DB name (MONGODB_DB_NAME)"})}

    db = get_database(db_name)
    users = db["users"]

    # si el _id es ObjectId válido, úsalo; si no, búscalo como string
    query_id = None
    if ObjectId and isinstance(user_id, str) and ObjectId.is_valid(user_id):
        query_id = ObjectId(user_id)
    else:
        query_id = user_id

    user_data = users.find_one({"_id": query_id})
    if not user_data:
        return {"statusCode": 404, "body": json.dumps({"error": "User not found"})}

    # valida que el token corresponda al actual guardado
    current_access_token = user_data.get("current_access_token")
    if not current_access_token or access_token != current_access_token:
        return {"statusCode": 401, "body": json.dumps({"error": "Invalid token"})}

    return {
        "statusCode": 200,
        "user_id": str(user_data.get("_id")),
        "user_data": user_data,  # si es sensible, evita devolver todo
        "access_token": access_token,
    }
