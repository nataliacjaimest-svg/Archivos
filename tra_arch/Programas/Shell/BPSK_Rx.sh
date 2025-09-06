#!/usr/bin/env bash

# --- Posicionamiento en el directorio del Shell ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

set -euo pipefail

# --- Configuración ---
RECIBIDAS_DIR="../../Fotos/Recibidas"

SALIDA_PY="../Python/TxRx/Archivos/ImagenDeLlegada.jpg" # archivo fijo que genera el Python
PY_SCRIPT="../Python/TxRx/Bpsk_stageRx.py"                   # ajusta la ruta si está en otro lado

INTERVALO=1   # segundos entre iteraciones (ajústalo a gusto)

# --- Asegura que existan las carpetas ---
mkdir -p "$RECIBIDAS_DIR"

# --- Bucle principal ---
while true; do
  FECHA="$(date +'%Y-%m-%d_%H-%M-%S')"

  echo "[*] Ejecutando Python para recepcion ..."
  python3 "$PY_SCRIPT" -i "$CAPTURA"

  # Guarda la imagen de salida con sello de tiempo en Recibidas
  if [[ -f "$SALIDA_PY" ]]; then
    DESTINO="${RECIBIDAS_DIR}/foto_${FECHA}.jpg"
    cp "$SALIDA_PY" "$DESTINO"
    echo "[✓] Imagen recibida guardada como: $DESTINO"
  else
    echo "[!] No se encontró la salida esperada: $SALIDA_PY" >&2
  fi

  sleep "$INTERVALO"
done
