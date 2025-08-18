import time
# =========================
# Construcción del item
# =========================
def now_ts() -> int:
    # Usa timestamp en segundos; equivalente a int(datetime.now().timestamp())
    return int(time.time())

#suma horas al timestamp actual
def add_hours_to_timestamp(hours: int) -> int:
    return int(time.time()) + hours * 3600

#suma segundos al timestamp actual
def add_seconds_to_timestamp(seconds: int, base_ts: int | None = None) -> int:
    base = base_ts if base_ts is not None else now_ts()
    return base + seconds
