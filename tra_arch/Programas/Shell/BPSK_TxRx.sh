#!/usr/bin/env bash

# --- Posicionamiento en el directorio del Shell ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

set -euo pipefail

# --- Configuración ---
DEVICE="/dev/video0"

CAPTURADAS_DIR="../../Fotos/Capturadas"
RECIBIDAS_DIR="../../Fotos/Recibidas"

CAPTURA="${CAPTURADAS_DIR}/foto.jpg"                 # nombre fijo para la toma
SALIDA_PY="../Python/TxRx/Archivos/ImagenDeLlegada.jpg" # archivo fijo que genera el Python
PY_SCRIPT="../Python/TxRx/TxRxBPSK.py"                   # ajusta la ruta si está en otro lado

INTERVALO=1   # segundos entre iteraciones (ajústalo a gusto)

# --- Asegura que existan las carpetas ---
mkdir -p "$CAPTURADAS_DIR" "$RECIBIDAS_DIR"

# --- Abrir segundo terminal con entorno virtual e Interfaz ---

# --- Bucle principal ---
while true; do
  FECHA="$(date +'%Y-%m-%d_%H-%M-%S')"

  echo "[*] Capturando foto en $CAPTURA ..."
  fswebcam -d "$DEVICE" -r 640x480 --no-banner "$CAPTURA"

  echo "[*] Ejecutando Python con la foto capturada ..."
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
