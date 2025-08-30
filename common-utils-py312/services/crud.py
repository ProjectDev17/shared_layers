import json
from datetime import datetime
from uuid6 import uuid6

from utils.timestamp import now_ts
from utils.crud import _resp, _get_user_db_or_403, _parse_body_or_400, _require_table_name_from_query, _require_table_name_from_body, _get_db_and_collection, _require_path_id, _find_existing_or_error

# =========================
# Handlers
# =========================
def get(event, context):
    try:
        user_data, err = _get_user_db_or_403(event)
        if err: 
            return err

        table_name, err = _require_table_name_from_query(event)
        if err: 
            return err

        db, collection = _get_db_and_collection(user_data["db_name"], table_name)
        module_id = (event.get("pathParameters") or {}).get("id")

        if module_id:
            doc = collection.find_one({"_id": module_id, "deleted": False})
            if not doc:
                return _resp(404, {"error": "Documento no encontrado o fue eliminado"})
            return _resp(200, doc)

        items = list(collection.find({"deleted": False}))
        total = len(items)
        return _resp(200, {
            "current_page": 1,
            "total_pages": 1,
            "total_items": total,
            "per_page": total,
            "next_page": None,
            "previous_page": None,
            "items": items
        })

    except Exception as e:
        return _resp(400, {"error": f"Error al buscar el documento: {str(e)}"})

def post(event, context):
    try:
        user_data, err = _get_user_db_or_403(event)
        if err: 
            return err

        body, err = _parse_body_or_400(event)
        if err: 
            return err

        table_name, err = _require_table_name_from_body(body)
        if err: 
            return err

        db, collection = _get_db_and_collection(user_data["db_name"], table_name)

        # limpiar body de metacampos reservados
        body = dict(body)  # copia
        body.pop("table_name", None)

        now_ts = now_ts()
        generated_id = str(uuid6())

        new_item = {
            **body,
            "_id": generated_id,
            "created_at": now_ts,
            "created_by": user_data.get("_id"),
            "updated_at": now_ts,
            "updated_by": user_data.get("_id"),
            "deleted": False,
            "status": True,
        }

        collection.insert_one(new_item)
        return _resp(201, {
            "message": f"Registro creado con ID {generated_id}",
            "item": new_item
        })

    except Exception as e:
        return _resp(500, {"error": str(e)})


def put(event, context):
    try:
        user_data, err = _get_user_db_or_403(event)
        if err: 
            return err

        body, err = _parse_body_or_400(event)
        if err: 
            return err

        table_name, err = _require_table_name_from_body(body)
        if err: 
            return err

        _id, err = _require_path_id(event)
        if err: 
            return err

        db, collection = _get_db_and_collection(user_data["db_name"], table_name)

        existing, err = _find_existing_or_error(collection, _id, allow_deleted=False, noun=table_name)
        if err: 
            return err

        # Validación de nombre duplicado (si viene name)
        if isinstance(body.get("name"), str) and body["name"].strip():
            new_name = body["name"].strip()
            dup = collection.find_one({
                "name": {"$regex": f"^{new_name}$", "$options": "i"},
                "_id": {"$ne": _id},
                "deleted": False
            })
            if dup:
                return _resp(409, {"error": f"Ya existe otra {table_name} con el nombre '{new_name}'"})
            body["name"] = new_name

        # Metadatos de actualización
        body = dict(body)  # copia
        body.pop("table_name", None)
        body["updated_at"] = now_ts()
        body["updated_by"] = user_data.get("_id")

        result = collection.update_one({"_id": _id}, {"$set": body})
        if result.matched_count == 0:
            return _resp(404, {"error": f"No se encontró {table_name} con ID {_id}"})

        updated_doc = collection.find_one({"_id": _id})
        return _resp(200, {
            "message": f"{table_name} {_id} actualizada correctamente",
            "item": updated_doc
        })

    except Exception as e:
        return _resp(500, {"error": str(e)})


def delete(event, context):
    """Borrado lógico: set deleted=True + metadatos de update."""
    try:
        user_data, err = _get_user_db_or_403(event)
        if err: 
            return err

        body, err = _parse_body_or_400(event)
        if err: 
            return err

        table_name, err = _require_table_name_from_body(body)
        if err: 
            return err

        _id, err = _require_path_id(event)
        if err: 
            return err

        db, collection = _get_db_and_collection(user_data["db_name"], table_name)

        existing, err = _find_existing_or_error(collection, _id, allow_deleted=False, noun=table_name)
        if err: 
            return err

        result = collection.update_one(
            {"_id": _id},
            {"$set": {
                "deleted": True,
                "updated_at": now_ts(),
                "updated_by": user_data.get("_id")
            }}
        )
        if result.matched_count == 0:
            return _resp(404, {"error": f"No se encontró la {table_name} con ese ID para eliminar"})

        return _resp(200, {"message": f"{table_name} {_id} marcada como eliminada"})

    except Exception as e:
        return _resp(500, {"error": str(e)})
