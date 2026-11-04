"""
Conector para agentes de Microsoft Foundry (cliente OpenAI del proyecto).

Mismos patrones que cliente.py: conversations.create / responses.create,
aprobaciones MCP (mcp_approval_request / mcp_approval_response) y ficheros del
Code Interpreter (container_file_citation + barrido de containers).

Variables de entorno: PROJECT_ENDPOINT y AGENT_NAME.
"""

import base64
import os
import re

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from .base import Actividad, Agente, Aprobacion, Decision, Respuesta

RE_SANDBOX_IMG = re.compile(r"!\[[^\]]*\]\(sandbox:/mnt/data/[^)]*\)")
RE_SANDBOX_LINK = re.compile(r"\[([^\]]*)\]\(sandbox:/mnt/data/[^)]*\)")
RE_SANDBOX_BARE = re.compile(r"sandbox:/mnt/data/\S+")


class AgenteFoundry(Agente):

    def __init__(self, ajustes, carpeta_salidas, log):
        super().__init__(ajustes, carpeta_salidas, log)
        endpoint = os.environ.get("PROJECT_ENDPOINT")
        self.agent_name = os.environ.get("AGENT_NAME") or self.ajustes.get("agent_name")
        faltan = [n for n, v in (("PROJECT_ENDPOINT", endpoint), ("AGENT_NAME", self.agent_name)) if not v]
        if faltan:
            raise RuntimeError(
                f"Faltan variables de entorno: {', '.join(faltan)}. En local, ponlas en el fichero .env; "
                "en GitHub Codespaces, como secretos de Codespaces (ver README)."
            )
        # DefaultAzureCredential usa AZURE_CLIENT_ID/AZURE_TENANT_ID/AZURE_CLIENT_SECRET si
        # existen (service principal, p. ej. en Codespaces) o la sesión de `az login`.
        credential = DefaultAzureCredential()
        project = AIProjectClient(endpoint=endpoint, credential=credential)
        self.client = project.get_openai_client(agent_name=self.agent_name)
        self._estado = {}   # conv_id -> {"containers": [...], "descargados": set()}

    @property
    def etiqueta(self):
        return self.agent_name

    # --- Conversación ---
    def nueva_conversacion(self):
        conv_id = self.client.conversations.create().id
        self._estado[conv_id] = {"containers": [], "descargados": set()}
        return conv_id

    def cerrar_conversacion(self, conv_id):
        self._estado.pop(conv_id, None)
        self.client.conversations.delete(conversation_id=conv_id)

    def enviar(self, conv_id, texto):
        return self._ronda(conv_id, texto)

    def responder_aprobaciones(self, conv_id, decisiones: list[Decision]):
        entrada = [{"type": "mcp_approval_response", "approve": d.aprobar,
                    "approval_request_id": d.aprobacion_id} for d in decisiones]
        return self._ronda(conv_id, entrada)

    def postprocesar_texto(self, texto, hay_figuras):
        """Sustituye los enlaces a sandbox:/mnt/data/... (no funcionan en el navegador)."""
        nota = "(ver figura abajo)" if hay_figuras else "(fichero generado en el sandbox del agente)"
        texto = RE_SANDBOX_IMG.sub(nota, texto)
        texto = RE_SANDBOX_LINK.sub(lambda m: f"{m.group(1)} {nota}", texto)
        return RE_SANDBOX_BARE.sub(nota, texto)

    # --- Internos ---
    def _estado_de(self, conv_id):
        return self._estado.setdefault(conv_id, {"containers": [], "descargados": set()})

    def _ronda(self, conv_id, entrada):
        response = self.client.responses.create(conversation=conv_id, input=entrada)
        estado = self._estado_de(conv_id)
        actividad = self._actividad(response)
        ficheros = self._descargar_ficheros(response, estado)
        aprobaciones = self._aprobaciones(response)
        if not aprobaciones:  # fin del turno: barrer los containers vistos
            for ruta in self._barrer_containers(estado):
                if ruta not in ficheros:
                    ficheros.append(ruta)
            estado["containers"] = []
        return Respuesta(texto=response.output_text or "", aprobaciones=aprobaciones,
                         actividad=actividad, ficheros=ficheros)

    def _actividad(self, response):
        """Registra los tool calls de la ronda (las aprobaciones las registra la interfaz al decidir)."""
        actividad = []
        for item in response.output:
            tipo = getattr(item, "type", "desconocido")
            if tipo in ("message", "reasoning", "mcp_approval_request", "mcp_approval_response"):
                continue
            estado = f"⚙️ {getattr(item, 'status', None) or 'ejecutada'}"
            if tipo == "mcp_call":
                error = getattr(item, "error", None)
                actividad.append(Actividad(
                    self.icono("mcp", "🔌"),
                    f"{self.nombre_servidor(getattr(item, 'server_label', 'MCP'))} · {getattr(item, 'name', '?')}",
                    f"⚠️ error: {error}" if error else "⚙️ ejecutada",
                    self.parse_args(getattr(item, "arguments", None))))
            elif tipo == "mcp_list_tools":
                tools = [getattr(t, "name", "?") for t in (getattr(item, "tools", None) or [])]
                actividad.append(Actividad(
                    self.icono("listar", "📚"),
                    f"{self.nombre_servidor(getattr(item, 'server_label', 'MCP'))} · listar herramientas",
                    "⚙️ ejecutada", {"herramientas": tools} if tools else None))
            elif tipo == "code_interpreter_call":
                code = getattr(item, "code", None)
                actividad.append(Actividad(self.icono("codigo", "🐍"), "Code Interpreter", estado,
                                           {"code": code} if code else None))
            elif "search" in tipo:
                queries = getattr(item, "queries", None) or getattr(item, "query", None)
                actividad.append(Actividad(self.icono("busqueda", "🔎"), f"Búsqueda en documentos ({tipo})",
                                           estado, {"consultas": queries} if queries else None))
            else:
                actividad.append(Actividad(self.icono("otra", "🛠️"), getattr(item, "name", None) or tipo,
                                           estado, self.parse_args(getattr(item, "arguments", None))))
        return actividad

    def _aprobaciones(self, response):
        return [
            Aprobacion(id=item.id,
                       servidor=self.nombre_servidor(getattr(item, "server_label", "MCP")),
                       herramienta=getattr(item, "name", "?"),
                       argumentos=self.parse_args(getattr(item, "arguments", None)))
            for item in response.output
            if getattr(item, "type", None) == "mcp_approval_request"
        ]

    def _guardar(self, file_id, container_id, nombre, estado):
        """Descarga un fichero del container (una sola vez por file_id)."""
        os.makedirs(self.carpeta_salidas, exist_ok=True)
        ruta = os.path.join(self.carpeta_salidas, f"{file_id}_{os.path.basename(nombre or file_id)}")
        if not os.path.exists(ruta):
            data = self.client.containers.files.content.retrieve(file_id=file_id, container_id=container_id)
            with open(ruta, "wb") as f:
                f.write(data.read())
            self.log.info("Fichero descargado: %s (container %s)", ruta, container_id)
        estado["descargados"].add(file_id)
        return ruta

    def _descargar_ficheros(self, response, estado):
        """Citas container_file_citation e imágenes en los outputs del Code Interpreter."""
        def anotar(cid):
            if cid and cid not in estado["containers"]:
                estado["containers"].append(cid)

        rutas = []
        for item in response.output:
            tipo = getattr(item, "type", None)
            if tipo == "message":
                for content in getattr(item, "content", None) or []:
                    for ann in getattr(content, "annotations", None) or []:
                        if getattr(ann, "type", None) != "container_file_citation":
                            continue
                        anotar(getattr(ann, "container_id", None))
                        try:
                            ruta = self._guardar(ann.file_id, ann.container_id,
                                                 getattr(ann, "filename", None), estado)
                            if ruta not in rutas:
                                rutas.append(ruta)
                        except Exception as e:
                            self.log.warning("No se pudo descargar %s: %s", getattr(ann, "file_id", "?"), e)
            elif tipo == "code_interpreter_call":
                anotar(getattr(item, "container_id", None))
                for i, out in enumerate(getattr(item, "outputs", None) or []):
                    url = getattr(out, "url", None) or ""
                    if getattr(out, "type", None) == "image" and url.startswith("data:image"):
                        try:
                            cabecera, b64 = url.split(",", 1)
                            ext = cabecera.split("/")[1].split(";")[0].replace("jpeg", "jpg")
                            os.makedirs(self.carpeta_salidas, exist_ok=True)
                            ruta = os.path.join(self.carpeta_salidas, f"{getattr(item, 'id', 'ci')}_{i}.{ext}")
                            if not os.path.exists(ruta):
                                with open(ruta, "wb") as f:
                                    f.write(base64.b64decode(b64))
                                self.log.info("Imagen descargada (output Code Interpreter): %s", ruta)
                            if ruta not in rutas:
                                rutas.append(ruta)
                        except Exception as e:
                            self.log.warning("No se pudo guardar la imagen del Code Interpreter: %s", e)
        return rutas

    def _barrer_containers(self, estado):
        """Lista cada container visto en el turno y descarga los .png pendientes."""
        rutas = []
        for cid in estado["containers"]:
            try:
                ficheros = list(self.client.containers.files.list(container_id=cid))
            except Exception as e:
                self.log.warning("No se pudieron listar los ficheros del container %s: %s", cid, e)
                continue
            if not ficheros:
                self.log.info("El container %s no devolvió ficheros", cid)
                continue
            for f in ficheros:
                path = getattr(f, "path", None) or ""
                if not path.lower().endswith(".png") or f.id in estado["descargados"]:
                    continue
                try:
                    rutas.append(self._guardar(f.id, cid, path, estado))
                except Exception as e:
                    self.log.warning("No se pudo descargar %s del container %s: %s", path, cid, e)
        return rutas
