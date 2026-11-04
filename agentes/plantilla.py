"""
Plantilla para añadir un proveedor nuevo (Claude, OpenAI directo, LangGraph, uno propio...).

Pasos:
  1. Copia este fichero (p. ej. agentes/mi_proveedor.py) e implementa los métodos.
  2. En config.toml pon:   [agente] proveedor = "agentes.mi_proveedor:AgenteMiProveedor"
     (o añade una clave corta en PROVEEDORES de agentes/__init__.py).
  3. Lee claves/endpoints de variables de entorno (.env), nunca del código.

La interfaz solo espera objetos de agentes.base:
  - enviar(...) y responder_aprobaciones(...) devuelven una Respuesta.
  - Si la Respuesta trae `aprobaciones`, la interfaz muestra las tarjetas y luego
    llama a responder_aprobaciones con una lista de Decision.
  - `ficheros` son rutas locales ya descargadas (guárdalas en self.carpeta_salidas);
    las imágenes se muestran como figuras.
  - `actividad` es la lista de herramientas usadas en la ronda (para el registro).
  - Si el agente escribe bloques de gráfico (```radar {...}```), la interfaz los
    dibuja sola: no hay que hacer nada aquí.
"""

from .base import Agente, Decision, Respuesta


class AgenteMiProveedor(Agente):

    def __init__(self, ajustes, carpeta_salidas, log):
        super().__init__(ajustes, carpeta_salidas, log)
        # self.client = MiSDK(api_key=os.environ["MI_API_KEY"])
        # self.historial = {}   # conv_id -> mensajes, si el proveedor no guarda estado
        raise NotImplementedError("Plantilla: implementa el conector")

    def nueva_conversacion(self) -> str:
        # Crear la conversación en el proveedor, o un uuid local si no las gestiona.
        raise NotImplementedError

    def enviar(self, conv_id: str, texto: str) -> Respuesta:
        # Llamar al modelo/agente y traducir su salida a Respuesta(texto, aprobaciones, actividad, ficheros).
        raise NotImplementedError

    def responder_aprobaciones(self, conv_id: str, decisiones: list[Decision]) -> Respuesta:
        # Enviar las decisiones al proveedor (o ejecutar/omitir la herramienta tú mismo) y continuar.
        raise NotImplementedError
