import json
import time
from typing import Any, Dict, Tuple
from uuid6 import uuid6
from datetime import datetime
from utils.timestamp import now_ts

# Dependencia externa que ya tienes en tu proyecto
# from your_layer.mongo import get_database


# =========================
# Utilidades de respuesta
# =========================
def make_response(status: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status,
        "body": json.dumps(payload)
    }


# =========================
# Excepciones controladas
# =========================
class ClientError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status
        self.message = message


# =========================
# Helpers de extracción
# =========================
def get_db_name(event: Dict[str, Any]) -> str:
    db_name = event.get("db_name")
    if not db_name:
        raise ClientError("No se recibió db_name en el evento", status=500)
    return db_name


def parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        raise ClientError("El cuerpo de la solicitud no es un JSON válido")


def get_table_name(body: Dict[str, Any]) -> str:
    table_name = body.get("table_name")
    if not table_name:
        raise ClientError("Falta el campo 'table_name' en el cuerpo de la solicitud")
    return table_name


def get_collection(db_name: str, table_name: str):
    db = get_database(db_name)
    return db[table_name]


def extract_user_info(event: Dict[str, Any]) -> Tuple[str, str]:
    auth_result = event.get("auth_result", {}) or {}
    user_data = auth_result.get("user_data", {}) or {}
    created_by_user = user_data.get("sub") or "unknown"
    id_client = user_data.get("client_id") or "unknown"
    return created_by_user, id_client


def build_new_item(body: Dict[str, Any], created_by_user: str) -> Dict[str, Any]:
    generated_id = str(uuid6())
    ts = now_ts()

    return {
        **body,
        "_id": generated_id,
        "created_at": ts,
        "created_by": created_by_user,
        "updated_at": ts,
        "updated_by": created_by_user,
        "deleted": False,
        "status": True
    }


# =========================
# Persistencia
# =========================
def insert_item(collection, item: Dict[str, Any]) -> None:
    collection.insert_one(item)
