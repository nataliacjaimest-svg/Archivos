#!/usr/bin/env bash

# --- Posicionamiento en el directorio ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

set -euo pipefail

# --- Configuración ---
RECIBIDAS_DIR="../../Fotos/Recibidas"
SALIDA_PY="../Python/TxRx/Archivos/ImagenDeLlegada.jpg"
HEX_RECIBIDO="../Python/TxRx/Archivos/Recibido.hex"  # El archivo que genera GNU Radio
PY_SCRIPT="../Python/TxRx/Bpsk_stageRx_PRUEBA.py"

INTERVALO=2   # Breve pausa para estabilizar los SDR entre capturas

# Asegura que existan las carpetas
mkdir -p "$RECIBIDAS_DIR"

echo "====================================================="
echo "   SISTEMA DE RECEPCIÓN CÍCLICA SDR - ACTIVADO"
echo "====================================================="

# --- Bucle principal ---
while true; do
  FECHA="$(date +'%Y-%m-%d_%H-%M-%S')"
  
  # 1. Limpieza preventiva: Borramos el .hex anterior para no procesar datos viejos
  rm -f "$HEX_RECIBIDO"
  rm -f "$SALIDA_PY"

  echo "[$(date +'%H:%M:%S')] [*] Esperando transmisión (Iniciando GNU Radio)..."
  
  # 2. Ejecutar el script de Python
  # Nota: Tu Python tiene un timer interno de 50s o cierra al recibir SIGINT
  python3 "$PY_SCRIPT"

  # 3. Verificación de la imagen generada por el post-procesamiento
  if [[ -f "$SALIDA_PY" ]]; then
    DESTINO="${RECIBIDAS_DIR}/foto_${FECHA}.jpg"
    cp "$SALIDA_PY" "$DESTINO"
    
    echo "-----------------------------------------------------"
    echo "[✓] ¡ÉXITO! Paquete validado y guardado."
    echo "[✓] Archivo: $DESTINO"
    echo "-----------------------------------------------------"
  else
    echo "[!] ADVERTENCIA: Ciclo terminado sin recibir imagen válida."
  fi

  echo "[*] Reiniciando en $INTERVALO segundos... (Ctrl+C para detener)"
  sleep "$INTERVALO"
done

