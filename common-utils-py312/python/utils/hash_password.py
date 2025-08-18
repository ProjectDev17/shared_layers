import bcrypt

def hash_password(password: str) -> str:
    """
    Hashea una contraseña usando bcrypt.
    Devuelve el hash como string utf-8.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(password: str, hashed: str | bytes) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con un hash bcrypt.
    """
    if isinstance(hashed, str):
        hashed = hashed.encode("utf-8")
    return bcrypt.checkpw(password.encode("utf-8"), hashed)
