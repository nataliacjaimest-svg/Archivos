#!/usr/bin/env python3
import argparse
import mmap
import zlib
from bitarray import bitarray

def bytes_to_bits(data, bitorder='big'):
    """
    Convierte un objeto de tipo bytes en un bitarray.
    Parámetros:
        data: bytes, contenido binario.
        bitorder: 'big' (msb primero) o 'little' (lsb primero).
    Retorna:
        bitarray con el contenido en bits.
    """
    ba = bitarray(endian='big' if bitorder == 'msb' else 'little')
    ba.frombytes(data)
    return ba

def find_preamble(bits, preamble_min=20, start_index=0):
    """
    Busca un patrón alternante 1,0 repetido y seguido de 64 unos.
    Parámetros:
        bits: bitarray completo.
        preamble_min: mínimo de bits alternantes a encontrar.
        start_index: índice desde donde empezar la búsqueda.
    Retorna:
        índice del bit después de los 64 unos, o None si no se encuentra.
    """
    # Patrón alternante generado
    alt_pattern = [1, 0] * ((preamble_min // 2) + 2)
    preamble_len = len(alt_pattern[:preamble_min])

    # Iteramos desde start_index hasta el final menos lo que ocupa el patrón
    for i in range(start_index, len(bits) - preamble_len - 64 - 24):
        # Verificamos que la parte inicial coincide con el patrón alternante
        if bits[i:i+preamble_len].tolist() == alt_pattern[:preamble_len]:
            # Verificamos que luego vengan 64 bits de unos
            if all(b == 1 for b in bits[i+preamble_len : i+preamble_len+64]):
                return i + preamble_len + 64
    return None

def main():
    parser = argparse.ArgumentParser(description="Receptor con CRC-32 y reintento en caso de error")
    parser.add_argument("-i", "--input", required=True, help="Archivo de entrada")
    parser.add_argument("-o", "--output", required=True, help="Archivo de salida")
    parser.add_argument("--preamble-min", type=int, default=20, help="Longitud mínima preámbulo en bits")
    parser.add_argument("--bit-order", choices=["msb","lsb"], default="msb", help="Orden de bits")
    args = parser.parse_args()

    # 1) Leer archivo como memoria mapeada (permite acceder sin cargar todo en RAM)
    with open(args.input, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        bits = bytes_to_bits(mm, bitorder=args.bit_order)

    search_pos = 0
    found_valid = False

    while search_pos < len(bits):
        # 2) Buscar preámbulo
        start_after_64ones = find_preamble(bits, args.preamble_min, start_index=search_pos)
        if start_after_64ones is None:
            break  # No hay más secuencias

        # 3) Leer tamaño (3 bytes → 24 bits)
        size_bits = bits[start_after_64ones : start_after_64ones + 24]
        size_bytes = int.from_bytes(size_bits.tobytes(), byteorder='big')
        start_msg_bit = start_after_64ones + 24
        end_msg_bit = start_msg_bit + (size_bytes * 8)

        # 4) Leer CRC recibido (últimos 4 bytes después del payload)
        crc_bits = bits[end_msg_bit : end_msg_bit + 32]
        crc_recv = int.from_bytes(crc_bits.tobytes(), byteorder='big')

        # 5) Extraer payload
        payload_bits = bits[start_msg_bit:end_msg_bit]
        payload_bytes = payload_bits.tobytes()

        # 6) Calcular CRC sobre tamaño + payload
        size_bytes_data = size_bytes.to_bytes(3, byteorder='big')
        crc_calc = zlib.crc32(size_bytes_data + payload_bytes)

        # 7) Comparar CRCs
        if crc_calc == crc_recv:
            with open(args.output, "wb") as out:
                out.write(payload_bytes)
            print(f"✅ Archivo recibido correctamente ({size_bytes} bytes). CRC verificado.")
            found_valid = True
            break
        else:
            print(f"⚠ CRC incorrecto en posición {search_pos} → buscando siguiente posible paquete...")
            search_pos = end_msg_bit + 32  # Avanzar más allá del mensaje actual

    if not found_valid:
        print("❌ No se recibió ningún paquete válido.")

if __name__ == "__main__":
    main()
