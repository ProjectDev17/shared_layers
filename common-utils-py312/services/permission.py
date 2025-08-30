def permission_middleware(event, context):
    auth_result = event.get("auth_result", {})
    user_data = auth_result.get("user_data", {})
    if user_data.get("email_verified") != "True":
        return {
            "statusCode": 403,
            "body": json.dumps({
                "message": "Email not verified"
            })
        }
    if user_data.get("deleted") == "True":
        return {
            "statusCode": 403,
            "body": json.dumps({
                "message": "User does not have admin role"
            })
        }
    return True
