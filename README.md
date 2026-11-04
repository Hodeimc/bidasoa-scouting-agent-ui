# Agente de chat con Streamlit · Bidasoa FC Scouting

Interfaz web genérica para conversar con un agente de IA, configurada aquí para el agente de scouting **bidasoa-scouting-agent** de Microsoft Foundry. Incluye:

- Chat con historial y consultas rápidas.
- Aprobación humana de las acciones del agente en servidores MCP (p. ej. crear issues en GitHub).
- Registro de las herramientas usadas en cada respuesta.
- Radares interactivos (plotly) que el agente devuelve como bloque ```` ```radar ````.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Hodeimc/bidasoa-scouting-agent-ui)


## Probarlo en GitHub Codespaces

No hay que configurar nada: el endpoint y el agente ya están en `config.toml`. Solo hace falta iniciar sesión con una cuenta de Azure que tenga acceso al proyecto de Foundry.

1. Pulsa el botón **Open in GitHub Codespaces** (o **Code → Codespaces → Create codespace**) y espera a que termine la instalación (2-3 minutos la primera vez).
2. En la **terminal** aparece automáticamente un recuadro *"🔐 Inicia sesión en Azure"* con un enlace y un código. Abre el enlace, escribe el código e inicia sesión con tu cuenta.
3. **Recarga la app** (se abre sola en una pestaña nueva del navegador; si no, pestaña **Ports** → puerto **8501** → icono 🌐) y prueba una consulta rápida, por ejemplo **📋 Requisitos de invierno**. El agente tarda entre 30 y 90 segundos.

Si cerraste la terminal o el código caducó: `bash .devcontainer/login-azure.sh`. Si tu cuenta tiene varios tenants: `az login --use-device-code --tenant <tenant-del-proyecto>`.

Para relanzar la app a mano:

```bash
streamlit run app.py --server.enableCORS false --server.enableXsrfProtection false
```

### Dar acceso a una persona (solo el dueño del proyecto de Azure)

Asigna a su cuenta el rol **Azure AI User** limitado al proyecto de Foundry:

```bash
# ID del proyecto: id del recurso de Foundry + /projects/<nombre-del-proyecto>
az cognitiveservices account list --query "[].{nombre:name, id:id}" -o table

az role assignment create --assignee <correo-de-la-persona> --role "Azure AI User" \
  --scope "<id-del-recurso>/projects/<nombre-del-proyecto>"
```

Para quitarle el acceso: `az role assignment delete --assignee <correo> --role "Azure AI User" --scope "<mismo-scope>"`.

> Para usar otro proyecto o agente, cambia `project_endpoint` y `agent_name` en `config.toml`, o define las variables `PROJECT_ENDPOINT` / `AGENT_NAME`, que tienen prioridad.
>
> Alternativa sin login: un *service principal*. Define `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` y `AZURE_CLIENT_SECRET` como secretos de Codespaces y `DefaultAzureCredential` los usará en lugar de `az login`. Ojo: quien abra el Codespace podrá leer ese secreto.

## Ejecutar en local

```bash
pip install -r requirements.txt
cp env.example .env          # y rellena PROJECT_ENDPOINT y AGENT_NAME
az login                     # o define las variables AZURE_* de un service principal
streamlit run app.py         # http://localhost:8501
```

`cliente.py` es el cliente de terminal de referencia: `python cliente.py`.

## Reutilizarlo con otro agente o tema

El código es genérico:

- **`config.toml`**: marca, logo, colores, textos, consultas rápidas, nombres de servidores MCP y tipos de gráfico. Para otro caso de uso, cambia solo este fichero.
- **`agentes/`**: un conector por proveedor. `foundry.py` es el actual. Para otro agente (Claude, OpenAI, uno propio…), copia `agentes/plantilla.py`, implementa `nueva_conversacion`, `enviar` y `responder_aprobaciones`, y en `config.toml` pon `proveedor = "agentes.mi_modulo:MiClase"`.
- **`graficos.py`**: bloques de gráfico en la respuesta del agente (`radar`, `barras`). Se pueden añadir tipos nuevos.
