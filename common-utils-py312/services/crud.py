def get(event, context):
    # permission_middleware = permission_middleware(event, context)

    # if permission_middleware is not True:
    #     return permission_middleware
    
    auth_result = event.get("auth_result", {})
    user_data = auth_result.get("user_data", {})
    
    if not user_data.get("db_name"):
        return {
            "statusCode": 403,
            "body": json.dumps({"error": "Unauthorized"})
        }
    
    table_name = event.get("queryStringParameters", {}).get("table_name")

    #valida si viene el table_name
    if not table_name:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Falta el campo 'table_name' en el cuerpo de la solicitud"})
        }
    try:
        db = get_database(user_data.get("db_name"))
        collection = db[table_name]
        module_id = event.get("pathParameters", {}).get("id")
        if module_id:
            try:
                doc = collection.find_one({"_id": module_id, "deleted": False})
                if not doc:
                    return {
                        "statusCode": 404,
                        "body": json.dumps({"error": "Documento no encontrado o fue eliminado"})
                    }

                return {
                    "statusCode": 200,
                    "body": json.dumps(doc)
                }
            except Exception as e:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": f"Error al buscar el documento: {str(e)}"})
                }
        items_cursor = collection.find({"deleted": False})
        items = []
        for doc in items_cursor:
            items.append(doc)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "current_page": 1,
                "total_pages": 1,
                "total_items": len(items),
                "per_page": len(items),
                "next_page": None,
                "previous_page": None,
                "items": items
            })
        }
    except Exception as e:
            return _response(400, {"error": f"Error al buscar el documento: {str(e)}"})
  

def post(event, context):
    try:
        auth_result = event.get("auth_result", {})
        user_data = auth_result.get("user_data", {})
        
        if not user_data.get("db_name"):
            return {
                "statusCode": 403,
                "body": json.dumps({"error": "Unauthorized"})
            }

        db = get_database(user_data.get("db_name"))
        body = json.loads(event.get("body") or "{}")
        if not body or not isinstance(body, dict):
            return _response(400, {"error": "El body debe ser un JSON válido con campos a actualizar"})
        
        table_name = body.get("table_name")
        #valida si viene el table_name
        if not table_name:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Falta el campo 'table_name' en el cuerpo de la solicitud"})
            }
        collection = db[table_name]

        now_ts = int(datetime.now().timestamp())
        generated_id = str(uuid6())
        global_key_str = f"template_{generated_id}"

        #Eliminar el table_name del body
        body.pop("table_name", None)

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

        return {
            "statusCode": 201,
            "body": json.dumps({
                "message": f"Registro creado con ID {generated_id}",
                "item": new_item
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


def put(event, context):
    try:
        auth_result = event.get("auth_result", {})
        user_data = auth_result.get("user_data", {})
        
        if not user_data.get("db_name"):
            return {
                "statusCode": 403,
                "body": json.dumps({"error": "Unauthorized"})
            }

        db = get_database(user_data.get("db_name"))
        body = json.loads(event.get("body") or "{}")
        if not body or not isinstance(body, dict):
            return _response(400, {"error": "El body debe ser un JSON válido con campos a actualizar"})
        
        table_name = body.get("table_name")
        #valida si viene el table_name
        if not table_name:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Falta el campo 'table_name' en el cuerpo de la solicitud"})
            }
        collection = db[table_name]

        _id = event.get("pathParameters", {}).get("id")
        if not _id:
            return _response(400, {"error": "Falta el parámetro '_id' en la ruta"})

        # Verificar existencia y que no esté eliminado
        existing_doc = collection.find_one({"_id": _id})
        if not existing_doc:
            return _response(404, {"error": f"No se encontró {table_name} con ID {_id}"})
        if existing_doc.get("deleted", False):
            return _response(400, {"error": f"No se puede editar {table_name} con ID {_id} porque está eliminado"})

        # Validar nombre duplicado si incluye "name"
        new_name = body.get("name")
        if new_name and isinstance(new_name, str) and new_name.strip():
            new_name = new_name.strip()
            if collection.find_one({
                "name": {"$regex": f"^{new_name}$", "$options": "i"},
                "_id": {"$ne": _id},
                "deleted": False
            }):
                return _response(409, {"error": f"Ya existe otra {table_name} con el nombre '{new_name}'"})
            body["name"] = new_name

        # Preparar y aplicar la actualización
        body["updated_at"] = int(datetime.now().timestamp())
        body["updated_by"] = user_data.get("_id")

        result = collection.update_one(
            {"_id": _id},
            {"$set": body}
        )

        if result.matched_count == 0:
            return _response(404, {"error": f"No se encontró {table_name} con ID {_id}"})

        updated_doc = collection.find_one({"_id": _id})
        updated_doc["_id"] = str(updated_doc["_id"])

        return _response(200, {
            "message": f"{table_name} {_id} actualizada correctamente",
            "item": updated_doc
        })

    except Exception as e:
        return _response(500, {"error": str(e)})


def delete(event, context):
    """
    Lógica para DELETE  (borrado lógico).
    Cambia el campo 'deleted' a True y actualiza 'updated_at' y 'updated_by'.
    """
    try:
        auth_result = event.get("auth_result", {})
        user_data = auth_result.get("user_data", {})
        
        if not user_data.get("db_name"):
            return {
                "statusCode": 403,
                "body": json.dumps({"error": "Unauthorized"})
            }

        db = get_database(user_data.get("db_name"))
        body = json.loads(event.get("body") or "{}")
        if not body or not isinstance(body, dict):
            return _response(400, {"error": "El body debe ser un JSON válido con campos a actualizar"})
        
        table_name = body.get("table_name")
        #valida si viene el table_name
        if not table_name:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Falta el campo 'table_name' en el cuerpo de la solicitud"})
            }
        collection = db[table_name]

        _id = event.get("pathParameters", {}).get("id")
        if not _id:
            return _response(400, {"error": "Falta el parámetro '_id' en la ruta"})

        # Verificar existencia y que no esté eliminado
        existing_doc = collection.find_one({"_id": _id})
        if not existing_doc:
            return _response(404, {"error": f"No se encontró {table_name} con ID {_id}"})
        if existing_doc.get("deleted", False):
            return _response(400, {"error": f"No se puede editar {table_name} con ID {_id} porque está eliminado"})

        # Actualizar documento: borrado lógico
        result = collection.update_one(
            {"_id": _id},
            {
                "$set": {
                    "deleted": True,
                    "updated_at": int(datetime.now().timestamp()),
                    "updated_by": user_data.get("_id")
                }
            }
        )

        if result.matched_count == 0:
            return _response(404, {"error": f"No se encontró la {table_name} con ese ID para eliminar"})

        return _response(200, {"message": f"{table_name} {_id} marcada como eliminada"})

    except Exception as e:
        return _response(500, {"error": str(e)})


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "body": json.dumps(body_dict)
    }
