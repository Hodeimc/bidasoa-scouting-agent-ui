# Agente de chat con Streamlit · Bidasoa FC Scouting

Interfaz web genérica para conversar con un agente de IA, configurada aquí para el agente de scouting **bidasoa-scouting-agent** de Microsoft Foundry. Incluye:

- Chat con historial y consultas rápidas.
- Aprobación humana de las acciones del agente en servidores MCP (p. ej. crear issues en GitHub).
- Registro de las herramientas usadas en cada respuesta.
- Radares interactivos (plotly) que el agente devuelve como bloque ```` ```radar ````.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Hodeimc/bidasoa-scouting-agent-ui)


## Probarlo en GitHub Codespaces

1. Pulsa el botón **Open in GitHub Codespaces** o ve a **Code → Codespaces → Create codespace**.
2. En la pantalla de creación, GitHub pide estos **secretos**. Si el dueño del repo ya los configuró, aparecen rellenos:

   | Secreto | Qué es |
   |---|---|
   | `PROJECT_ENDPOINT` | Endpoint del proyecto de Foundry |
   | `AGENT_NAME` | Nombre del agente (`bidasoa-scouting-agent`) |
   | `AZURE_CLIENT_ID` | appId del service principal |
   | `AZURE_TENANT_ID` | Tenant de Azure |
   | `AZURE_CLIENT_SECRET` | Secreto del service principal |

3. Espera a que termine la instalación (`pip install -r requirements.txt`). La app se arranca sola y se abre en una pestaña de vista previa (puerto **8501**). Si no se abre, ve a la pestaña **Ports** y abre el 8501.
4. Prueba una consulta rápida, por ejemplo **📋 Requisitos de invierno**. El agente tarda entre 30 y 90 segundos.

Para relanzar la app a mano:

```bash
streamlit run app.py --server.enableCORS false --server.enableXsrfProtection false
```

### Preparar el acceso (solo el dueño del proyecto de Azure)

La app se autentica con `DefaultAzureCredential`. En Codespaces no hay `az login`, así que se usa un **service principal** con permiso solo sobre el proyecto de Foundry:

```bash
# 1. Crear el service principal (devuelve appId, password y tenant)
az ad sp create-for-rbac --name bidasoa-codespaces

# 2. Darle acceso solo al proyecto de Foundry
az role assignment create --assignee <appId> --role "Azure AI User" \
  --scope <id-del-recurso-del-proyecto-foundry>
```

Después guarda los valores como secretos de Codespaces del repositorio, en **Settings → Secrets and variables → Codespaces**, o con:

```bash
gh secret set AZURE_CLIENT_ID --app codespaces
gh secret set AZURE_TENANT_ID --app codespaces
gh secret set AZURE_CLIENT_SECRET --app codespaces
gh secret set PROJECT_ENDPOINT --app codespaces
gh secret set AGENT_NAME --app codespaces
```

> ⚠️ **Seguridad:** cualquiera que abra un Codespace con estos secretos puede leerlos desde la terminal. Por eso conviene:
> - usar un repositorio **privado** e invitar solo a quien deba probarlo;
> - dar al service principal el rol mínimo (Azure AI User) limitado al proyecto;
> - rotar o borrar el secreto cuando terminen las pruebas (`az ad sp credential reset` / `az ad sp delete`).

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
