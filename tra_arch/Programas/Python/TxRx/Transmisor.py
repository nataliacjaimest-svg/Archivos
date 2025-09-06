#!/usr/bin/env python3
import argparse
import zlib  # Para calcular CRC-32
from bitarray import bitarray

def main():
    parser = argparse.ArgumentParser(description="Generar archivo con preámbulo, 64 unos, tamaño, payload y CRC-32")
    parser.add_argument("-i", "--input", required=True, help="Archivo de entrada (payload)")
    parser.add_argument("-o", "--output", required=True, help="Archivo de salida preparado para transmisión")
    args = parser.parse_args()

    # Leer archivo de entrada
    with open(args.input, "rb") as f:
        payload = f.read()

    # --------------------------
    # 1) Preambulo alternante 128 bits
    preamble_bits = bitarray(endian='big')
    for i in range(128):
        preamble_bits.append((i+1) % 2)  # 1,0,1,0...

    # 2) 64 unos seguidos
    ones_bits = bitarray('1'*64, endian='big')

    # 3) Tamaño del payload en 3 bytes
    size = len(payload)
    if size > 16777215:
        raise ValueError("Archivo demasiado grande, máximo 16_777_215 bytes")
    size_bytes = size.to_bytes(3, byteorder='big')
    size_bits = bitarray(endian='big')
    size_bits.frombytes(size_bytes)

    # 4) Convertir payload a bits
    payload_bits = bitarray(endian='big')
    payload_bits.frombytes(payload)

    # 5) Calcular CRC-32 sobre tamaño + payload
    crc_input = size_bytes + payload
    crc_value = zlib.crc32(crc_input)  # Devuelve un entero de 32 bits
    crc_bytes = crc_value.to_bytes(4, byteorder='big')  # 32 bits = 4 bytes
    crc_bits = bitarray(endian='big')
    crc_bits.frombytes(crc_bytes)
 
    # --------------------------
    # Concatenar todo
    final_bits = preamble_bits + ones_bits + size_bits + payload_bits + crc_bits

    # Escribir a archivo
    with open(args.output, "wb") as f:
        f.write(final_bits.tobytes())

    print(f"✅ Archivo '{args.output}' generado correctamente. Tamaño payload: {size} bytes. CRC-32 agregado.")

if __name__ == "__main__":
    main()
