# App de chat con agente (configurada para Bidasoa FC · Scouting en Microsoft Foundry)

Interfaz web en Streamlit **genérica**: el código no sabe nada del caso de uso ni del proveedor. Todo lo específico está en `config.toml` (marca, textos, prompts, colores) y en un conector de `agentes/` (proveedor). Configuración actual: agente de Foundry `bidasoa-scouting-agent`. El usuario se comunica en español: responde en español.

## Estructura
- `app.py`: interfaz genérica (chat, aprobaciones, figuras, actividad). Sin imports de SDKs de proveedor ni textos del dominio.
- `config.toml`: marca/logo, colores, tipografía, bienvenida, consultas rápidas, proveedor (`[agente] proveedor`), nombres legibles de servidores MCP, iconos, bloques de gráfico y paleta, carpeta de salidas, nombre del logger.
- `agentes/base.py`: contrato neutro (`Agente`, `Respuesta`, `Aprobacion`, `Actividad`, `Decision`).
- `agentes/__init__.py`: registro `crear_agente()`; acepta una clave (`foundry`) o `"modulo:Clase"`.
- `agentes/foundry.py`: conector Foundry (todo el código del SDK Azure/OpenAI vive aquí).
- `agentes/plantilla.py`: esqueleto documentado para añadir otro proveedor.
- `graficos.py`: bloques de gráfico en la respuesta (```radar {json}```) → plotly. Tipos: `radar`, `barras`.
- `cliente.py`: cliente de terminal de referencia. **NO modificar.**
- `.env`: `PROJECT_ENDPOINT`, `AGENT_NAME` (y opcional `AGENT_PROVIDER`). **NO modificar ni mostrar su contenido.**
- `salidas/`: ficheros descargados del agente (ignorado por git).
- `.devcontainer/devcontainer.json`: entorno de GitHub Codespaces (Python 3.12, instala requirements y arranca la app en el puerto 8501).
- `README.md`: instrucciones para Codespaces, service principal y uso local.
- Git: `.env`, `salidas/` y `__pycache__/` están en `.gitignore`. Hacer commits/push solo si el usuario lo pide, y nunca subir `.env` ni secretos.

## GitHub Codespaces
- Sin configuración: `project_endpoint` y `agent_name` están en `[agente]` de `config.toml` (decisión del usuario: no son secretos). Las variables de entorno `PROJECT_ENDPOINT`/`AGENT_NAME` tienen prioridad.
- Autenticación: al abrir el Codespace, `postAttachCommand` lanza a la vez la app y `.devcontainer/login-azure.sh`, que hace `az login --use-device-code` si no hay sesión. Después basta con recargar la app. La cuenta necesita un rol con acceso a los agentes del proyecto (p. ej. **Azure AI User**). El destinatario previsto es el profesor, administrador del recurso.
- Alternativa opcional: service principal (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`); `DefaultAzureCredential` lo usa sin cambios de código.
- Sin sesión, el conector Foundry muestra "No hay sesión de Azure…" en la página. El cliente no cachea el fallo, así que basta con recargar tras el login.
- Arranque en Codespaces: `streamlit run app.py --server.enableCORS false --server.enableXsrfProtection false` (lo hace `postAttachCommand`).
- Si se añaden variables de entorno nuevas, declararlas también en `secrets` de `devcontainer.json`, en `env.example` y en el README.

## Reglas al modificar
- Mantener el código genérico: nada de literales del dominio (club, fútbol, GitHub…) ni del proveedor en `app.py`, `graficos.py`, `agentes/base.py`. Lo del dominio va a `config.toml`; lo del proveedor, a su conector.
- Nuevo proveedor: copiar `agentes/plantilla.py`, implementar `nueva_conversacion`, `enviar`, `responder_aprobaciones` (devuelven `Respuesta`), y poner `proveedor = "agentes.mi_modulo:MiClase"` en `config.toml`.
- Nuevo tipo de gráfico: función en `graficos.py` registrada en `RENDERIZADORES` + etiqueta en `[graficos.bloques]`.

## Cuando el usuario pida "abrir la web" / "arrancar la app"
1. Comprobar si ya está corriendo: `curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/_stcore/health` → si da `200`, solo dar la URL.
2. Si no: comprobar dependencias con `python -c "import streamlit, plotly, azure.ai.projects"`; si falta algo, `python -m pip install -r requirements.txt`.
3. Arrancar en segundo plano (Bash, `run_in_background: true`), desde la carpeta del proyecto:
   ```
   python -m streamlit run app.py --server.headless true --server.port 8501
   ```
4. Esperar a que el health check devuelva `200` y revisar el log del proceso en busca de errores.
5. Dar al usuario la URL **http://localhost:8501**.

Para reiniciar (tras cambios), primero parar el proceso del puerto 8501 (PowerShell):
```
Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -Confirm:$false }
```
**Avisar al usuario antes de reiniciar**: se pierde la conversación abierta en el navegador.

## Problemas conocidos
- Error de credenciales al conectar con Foundry → sesión de Azure caducada: pedir al usuario `! az login`.
- Claude Code puede matar el proceso en segundo plano si el sistema va justo de memoria. No relanzarlo por iniciativa propia; avisar y relanzar solo si el usuario lo pide.
- El agente tarda 30-90 s (a veces más) por consulta; el log no muestra nada mientras espera.

## Notas del conector Foundry
- Patrones de `cliente.py`: `AIProjectClient` → `get_openai_client(agent_name=...)`, `conversations.create()`, `responses.create(conversation=..., input=...)`. No usar `previous_response_id` ni threads/runs.
- Aprobaciones MCP: `mcp_approval_request` → `Aprobacion`; las `Decision` se envían como `mcp_approval_response` (puede haber varias rondas).
- El Code Interpreter corre como `mcp_call` a un toolbox, así que no suelen llegar PNG; el radar llega como bloque ```radar``` (las instrucciones del agente en Foundry deben pedirlo; usa la clave `jugadores`, aceptada vía `claves_series` en config). La descarga de PNG de containers se mantiene por si llega algún fichero.
- Todo el CSS/HTML se inyecta con `st.html` (no `st.markdown`, que lo pintaba como texto).
