#!/usr/bin/env bash

# --- Posicionamiento en el directorio del Shell ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

set -euo pipefail

# --- Configuración ---
DEVICE="/dev/video0"

CAPTURADAS_DIR="../../Fotos/Capturadas"

CAPTURA="${CAPTURADAS_DIR}/foto.jpg"                 # nombre fijo para la toma
PY_SCRIPT="../Python/TxRx/Bpsk_stageTxthis.py"                   # ajusta la ruta si está en otro lado

INTERVALO=1   # segundos entre iteraciones (ajústalo a gusto)

# --- Asegura que existan las carpetas ---
mkdir -p "$CAPTURADAS_DIR"

# --- Bucle principal ---
while true; do
  echo "[*] Capturando foto en $CAPTURA ..."
  fswebcam -d "$DEVICE" -r 640x480 --no-banner "$CAPTURA"

  echo "[*] Ejecutando Python para transmision ..."
  sudo chrt -f 80 python3 "$PY_SCRIPT" -i "$CAPTURA"

  sleep "$INTERVALO"
done
