"""
Registro de conectores de agente.

El proveedor se elige por configuración (`[agente] proveedor` en config.toml o la
variable de entorno AGENT_PROVIDER). Puede ser:
  - una clave de PROVEEDORES (p. ej. "foundry"), o
  - una ruta "paquete.modulo:Clase" a cualquier subclase de agentes.base.Agente,
    sin tocar este fichero.
Los módulos se importan de forma perezosa: un proveedor no necesita instalados
los SDKs de los demás.
"""

import importlib

from .base import Actividad, Agente, Aprobacion, Decision, Respuesta  # noqa: F401

PROVEEDORES = {
    "foundry": "agentes.foundry:AgenteFoundry",
}


def crear_agente(proveedor: str, **kwargs) -> Agente:
    ruta = PROVEEDORES.get(proveedor, proveedor)
    if ":" not in ruta:
        raise ValueError(
            f"Proveedor desconocido '{proveedor}'. Usa uno de {list(PROVEEDORES)} "
            "o una ruta 'modulo:Clase'."
        )
    modulo, clase = ruta.split(":", 1)
    cls = getattr(importlib.import_module(modulo), clase)
    if not issubclass(cls, Agente):
        raise TypeError(f"{ruta} no hereda de agentes.base.Agente")
    return cls(**kwargs)
