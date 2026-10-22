from math import ceil

from flask import request


def paginar_query(query, nombre_items, armar_item):
    """Paginación con el formato del resto de la API (`total`, `page`,
    `per_page`, `paginas`). `armar_item(fila)` convierte cada fila."""
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 20, type=int), 1), 100)
    total = query.count()
    filas = query.limit(per_page).offset((page - 1) * per_page).all()
    return {
        nombre_items: [armar_item(f) for f in filas],
        "total": total,
        "page": page,
        "per_page": per_page,
        "paginas": ceil(total / per_page) if total else 0,
    }
