#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Not titled yet
# GNU Radio version: 3.10.5.1

from packaging.version import Version as StrictVersion

if __name__ == '__main__':
    import ctypes
    import sys
    if sys.platform.startswith('linux'):
        try:
            x11 = ctypes.cdll.LoadLibrary('libX11.so')
            x11.XInitThreads()
        except:
            print("Warning: failed to XInitThreads()")

from gnuradio import blocks
import pmt
from gnuradio import digital
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import uhd
import time



from gnuradio import qtgui

class Bpsk_stageTx(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Not titled yet", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Not titled yet")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except:
            pass
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("GNU Radio", "Bpsk_stageTx")

        try:
            if StrictVersion(Qt.qVersion()) < StrictVersion("5.0.0"):
                self.restoreGeometry(self.settings.value("geometry").toByteArray())
            else:
                self.restoreGeometry(self.settings.value("geometry"))
        except:
            pass

        ##################################################
        # Variables
        ##################################################
        self.sps = sps = 4
        self.samp_rate = samp_rate = 32000
        self.excess_bw = excess_bw = 0.35
        self.bpsk = bpsk = digital.constellation_bpsk().base()

        ##################################################
        # Blocks
        ##################################################

        self.uhd_usrp_sink_0 = uhd.usrp_sink(
            ",".join(("", '')),
            uhd.stream_args(
                cpu_format="fc32",
                args='',
                channels=list(range(0,1)),
            ),
            "",
        )
        self.uhd_usrp_sink_0.set_samp_rate(samp_rate)
        self.uhd_usrp_sink_0.set_time_unknown_pps(uhd.time_spec(0))

        self.uhd_usrp_sink_0.set_center_freq(150e6, 0)
        self.uhd_usrp_sink_0.set_antenna("TX/RX", 0)
        self.uhd_usrp_sink_0.set_bandwidth(0.5e6, 0)
        self.uhd_usrp_sink_0.set_gain(90, 0)
        self.digital_constellation_modulator_0 = digital.generic_mod(
            constellation=bpsk,
            differential=True,
            samples_per_symbol=sps,
            pre_diff_code=True,
            excess_bw=excess_bw,
            verbose=False,
            log=False,
            truncate=False)
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_cc(1)
        self.blocks_file_source_1 = blocks.file_source(gr.sizeof_char*1, '../Python/TxRx/Archivos/Salida.hex', True, 0, 0)
        self.blocks_file_source_1.set_begin_tag(pmt.PMT_NIL)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_file_source_1, 0), (self.digital_constellation_modulator_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.uhd_usrp_sink_0, 0))
        self.connect((self.digital_constellation_modulator_0, 0), (self.blocks_multiply_const_vxx_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "Bpsk_stageTx")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.uhd_usrp_sink_0.set_samp_rate(self.samp_rate)

    def get_excess_bw(self):
        return self.excess_bw

    def set_excess_bw(self, excess_bw):
        self.excess_bw = excess_bw

    def get_bpsk(self):
        return self.bpsk

    def set_bpsk(self, bpsk):
        self.bpsk = bpsk




def main(top_block_cls=Bpsk_stageTx, options=None):
    ##################################################
    # Preparación para transmitir archivo
    ##################################################
    parser = argparse.ArgumentParser(description="Generar archivo con preámbulo, 64 unos, tamaño, payload y CRC-32")
    parser.add_argument("-i", "--input", required=True, help="Archivo de entrada (payload)")
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
    with open("../Python/TxRx/Archivos/Salida.hex", "wb") as f:
        f.write(final_bits.tobytes())

    print(f"✅ Archivo para transmitir generado correctamente. Tamaño payload: >

    ##################################################
    # Transmición en GNU Radio
    ##################################################
    if StrictVersion("4.5.0") <= StrictVersion(Qt.qVersion()) < StrictVersion("5.0.0"):
        style = gr.prefs().get_string('qtgui', 'style', 'raster')
        Qt.QApplication.setGraphicsSystem(style)
    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    Qt.QTimer.singleShot(40000, lambda: sig_handler())

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
