from database import db
from models import Inscripcion


def promover_lista_espera(categoria_id):
    """Cuando se libera un lugar en una categoría, sube al primero de la
    lista de espera (queda en `pendiente_pago`). Regresa la inscripción
    promovida o None. No hace commit: lo hace quien la llama."""
    siguiente = (
        Inscripcion.query.filter_by(categoria_id=categoria_id, estado="lista_espera")
        .order_by(Inscripcion.inscrita_en)
        .first()
    )
    if siguiente:
        siguiente.estado = "pendiente_pago"
    return siguiente
