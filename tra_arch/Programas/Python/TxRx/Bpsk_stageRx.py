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

from PyQt5 import Qt
from gnuradio import qtgui
import sip
from gnuradio import blocks
from gnuradio import digital
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import uhd
import time
from gnuradio import qtgui

# ---------------------------------------------------------
# Funciones del receptor (nivel módulo) -- **NO** dentro de la clase
# ---------------------------------------------------------
def bytes_to_bits(data, bitorder='big'):
    """
    Convierte bytes (o mmap/memoryview) en bitarray big-endian.
    """
    ba = bitarray(endian='big')
    # Si es mmap o memoryview, tomar su contenido como bytes
    try:
        # mmap soporta slicing mm[:], que devuelve bytes
        if isinstance(data, (mmap.mmap, memoryview)):
            raw = data[:]
        else:
            raw = data
    except Exception:
        raw = data
    ba.frombytes(raw)
    return ba

def find_frame_start(bits, preamble_min=20, start_index=0):
    """
    Busca un patrón alternante 1,0 repetido (mín. 'preamble_min' bits) seguido de 64 unos.
    Retorna el índice del bit justo después de esos 64 unos, o None.
    """
    alt_pattern = [1, 0] * ((preamble_min // 2) + 2)
    preamble_len = len(alt_pattern[:preamble_min])

    for i in range(start_index, len(bits) - preamble_len - 64 - 24):
        if bits[i:i+preamble_len].tolist() == alt_pattern[:preamble_len]:
            if all(b == 1 for b in bits[i+preamble_len : i+preamble_len+64]):
                return i + preamble_len + 64
    return None

def run_post_rx(output_path):
    """
    Abre ../Python/TxRx/Archivos/Llegada.hex, busca el paquete, verifica CRC y escribe payload en output_path.
    """
    # 1) Leer archivo como memoria mapeada
    with open("../Python/TxRx/Archivos/Llegada.hex", "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            bits = bytes_to_bits(mm[:])  # usar mm[:] para bytes explícitos
        finally:
            mm.close()

    search_pos = 0
    found_valid = False

    while search_pos < len(bits):
        # 2) Buscar preámbulo (pides 20, se mantiene 20)
        start_after_64ones = find_frame_start(bits, preamble_min=20, start_index=search_pos)
        if start_after_64ones is None:
            break  # No hay más secuencias

        # 3) Leer tamaño (3 bytes → 24 bits)
        size_bits = bits[start_after_64ones : start_after_64ones + 24]
        size_bytes = int.from_bytes(size_bits.tobytes(), byteorder='big')
        start_msg_bit = start_after_64ones + 24
        end_msg_bit = start_msg_bit + (size_bytes * 8)

        # 4) Leer CRC recibido (32 bits)
        crc_bits = bits[end_msg_bit : end_msg_bit + 32]
        crc_recv = int.from_bytes(crc_bits.tobytes(), byteorder='big')

        # 5) Payload
        payload_bits = bits[start_msg_bit:end_msg_bit]
        payload_bytes = payload_bits.tobytes()

        # 6) Calcular CRC sobre tamaño(3B) + payload
        size_bytes_data = size_bytes.to_bytes(3, byteorder='big')
        crc_calc = zlib.crc32(size_bytes_data + payload_bytes)

        # 7) Comparar CRCs
        if crc_calc == crc_recv:
            with open(output_path, "wb") as out:
                out.write(payload_bytes)
            print(f"✅ Archivo recibido correctamente ({size_bytes} bytes). CRC verificado. Guardado en: {output_path}")
            found_valid = True
            break
        else:
            print(f"⚠ CRC incorrecto en posición {search_pos} → buscando siguiente posible paquete...")
            search_pos = end_msg_bit + 32  # avanzar más allá del mensaje actual

    if not found_valid:
        print("❌ No se recibió ningún paquete válido.")


# ---------------------------------------------------------
# Clase flowgraph GNU Radio (sin modificar su lógica)
# ---------------------------------------------------------
class Bpsk_stageRx(gr.top_block, Qt.QWidget):

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

        self.settings = Qt.QSettings("GNU Radio", "Bpsk_stageRx")

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
        self.nfilts = nfilts = 32
        self.timing_loop_bw_0 = timing_loop_bw_0 = 0.0628
        self.timing_loop_bw = timing_loop_bw = 0.0628
        self.samp_rate = samp_rate = 32000
        self.rrc_taps = rrc_taps = firdes.root_raised_cosine(nfilts, nfilts, 1.0/float(sps), 0.35, 11*sps*nfilts)
        self.phase_bw = phase_bw = 0.0628
        self.loop_order = loop_order = 2
        self.bpsk = bpsk = digital.constellation_bpsk().base()

        ##################################################
        # Blocks
        ##################################################

        self.uhd_usrp_source_0 = uhd.usrp_source(
            ",".join(("", '')),
            uhd.stream_args(
                cpu_format="fc32",
                args='',
                channels=list(range(0,1)),
            ),
        )
        self.uhd_usrp_source_0.set_samp_rate(samp_rate)
        self.uhd_usrp_source_0.set_time_unknown_pps(uhd.time_spec(0))

        self.uhd_usrp_source_0.set_center_freq(150e6, 0)
        self.uhd_usrp_source_0.set_antenna("RX2", 0)
        self.uhd_usrp_source_0.set_bandwidth(500e3, 0)
        self.uhd_usrp_source_0.set_gain(30, 0)
        self.qtgui_const_sink_x_0 = qtgui.const_sink_c(
            1024, #size
            '', #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_const_sink_x_0.set_update_time(0.10)
        self.qtgui_const_sink_x_0.set_y_axis((-2), 2)
        self.qtgui_const_sink_x_0.set_x_axis((-2), 2)
        self.qtgui_const_sink_x_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, "")
        self.qtgui_const_sink_x_0.enable_autoscale(False)
        self.qtgui_const_sink_x_0.enable_grid(False)
        self.qtgui_const_sink_x_0.enable_axis_labels(True)


        labels = ['', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "red", "red", "red",
            "red", "red", "red", "red", "red"]
        styles = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        markers = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_const_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_const_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_const_sink_x_0.set_line_width(i, widths[i])
            self.qtgui_const_sink_x_0.set_line_color(i, colors[i])
            self.qtgui_const_sink_x_0.set_line_style(i, styles[i])
            self.qtgui_const_sink_x_0.set_line_marker(i, markers[i])
            self.qtgui_const_sink_x_0.set_line_alpha(i, alphas[i])

        self._qtgui_const_sink_x_0_win = sip.wrapinstance(self.qtgui_const_sink_x_0.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_const_sink_x_0_win, 3, 0, 1, 4)
        for r in range(3, 4):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.digital_pfb_clock_sync_xxx_0 = digital.pfb_clock_sync_ccf(sps, timing_loop_bw, rrc_taps, nfilts, (nfilts/2), 1.5, 1)
        self.digital_diff_decoder_bb_0 = digital.diff_decoder_bb(2, digital.DIFF_DIFFERENTIAL)
        self.digital_costas_loop_cc_0 = digital.costas_loop_cc(phase_bw, loop_order, False)
        self.digital_constellation_decoder_cb_0 = digital.constellation_decoder_cb(bpsk)
        self.blocks_pack_k_bits_bb_0 = blocks.pack_k_bits_bb(8)
        self.blocks_file_sink_1 = blocks.file_sink(gr.sizeof_char*1, '../Python/TxRx/Archivos/Llegada.hex', False)
        self.blocks_file_sink_1.set_unbuffered(False)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_pack_k_bits_bb_0, 0), (self.blocks_file_sink_1, 0))
        self.connect((self.digital_constellation_decoder_cb_0, 0), (self.digital_diff_decoder_bb_0, 0))
        self.connect((self.digital_costas_loop_cc_0, 0), (self.digital_constellation_decoder_cb_0, 0))
        self.connect((self.digital_costas_loop_cc_0, 0), (self.qtgui_const_sink_x_0, 0))
        self.connect((self.digital_diff_decoder_bb_0, 0), (self.blocks_pack_k_bits_bb_0, 0))
        self.connect((self.digital_pfb_clock_sync_xxx_0, 0), (self.digital_costas_loop_cc_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.digital_pfb_clock_sync_xxx_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "Bpsk_stageRx")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps
        self.set_rrc_taps(firdes.root_raised_cosine(self.nfilts, self.nfilts, 1.0/float(self.sps), 0.35, 11*self.sps*self.nfilts))

    def get_nfilts(self):
        return self.nfilts

    def set_nfilts(self, nfilts):
        self.nfilts = nfilts
        self.set_rrc_taps(firdes.root_raised_cosine(self.nfilts, self.nfilts, 1.0/float(self.sps), 0.35, 11*self.sps*self.nfilts))

    def get_timing_loop_bw_0(self):
        return self.timing_loop_bw_0

    def set_timing_loop_bw_0(self, timing_loop_bw_0):
        self.timing_loop_bw_0 = timing_loop_bw_0

    def get_timing_loop_bw(self):
        return self.timing_loop_bw

    def set_timing_loop_bw(self, timing_loop_bw):
        self.timing_loop_bw = timing_loop_bw
        self.digital_pfb_clock_sync_xxx_0.set_loop_bandwidth(self.timing_loop_bw)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.uhd_usrp_source_0.set_samp_rate(self.samp_rate)

    def get_rrc_taps(self):
        return self.rrc_taps

    def set_rrc_taps(self, rrc_taps):
        self.rrc_taps = rrc_taps
        self.digital_pfb_clock_sync_xxx_0.update_taps(self.rrc_taps)

    def get_phase_bw(self):
        return self.phase_bw

    def set_phase_bw(self, phase_bw):
        self.phase_bw = phase_bw
        self.digital_costas_loop_cc_0.set_loop_bandwidth(self.phase_bw)

    def get_loop_order(self):
        return self.loop_order

    def set_loop_order(self, loop_order):
        self.loop_order = loop_order

    def get_bpsk(self):
        return self.bpsk

    def set_bpsk(self, bpsk):
        self.bpsk = bpsk




def main(top_block_cls=Bpsk_stageRx, options=None):

    if StrictVersion("4.5.0") <= StrictVersion(Qt.qVersion()) < StrictVersion("5.0.0"):
        style = gr.prefs().get_string('qtgui', 'style', 'raster')
        Qt.QApplication.setGraphicsSystem(style)
    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()

    tb.show()

    def sig_handler(sig=None, frame=None):
        # 1) Detener el flowgraph
        tb.stop()
        tb.wait()

        # 2) Cerrar/ocultar la GUI antes del post-proceso (opcional, evita parpadeos)
        try:
            tb.hide()   # como tu top_block hereda de QWidget, esto funciona
        except Exception:
            pass

        # 3) Ejecutar el tramo final (ANTES de cerrar Qt)
        #    Ajusta la ruta de salida si quieres otro nombre/ubicación
        run_post_rx("../Python/TxRx/Archivos/ImagenDeLlegada.jpg")

        # 4) Ahora sí, salir de Qt
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
