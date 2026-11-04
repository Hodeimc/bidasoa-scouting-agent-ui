#!/usr/bin/env bash
# Inicia sesión en Azure al abrir el Codespace (solo si no hay sesión ya).
# La app (DefaultAzureCredential) usa esta sesión para llamar al agente de Foundry.

if az account show >/dev/null 2>&1; then
  echo "✅ Ya hay sesión de Azure ($(az account show --query user.name -o tsv)). La app está en el puerto 8501."
  exit 0
fi

# Sin selector interactivo de suscripción tras el login (no hace falta para la app)
az config set core.login_experience_v2=off >/dev/null 2>&1

cat <<'EOF'

============================================================
  🔐 Inicia sesión en Azure para conectar la app con el agente
  1. Abre el enlace que aparece abajo
  2. Escribe el código que se indica e inicia sesión con tu cuenta
  3. Cuando termine, recarga la app (pestaña Ports → 8501)
============================================================

EOF

if az login --use-device-code --allow-no-subscriptions >/dev/null; then
  echo ""
  echo "✅ Sesión iniciada como $(az account show --query user.name -o tsv). Recarga la app (puerto 8501)."
else
  echo "❌ No se pudo iniciar sesión. Vuelve a intentarlo con: bash .devcontainer/login-azure.sh"
fi
