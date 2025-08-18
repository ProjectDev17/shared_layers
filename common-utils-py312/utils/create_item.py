from get_db_name, parse_body, get_table_name, get_collection import crud

# =========================
# Orquestador (handler)
# =========================
def create_item(event, _table_name_unused=None, _item_unused=None):
    try:
        db_name = get_db_name(event)
        body = parse_body(event)
        table_name = get_table_name(body)
        collection = get_collection(db_name, table_name)

        created_by_user, id_client = extract_user_info(event)
        new_item = build_new_item(body, created_by_user, id_client)

        insert_item(collection, new_item)

        return make_response(201, {
            "message": f"Registro creado con ID {new_item['_id']}",
            "item": new_item
        })

    except ClientError as ce:
        return make_response(ce.status, {"error": ce.message})
    except Exception as e:
        # Loggear e si corresponde
        return make_response(500, {"error": str(e)})