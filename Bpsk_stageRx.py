#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-License-Identifier: GPL-3.0
# GNU Radio Python Flow Graph - Proyecto TÖRÖN II

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from gnuradio import blocks
from gnuradio import digital
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
import osmosdr
import time
import sip
import threading
import mmap
import zlib
from bitarray import bitarray 

# ---------------------------------------------------------
# Funciones del receptor (nivel módulo)
# ---------------------------------------------------------
def bytes_to_bits(data):
    ba = bitarray(endian='big')
    try:
        raw = data[:] if isinstance(data, (mmap.mmap, memoryview)) else data
    except Exception:
        raw = data
    ba.frombytes(raw)
    return ba

def find_frame_start(bits, preamble_min=20, start_index=0):
    alt_pattern = [1, 0] * ((preamble_min // 2) + 2)
    preamble_len = len(alt_pattern[:preamble_min])
    for i in range(start_index, len(bits) - preamble_len - 64 - 24):
        if bits[i:i+preamble_len].tolist() == alt_pattern[:preamble_len]:
            if all(b == 1 for b in bits[i+preamble_len : i+preamble_len+64]):
                return i + preamble_len + 64
    return None

def run_post_rx(output_path):
    try:
        with open("../Python/TxRx/Archivos/Llegada.hex", "rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                bits = bytes_to_bits(mm[:])
            finally:
                mm.close()
        
        search_pos = 0
        found_valid = False
        while search_pos < len(bits):
            start_after_64ones = find_frame_start(bits, preamble_min=20, start_index=search_pos)
            if start_after_64ones is None: break
            
            size_bits = bits[start_after_64ones : start_after_64ones + 24]
            size_bytes = int.from_bytes(size_bits.tobytes(), byteorder='big')
            start_msg_bit = start_after_64ones + 24
            end_msg_bit = start_msg_bit + (size_bytes * 8)
            
            crc_bits = bits[end_msg_bit : end_msg_bit + 32]
            crc_recv = int.from_bytes(crc_bits.tobytes(), byteorder='big')
            
            payload_bytes = bits[start_msg_bit:end_msg_bit].tobytes()
            crc_calc = zlib.crc32(size_bytes.to_bytes(3, 'big') + payload_bytes)
            
            if crc_calc == crc_recv:
                with open(output_path, "wb") as out:
                    out.write(payload_bytes)
                print(f"✅ Archivo recibido ({size_bytes} bytes). CRC OK. Guardado en: {output_path}")
                found_valid = True
                break
            search_pos = end_msg_bit + 32
        if not found_valid: print("❌ No se encontró ningún paquete válido.")
    except Exception as e:
        print(f"Error en post-procesamiento: {e}")

# ---------------------------------------------------------
# Clase Principal del Flowgraph
# ---------------------------------------------------------
class Bpsk_stageRx(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Receptor BPSK - TÖRÖN II", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Receptor BPSK - TÖRÖN II")
        
        self.top_layout = Qt.QVBoxLayout(self)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)
        
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "Bpsk_stageRx")
        self.flowgraph_started = threading.Event()

        # Variables
        self.sps = 4
        self.samp_rate = 1000000
        self.freq = 150e6
        self.bpsk = digital.constellation_bpsk().base()
        taps = firdes.root_raised_cosine(32, 32, 1.0, 0.35, 11*self.sps*32)

        ##################################################
        # Blocks
        ##################################################
        # Fuente SDR
        self.osmosdr_source_0 = osmosdr.source(args="numchan=1")
        self.osmosdr_source_0.set_sample_rate(self.samp_rate)
        self.osmosdr_source_0.set_center_freq(self.freq, 0)
        self.osmosdr_source_0.set_gain(15, 0)
        self.osmosdr_source_0.set_if_gain(20, 0)
        self.osmosdr_source_0.set_bb_gain(20, 0)

        # Medición de Potencia (Corregido para dBFS)
        self.blocks_complex_to_mag_squared = blocks.complex_to_mag_squared(1)
        self.blocks_nlog10_ff_0 = blocks.nlog10_ff(10.0, 1, 0)
        self.qtgui_number_sink = qtgui.number_sink(gr.sizeof_float, 0, qtgui.NUM_GRAPH_HORIZ, 1)
        self.qtgui_number_sink.set_label(0, "Potencia")
        self.qtgui_number_sink.set_unit(0, "dBFS")
        self.top_grid_layout.addWidget(sip.wrapinstance(self.qtgui_number_sink.qwidget(), Qt.QWidget), 0, 0, 1, 4)

        # Visualización y Procesamiento
        self.qtgui_const_sink_x_0 = qtgui.const_sink_c(1024, "Constelación", 1)
        self.top_grid_layout.addWidget(sip.wrapinstance(self.qtgui_const_sink_x_0.qwidget(), Qt.QWidget), 1, 0, 1, 4)
        
        self.digital_pfb_clock_sync_xxx_0 = digital.pfb_clock_sync_ccf(self.sps, 0.0628, taps, 32, 16, 1.5, 1)
        self.digital_costas_loop_cc_0 = digital.costas_loop_cc(0.02, 2, False)
        self.digital_constellation_decoder_cb_0 = digital.constellation_decoder_cb(self.bpsk)
        self.digital_diff_decoder_bb_0 = digital.diff_decoder_bb(2, digital.DIFF_DIFFERENTIAL)
        self.blocks_pack_k_bits_bb_0 = blocks.pack_k_bits_bb(8)
        self.blocks_skiphead_0 = blocks.skiphead(gr.sizeof_char, 1024)
        self.blocks_file_sink_1 = blocks.file_sink(gr.sizeof_char, "../Python/TxRx/Archivos/Llegada.hex", False)

        ##################################################
        # Connections
        ##################################################
        # Rama de Potencia
        self.connect((self.osmosdr_source_0, 0), (self.blocks_complex_to_mag_squared, 0))
        self.connect((self.blocks_complex_to_mag_squared, 0), (self.blocks_nlog10_ff_0, 0))
        self.connect((self.blocks_nlog10_ff_0, 0), (self.qtgui_number_sink, 0))

        # Rama de Datos
        self.connect((self.osmosdr_source_0, 0), (self.digital_pfb_clock_sync_xxx_0, 0))
        self.connect((self.digital_pfb_clock_sync_xxx_0, 0), (self.digital_costas_loop_cc_0, 0))
        self.connect((self.digital_costas_loop_cc_0, 0), (self.qtgui_const_sink_x_0, 0))
        self.connect((self.digital_costas_loop_cc_0, 0), (self.digital_constellation_decoder_cb_0, 0))
        self.connect((self.digital_constellation_decoder_cb_0, 0), (self.digital_diff_decoder_bb_0, 0))
        self.connect((self.digital_diff_decoder_bb_0, 0), (self.blocks_pack_k_bits_bb_0, 0))
        self.connect((self.blocks_pack_k_bits_bb_0, 0), (self.blocks_skiphead_0, 0))
        self.connect((self.blocks_skiphead_0, 0), (self.blocks_file_sink_1, 0))

    def set_freq(self, freq):
        self.freq = freq
        self.osmosdr_source_0.set_center_freq(self.freq, 0)

# ---------------------------------------------------------
# Ejecución Principal
# ---------------------------------------------------------
def main():
    qapp = Qt.QApplication(sys.argv)
    tb = Bpsk_stageRx()
    tb.start()
    tb.show()

    def sig_handler(sig=None, frame=None):
        print("\n[!] Deteniendo receptor y procesando imagen...")
        tb.stop()
        tb.wait()
        try: tb.hide()
        except: pass
        run_post_rx("../Python/TxRx/Archivos/ImagenDeLlegada.jpg")
        Qt.QApplication.quit()

    # Vincula el cierre de la ventana con el procesamiento
    qapp.aboutToQuit.connect(sig_handler)
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    # Timer para mantener la UI responsiva
    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)
    
    # Auto-cierre tras 50 segundos (opcional)
    Qt.QTimer.singleShot(50000, lambda: sig_handler())

    sys.exit(qapp.exec_())

if __name__ == '__main__':
    main()
