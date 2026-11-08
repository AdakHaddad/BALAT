"""Tata letak dua PCB BALAT. Ubah angka posisi di sini lalu jalankan buat_semua.py."""

# urutan konektor antar-papan J1 (sama di kedua papan; pin 1 = kotak)
J1_NET = {"1": "GPS_EN", "2": "GPS_TX", "3": "TEMP_DQ", "4": "3V3", "5": "GND", "6": "VBAT"}
J1_LABEL = ["EN", "TX", "DQ", "3V3", "GND", "VBAT"]

ESP_NET = {"5V": "VBAT", "GND": "GND", "3V3": "3V3", "IO0": "VBAT_SENSE", "IO1": "TEMP_DQ",
           "IO3": "BUZ_CTRL", "IO4": "MOT_CTRL", "IO5": "GPS_EN", "IO6": "BTN", "IO10": "LED_CTRL",
           "IO20": "GPS_TX"}

# (ref, jenis, nilai, x, y, rotasi, {pad: net})  koordinat = pad 1, mm dari pojok kiri atas papan
UTAMA = dict(w=54, h=54, notch=7.5, parts=[
    ("U1", "ESP", "ESP32-C3 Super Mini", 17.78, 27.94, 180, ESP_NET),
    ("J1", "H6", "Ke kotak 2", 12.7, 49.53, 90, J1_NET),
    ("J2", "H2", "Motor PS", 50.17, 29.21, 0, {"1": "MOT_N", "2": "VBAT"}),
    ("J3", "H2", "Tombol lapor", 5.08, 33.02, 0, {"1": "BTN", "2": "GND"}),
    ("R10", "RV", "220", 5.08, 24.13, 90, {"1": "LED_CTRL", "2": "LED_A"}),
    ("D3", "LED", "LED", 5.08, 16.51, -90, {"1": "GND", "2": "LED_A"}),
    ("R1", "RV", "100k", 25.4, 2.54, -90, {"1": "VBAT", "2": "VBAT_SENSE"}),
    ("R2", "RV", "100k", 22.86, 7.62, 180, {"1": "VBAT_SENSE", "2": "GND"}),
    ("C2", "C", "100nF", 22.86, 11.43, 180, {"1": "VBAT_SENSE", "2": "GND"}),
    ("BZ1", "BZ", "Buzzer aktif 3,3V", 34.29, 8.89, 0, {"1": "3V3", "2": "BUZ_N"}),
    ("R3", "R", "4k7", 29.21, 19.05, 0, {"1": "TEMP_DQ", "2": "3V3"}),
    ("R4", "R", "1k", 29.21, 24.13, 0, {"1": "BUZ_CTRL", "2": "Q1_B"}),
    ("R5", "RV", "10k", 39.37, 24.13, 90, {"1": "Q1_B", "2": "GND"}),
    ("Q1", "Q", "S8050", 43.18, 26.67, 90, {"1": "GND", "2": "Q1_B", "3": "BUZ_N"}),
    ("R6", "R", "470", 29.21, 29.21, 0, {"1": "MOT_CTRL", "2": "Q2_B"}),
    ("R7", "RV", "10k", 39.37, 29.21, 0, {"1": "Q2_B", "2": "GND"}),
    ("Q2", "Q", "2N2222", 39.37, 34.29, 0, {"1": "GND", "2": "Q2_B", "3": "MOT_N"}),
    ("D2", "D", "1N5819", 46.99, 36.83, 90, {"1": "VBAT", "2": "MOT_N"}),
    ("C1", "CP", "470uF 10V", 33.02, 41.91, 0, {"1": "VBAT", "2": "GND"}),
])
UTAMA_KEEPOUT = [(12.5, 14.0, 23.0, 21.0)]   # di bawah antena ESP32

DAYA = dict(w=28, h=44, notch=0, parts=[
    ("J1", "H6", "Ke kotak 1", 10.16, 7.62, 0, J1_NET),
    ("JT", "H3", "DS18B20 (kabel)", 5.08, 12.7, 0, {"1": "TEMP_DQ", "2": "3V3", "3": "GND"}),
    ("R8", "R", "1k", 13.97, 7.62, 0, {"1": "GPS_EN", "2": "Q3_B"}),
    ("R9", "RV", "10k", 21.59, 2.54, -90, {"1": "3V3", "2": "Q3_B"}),
    ("Q3", "Q", "S8550", 25.4, 2.54, -90, {"1": "3V3", "2": "Q3_B", "3": "GPS_VCC"}),
    ("C4", "C", "100nF", 19.05, 12.7, -90, {"1": "GPS_VCC", "2": "GND"}),
    ("JGPS", "H3", "GPS NEO-6M", 24.13, 12.7, 0, {"1": "GPS_VCC", "2": "GPS_TX", "3": "GND"}),
    ("JSW", "H2", "Saklar ON/OFF", 10.16, 25.4, 0, {"1": "VBAT", "2": "FUSED"}),
    ("F1", "PF", "Polyfuse 1A", 10.16, 31.75, -90, {"1": "FUSED", "2": "TP_OUT"}),
    ("JTO", "H2", "TP4056 OUT", 10.16, 41.91, 90, {"1": "TP_OUT", "2": "GND"}),
    ("D1", "D", "1N5819", 17.78, 36.83, 0, {"1": "SOLAR_IN", "2": "SOLAR_RAW"}),
    ("JTI", "H2", "TP4056 IN", 17.78, 41.91, 90, {"1": "SOLAR_IN", "2": "PV_MIN"}),
    ("JPV", "H2", "Panel surya", 23.495, 41.91, 90, {"1": "PV_MIN", "2": "SOLAR_RAW"}),
])

# VBAT dilarang lewat sisi kiri papan utama (biar area tombol/LED tetap terhubung ke GND)
UTAMA_NET_KEEPOUT = {"VBAT": [(0, 7.0, 9.0, 47.0), (0, 44.0, 12.0, 54.0), (26.6, 30.0, 34.0, 40.3)]}
