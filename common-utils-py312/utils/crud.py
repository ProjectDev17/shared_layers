import json
import time
from typing import Any, Dict, Tuple
from uuid6 import uuid6
from datetime import datetime
from utils.timestamp import now_ts

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

# =========================
# Helpers (DRY)
# =========================
def _resp(status: int, payload):
    # Respuesta tipo Lambda Proxy Integration
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload, default=str)
    }

def _get_user_db_or_403(event):
    auth_result = (event or {}).get("auth_result", {})
    user_data = auth_result.get("user_data", {})
    db_name = user_data.get("db_name")
    if not db_name:
        return None, _resp(403, {"error": "Unauthorized"})
    return user_data, None


def _parse_body_or_400(event):
    """Intenta cargar body JSON como dict ({} si vacío)."""
    try:
        body = json.loads(event.get("body") or "{}")
        if not isinstance(body, dict):
            return None, _resp(400, {"error": "El body debe ser un JSON válido con campos a actualizar"})
        return body, None
    except Exception:
        return None, _resp(400, {"error": "Body inválido. Debe ser JSON"})

def _require_table_name_from_query(event):
    qsp = (event or {}).get("queryStringParameters") or {}
    table_name = qsp.get("table_name")
    if not table_name:
        return None, _resp(400, {"error": "Falta el campo 'table_name' en query"})
    return table_name, None

def _require_table_name_from_body(body):
    table_name = (body or {}).get("table_name")
    if not table_name:
        return None, _resp(400, {"error": "Falta el campo 'table_name' en el cuerpo de la solicitud"})
    return table_name, None

def _get_db_and_collection(db_name: str, table_name: str):
    db = get_database(db_name)
    collection = db[table_name]
    # >>> DEVUELVE el objeto db, no el nombre
    return db, collection

def _require_path_id(event):
    _id = (event.get("pathParameters") or {}).get("id")
    if not _id:
        return None, _resp(400, {"error": "Falta el parámetro '_id' en la ruta"})
    return _id, None

def _find_existing_or_error(collection, _id, allow_deleted=False, noun="registro"):
    existing = collection.find_one({"_id": _id})
    if not existing:
        return None, _resp(404, {"error": f"No se encontró {noun} con ID {_id}"})
    if not allow_deleted and existing.get("deleted", False):
        return None, _resp(400, {"error": f"No se puede operar sobre {noun} con ID {_id} porque está eliminado"})
    return existing, None