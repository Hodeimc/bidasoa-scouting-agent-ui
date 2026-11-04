"""
Contrato neutro entre la interfaz y cualquier agente.

La interfaz (app.py) solo conoce estas clases. Cada proveedor (Foundry, Claude,
OpenAI, un agente propio...) implementa `Agente` en su propio módulo y traduce
su SDK a estos objetos.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Aprobacion:
    """Una acción que el agente quiere ejecutar y necesita confirmación humana."""
    id: str
    servidor: str          # nombre legible del servidor/herramienta externa
    herramienta: str       # nombre de la herramienta que quiere usar
    argumentos: Any = None


@dataclass
class Actividad:
    """Una línea del registro de herramientas usadas durante un turno."""
    icono: str
    nombre: str
    estado: str
    args: Any = None


@dataclass
class Decision:
    """Respuesta humana a una `Aprobacion`."""
    aprobacion_id: str
    aprobar: bool


@dataclass
class Respuesta:
    """Resultado de una ronda. Si `aprobaciones` no está vacía, el turno sigue abierto."""
    texto: str = ""
    aprobaciones: list[Aprobacion] = field(default_factory=list)
    actividad: list[Actividad] = field(default_factory=list)
    ficheros: list[str] = field(default_factory=list)   # rutas locales ya descargadas


class Agente(ABC):
    """Interfaz que debe implementar cada proveedor."""

    def __init__(self, ajustes: dict, carpeta_salidas: str, log: logging.Logger):
        self.ajustes = ajustes or {}
        self.carpeta_salidas = carpeta_salidas
        self.log = log

    # --- Identidad (para la interfaz) ---
    @property
    def etiqueta(self) -> str:
        """Texto corto que identifica al agente (p. ej. su nombre o modelo)."""
        return self.ajustes.get("etiqueta", self.__class__.__name__)

    # --- Conversación ---
    @abstractmethod
    def nueva_conversacion(self) -> str:
        """Crea una conversación y devuelve su id."""

    def cerrar_conversacion(self, conv_id: str) -> None:
        """Libera la conversación en el proveedor (opcional)."""

    @abstractmethod
    def enviar(self, conv_id: str, texto: str) -> Respuesta:
        """Envía un mensaje del usuario."""

    @abstractmethod
    def responder_aprobaciones(self, conv_id: str, decisiones: list[Decision]) -> Respuesta:
        """Envía las decisiones humanas sobre las aprobaciones pendientes."""

    def postprocesar_texto(self, texto: str, hay_figuras: bool) -> str:
        """Ajustes del texto propios del proveedor (enlaces internos, etc.)."""
        return texto

    # --- Utilidades comunes ---
    def nombre_servidor(self, servidor: str) -> str:
        return self.ajustes.get("servidores", {}).get(str(servidor).lower(), str(servidor))

    def icono(self, clave: str, defecto: str = "🛠️") -> str:
        return self.ajustes.get("iconos", {}).get(clave, defecto)

    @staticmethod
    def parse_args(raw):
        if raw is None or isinstance(raw, (dict, list)):
            return raw
        try:
            return json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return raw
