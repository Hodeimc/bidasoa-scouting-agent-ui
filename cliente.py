"""
Cliente de terminal para el agente de scouting del Bidasoa FC (Microsoft Foundry).

- Autenticación: DefaultAzureCredential (usa tu sesión de `az login`).
- Conversación multi-turno con el agente ya creado en Foundry.
- Aprobación manual de las llamadas al MCP de GitHub (human-in-the-loop).
- Descarga de los ficheros que genera el Code Interpreter (por ejemplo, el radar).

Uso:  python cliente.py      (escribe "salir" para terminar)
"""

import json
import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()
PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
AGENT_NAME = os.environ.get("AGENT_NAME", "bidasoa-scouting-agent")
CARPETA_SALIDAS = "salidas"


def pedir_aprobaciones(response):
    """Revisa la respuesta y pide confirmación para cada llamada MCP pendiente."""
    aprobaciones = []
    for item in response.output:
        if item.type == "mcp_approval_request":
            print("\n[MCP] El agente quiere usar una herramienta externa:")
            print(f"  Servidor:    {item.server_label}")
            print(f"  Herramienta: {item.name}")
            try:
                args = json.loads(item.arguments)
            except (TypeError, json.JSONDecodeError):
                args = item.arguments
            print(f"  Argumentos:  {json.dumps(args, indent=2, ensure_ascii=False)}")
            ok = input("  ¿Aprobar? (s/N): ").strip().lower() == "s"
            aprobaciones.append({
                "type": "mcp_approval_response",
                "approve": ok,
                "approval_request_id": item.id,
            })
    return aprobaciones


def descargar_ficheros(openai, response):
    """Descarga los ficheros generados por el Code Interpreter (gráficas, CSV...)."""
    for item in response.output:
        if item.type != "message":
            continue
        for content in item.content:
            for ann in getattr(content, "annotations", None) or []:
                if ann.type == "container_file_citation":
                    os.makedirs(CARPETA_SALIDAS, exist_ok=True)
                    ruta = os.path.join(CARPETA_SALIDAS, ann.filename)
                    data = openai.containers.files.content.retrieve(
                        file_id=ann.file_id, container_id=ann.container_id
                    )
                    with open(ruta, "wb") as f:
                        f.write(data.read())
                    print(f"[Fichero guardado] {ruta}")


def main():
    print("Conectando con Foundry...")
    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential) as project,
        project.get_openai_client(agent_name=AGENT_NAME) as openai,
    ):
        conversation = openai.conversations.create()
        print(f"Conectado al agente '{AGENT_NAME}'. Escribe 'salir' para terminar.\n")

        try:
            while True:
                prompt = input("Tú > ").strip()
                if not prompt:
                    continue
                if prompt.lower() in ("salir", "exit", "quit"):
                    break

                try:
                    response = openai.responses.create(
                        conversation=conversation.id, input=prompt
                    )
                    # El agente puede pedir varias aprobaciones seguidas
                    aprobaciones = pedir_aprobaciones(response)
                    while aprobaciones:
                        response = openai.responses.create(
                            conversation=conversation.id, input=aprobaciones
                        )
                        aprobaciones = pedir_aprobaciones(response)

                    print(f"\nAgente > {response.output_text}\n")
                    descargar_ficheros(openai, response)

                except Exception as e:  # que un error no tumbe la sesión
                    print(f"\n[Error] {e}\n")
        finally:
            openai.conversations.delete(conversation_id=conversation.id)
            print("Conversación cerrada.")


if __name__ == "__main__":
    main()
