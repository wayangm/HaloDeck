# ============================================================
# Uji ManajerSerial.cari_port() tanpa perangkat keras.
# Jalankan dari root repo: python -m unittest discover tests
# Butuh pyserial (pip install -r pc_bridge/requirements.txt)
# ============================================================

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pc_bridge"))

from serial.tools.list_ports_common import ListPortInfo  # noqa: E402

import bridge_fase2a  # noqa: E402


def port(device, deskripsi):
    p = ListPortInfo(device)
    p.description = deskripsi
    return p


def cari_dengan(port_target, daftar):
    with mock.patch("serial.tools.list_ports.comports", return_value=daftar):
        return bridge_fase2a.ManajerSerial(port_target, 115200).cari_port()


class TesCariPort(unittest.TestCase):
    def test_port_target_terpasang_dipakai(self):
        daftar = [port("COM4", "USB-SERIAL CH340 (COM4)")]
        self.assertEqual(cari_dengan("COM4", daftar), "COM4")

    def test_port_target_tidak_ada_jatuh_ke_auto_cari(self):
        # Papan di PC lain sering muncul sebagai COM5, bukan COM4
        daftar = [port("COM1", "Communications Port (COM1)"),
                  port("COM5", "USB-SERIAL CH340 (COM5)")]
        self.assertEqual(cari_dengan("COM4", daftar), "COM5")

    def test_port_target_kosong_auto_cari(self):
        daftar = [port("COM3", "Silicon Labs CP210x USB to UART Bridge (COM3)")]
        self.assertEqual(cari_dengan("", daftar), "COM3")

    def test_tidak_ada_papan(self):
        daftar = [port("COM1", "Communications Port (COM1)")]
        self.assertIsNone(cari_dengan("COM4", daftar))


if __name__ == "__main__":
    unittest.main()
