#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: bpsk_stage6
# Author: Barry Duggan
# Description: Using Diff Enc
# GNU Radio version: 3.10.5.1

from packaging.version import Version as StrictVersion

import argparse
import zlib  # Para calcular CRC-32
import mmap  # <-- agregado
from bitarray import bitarray

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
from gnuradio.filter import firdes
import sip
from gnuradio import blocks
import pmt
from gnuradio import digital
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import uhd
import time
from gnuradio.qtgui import Range, RangeWidget
from PyQt5 import QtCore
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
class bpsk_stage6(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "bpsk_stage6", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("bpsk_stage6")
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

        self.settings = Qt.QSettings("GNU Radio", "bpsk_stage6")

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
        self.timing_loop_bw = timing_loop_bw = 0.0628
        self.time_offset = time_offset = 1.0001
        self.taps = taps = [1.0 + 0.0j, ]
        self.samp_rate = samp_rate = 200000
        self.rrc_taps = rrc_taps = firdes.root_raised_cosine(nfilts, nfilts, 1.0/float(sps), 0.35, 11*sps*nfilts)
        self.phase_bw = phase_bw = 0.0628
        self.noise_volt = noise_volt = 0.01
        self.loop_order = loop_order = 2
        self.freq_offset = freq_offset = 0.001
        self.excess_bw = excess_bw = 0.35
        self.delay2 = delay2 = 0
        self.delay = delay = 267
        self.bpsk = bpsk = digital.constellation_bpsk().base()

        ##################################################
        # Blocks
        ##################################################

        self._delay_range = Range(0, 10000, 1, 267, 200)
        self._delay_win = RangeWidget(self._delay_range, self.set_delay, "Delay", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._delay_win, 0, 3, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(3, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
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
        self._time_offset_range = Range(0.999, 1.001, 0.0001, 1.0001, 200)
        self._time_offset_win = RangeWidget(self._time_offset_range, self.set_time_offset, "Channel: Timing Offset", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._time_offset_win, 0, 1, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.qtgui_time_sink_x_0_0 = qtgui.time_sink_f(
            128, #size
            samp_rate, #samp_rate
            '', #name
            3, #number of inputs
            None # parent
        )
        self.qtgui_time_sink_x_0_0.set_update_time(0.10)
        self.qtgui_time_sink_x_0_0.set_y_axis(-2, 2)

        self.qtgui_time_sink_x_0_0.set_y_label('Amplitude', "")

        self.qtgui_time_sink_x_0_0.enable_tags(True)
        self.qtgui_time_sink_x_0_0.set_trigger_mode(qtgui.TRIG_MODE_AUTO, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.qtgui_time_sink_x_0_0.enable_autoscale(False)
        self.qtgui_time_sink_x_0_0.enable_grid(False)
        self.qtgui_time_sink_x_0_0.enable_axis_labels(True)
        self.qtgui_time_sink_x_0_0.enable_control_panel(False)
        self.qtgui_time_sink_x_0_0.enable_stem_plot(False)


        labels = ['Rx Bits', 'Diff', 'Tx Bits', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(3):
            if len(labels[i]) == 0:
                self.qtgui_time_sink_x_0_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_time_sink_x_0_0.set_line_label(i, labels[i])
            self.qtgui_time_sink_x_0_0.set_line_width(i, widths[i])
            self.qtgui_time_sink_x_0_0.set_line_color(i, colors[i])
            self.qtgui_time_sink_x_0_0.set_line_style(i, styles[i])
            self.qtgui_time_sink_x_0_0.set_line_marker(i, markers[i])
            self.qtgui_time_sink_x_0_0.set_line_alpha(i, alphas[i])

        self._qtgui_time_sink_x_0_0_win = sip.wrapinstance(self.qtgui_time_sink_x_0_0.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_time_sink_x_0_0_win, 1, 0, 1, 4)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
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
        self._noise_volt_range = Range(0, 1, 0.01, 0.01, 200)
        self._noise_volt_win = RangeWidget(self._noise_volt_range, self.set_noise_volt, "Channel: Noise Voltage", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._noise_volt_win, 0, 0, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._freq_offset_range = Range(-0.1, 0.1, 0.001, 0.001, 200)
        self._freq_offset_win = RangeWidget(self._freq_offset_range, self.set_freq_offset, "Channel: Frequency Offset", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._freq_offset_win, 0, 2, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(2, 3):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.digital_pfb_clock_sync_xxx_0 = digital.pfb_clock_sync_ccf(sps, timing_loop_bw, rrc_taps, nfilts, (nfilts/2), 1.5, 1)
        self.digital_diff_decoder_bb_0 = digital.diff_decoder_bb(2, digital.DIFF_DIFFERENTIAL)
        self.digital_costas_loop_cc_0 = digital.costas_loop_cc(phase_bw, loop_order, False)
        self.digital_constellation_modulator_0 = digital.generic_mod(
            constellation=bpsk,
            differential=True,
            samples_per_symbol=sps,
            pre_diff_code=True,
            excess_bw=excess_bw,
            verbose=False,
            log=False,
            truncate=False)
        self.digital_constellation_decoder_cb_0 = digital.constellation_decoder_cb(bpsk)
        self._delay2_range = Range(0, 7, 1, 0, 200)
        self._delay2_win = RangeWidget(self._delay2_range, self.set_delay2, "Delay 2", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._delay2_win, 2, 0, 1, 4)
        for r in range(2, 3):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.blocks_unpack_k_bits_bb_0_0 = blocks.unpack_k_bits_bb(8)
        self.blocks_sub_xx_0 = blocks.sub_ff(1)
        self.blocks_pack_k_bits_bb_0 = blocks.pack_k_bits_bb(8)
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_cc(1)
        self.blocks_file_source_1 = blocks.file_source(gr.sizeof_char*1, '../Python/TxRx/Archivos/Salida.hex', True, 0, 0)
        self.blocks_file_source_1.set_begin_tag(pmt.PMT_NIL)
        self.blocks_file_sink_1 = blocks.file_sink(gr.sizeof_char*1, '../Python/TxRx/Archivos/Llegada.hex', False)
        self.blocks_file_sink_1.set_unbuffered(False)
        self.blocks_delay_0 = blocks.delay(gr.sizeof_float*1, int(delay))
        self.blocks_char_to_float_0_0_0 = blocks.char_to_float(1, 1)
        self.blocks_char_to_float_0_0 = blocks.char_to_float(1, 1)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_char_to_float_0_0, 0), (self.blocks_sub_xx_0, 0))
        self.connect((self.blocks_char_to_float_0_0, 0), (self.qtgui_time_sink_x_0_0, 0))
        self.connect((self.blocks_char_to_float_0_0_0, 0), (self.blocks_delay_0, 0))
        self.connect((self.blocks_delay_0, 0), (self.blocks_sub_xx_0, 1))
        self.connect((self.blocks_delay_0, 0), (self.qtgui_time_sink_x_0_0, 2))
        self.connect((self.blocks_file_source_1, 0), (self.blocks_unpack_k_bits_bb_0_0, 0))
        self.connect((self.blocks_file_source_1, 0), (self.digital_constellation_modulator_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.uhd_usrp_sink_0, 0))
        self.connect((self.blocks_pack_k_bits_bb_0, 0), (self.blocks_file_sink_1, 0))
        self.connect((self.blocks_sub_xx_0, 0), (self.qtgui_time_sink_x_0_0, 1))
        self.connect((self.blocks_unpack_k_bits_bb_0_0, 0), (self.blocks_char_to_float_0_0_0, 0))
        self.connect((self.digital_constellation_decoder_cb_0, 0), (self.digital_diff_decoder_bb_0, 0))
        self.connect((self.digital_constellation_modulator_0, 0), (self.blocks_multiply_const_vxx_0, 0))
        self.connect((self.digital_costas_loop_cc_0, 0), (self.digital_constellation_decoder_cb_0, 0))
        self.connect((self.digital_costas_loop_cc_0, 0), (self.qtgui_const_sink_x_0, 0))
        self.connect((self.digital_diff_decoder_bb_0, 0), (self.blocks_char_to_float_0_0, 0))
        self.connect((self.digital_diff_decoder_bb_0, 0), (self.blocks_pack_k_bits_bb_0, 0))
        self.connect((self.digital_pfb_clock_sync_xxx_0, 0), (self.digital_costas_loop_cc_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.digital_pfb_clock_sync_xxx_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "bpsk_stage6")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    # ... (el resto de getters/setters tal cual estaban)
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

    def get_timing_loop_bw(self):
        return self.timing_loop_bw

    def set_timing_loop_bw(self, timing_loop_bw):
        self.timing_loop_bw = timing_loop_bw
        self.digital_pfb_clock_sync_xxx_0.set_loop_bandwidth(self.timing_loop_bw)

    def get_time_offset(self):
        return self.time_offset

    def set_time_offset(self, time_offset):
        self.time_offset = time_offset

    def get_taps(self):
        return self.taps

    def set_taps(self, taps):
        self.taps = taps

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.qtgui_time_sink_x_0_0.set_samp_rate(self.samp_rate)
        self.uhd_usrp_sink_0.set_samp_rate(self.samp_rate)
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

    def get_noise_volt(self):
        return self.noise_volt

    def set_noise_volt(self, noise_volt):
        self.noise_volt = noise_volt

    def get_loop_order(self):
        return self.loop_order

    def set_loop_order(self, loop_order):
        self.loop_order = loop_order

    def get_freq_offset(self):
        return self.freq_offset

    def set_freq_offset(self, freq_offset):
        self.freq_offset = freq_offset

    def get_excess_bw(self):
        return self.excess_bw

    def set_excess_bw(self, excess_bw):
        self.excess_bw = excess_bw

    def get_delay2(self):
        return self.delay2

    def set_delay2(self, delay2):
        self.delay2 = delay2

    def get_delay(self):
        return self.delay

    def set_delay(self, delay):
        self.delay = delay
        self.blocks_delay_0.set_dly(int(int(self.delay)))

    def get_bpsk(self):
        return self.bpsk

    def set_bpsk(self, bpsk):
        self.bpsk = bpsk




def main(top_block_cls=bpsk_stage6, options=None):
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

    print(f"✅ Archivo para transmitir generado correctamente. Tamaño payload: {size} bytes. CRC-32 agregado.")

    ##################################################
    # Transmición y Recepción en GNU Radio
    ##################################################
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
