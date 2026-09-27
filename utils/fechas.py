from datetime import date, datetime, time


def parse_datetime(valor):
    """Convierte un string ISO 8601 (lo que manda el frontend en JSON) a
    datetime de Python. SQLAlchemy exige objetos datetime/date, no strings,
    sin importar si el motor es SQLite o PostgreSQL.
    Acepta None, un datetime ya parseado, o un string tipo
    "2026-11-15T07:00:00" / "2026-11-15T07:00:00Z".
    """
    if valor is None or isinstance(valor, datetime):
        return valor
    if isinstance(valor, str):
        return datetime.fromisoformat(valor.replace("Z", "+00:00"))
    raise ValueError(f"No se pudo interpretar como fecha/hora: {valor!r}")


def parse_date(valor):
    """Igual que parse_datetime, pero para columnas Date (solo día)."""
    if valor is None or isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        return date.fromisoformat(valor)
    raise ValueError(f"No se pudo interpretar como fecha: {valor!r}")


def parse_time(valor):
    """Convierte un string "HH:MM:SS" (o "HH:MM") a time de Python, para
    columnas Time como `inscripciones.tiempo_oficial`. Nota: el tipo
    `time` de Postgres no admite 24 horas o más (un ultramaratón que
    termine después de 24h no cabe aquí; es una limitación del propio
    esquema de Neon, no de este parser)."""
    if valor is None or isinstance(valor, time):
        return valor
    if isinstance(valor, str):
        partes = valor.strip().split(":")
        if len(partes) == 2:
            valor = valor + ":00"
        return time.fromisoformat(valor)
    raise ValueError(f"No se pudo interpretar como hora: {valor!r}")
