#!/usr/bin/env bash
set -euo pipefail

# --- Configuración ---
DEVICE="/dev/video0"

CAPTURADAS_DIR="/home/diie/tra_arch/Fotos/Capturadas"
RECIBIDAS_DIR="/home/diie/tra_arch/Fotos/Recibidas"

CAPTURA="${CAPTURADAS_DIR}/foto.jpg"                 # nombre fijo para la toma
SALIDA_PY="/home/diie/Documents/ImagenDeLlegada.jpg" # archivo fijo que genera el Python
PY_SCRIPT="/home/diie/TxRxBPSK.py"                   # ajusta la ruta si está en otro lado

INTERVALO=5   # segundos entre iteraciones (ajústalo a gusto)

# --- Asegura que existan las carpetas ---
mkdir -p "$CAPTURADAS_DIR" "$RECIBIDAS_DIR"

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
