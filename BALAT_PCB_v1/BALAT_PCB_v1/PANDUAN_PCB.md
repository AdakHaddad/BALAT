# PCB BALAT v1: panduan singkat

> **HOLD — jangan fabrikasi atau nyalakan PCB v1 sebelum review power-path/DRC ditutup.** Profil firmware ESP32-C3 kini sesuai dengan net signal PCB; pinout bukan lagi kendala firmware. Ringkasan temuan: [`../../docs/PCB_LAYOUT_REVIEW_2026-11-08.md`](../../docs/PCB_LAYOUT_REVIEW_2026-11-08.md). Ikuti [`../../docs/ESP32_ASSEMBLY_DEMO.md`](../../docs/ESP32_ASSEMBLY_DEMO.md) untuk integrasi bench yang dibatasi.
>
> Untuk uji LED dan motor getar tanpa baterai/solar, gunakan setup breadboard
> terpisah pada [`panduan bench LED dan getar`](../../docs/LED_GETAR_BENCH_GUIDE.md).
> Panduan bench tersebut tidak menyalakan PCB kalung v1.

Per kalung ada 2 PCB, masing-masing 1 lapis tembaga, semua komponen tusuk (THT):

| PCB | Kotak | Ukuran | Isi |
|---|---|---|---|
| PCB UTAMA | Kotak 1 | 54 × 54 mm (sudut dicoak 7,5 mm untuk tiang baut tutup) | ESP32-C3, buzzer, driver buzzer dan motor, pembagi tegangan baterai, LED |
| PCB DAYA | Kotak 2 | 28 × 44 mm (di samping dudukan 18650) | Dioda panel, polyfuse, saklar GPS (S8550), titik sambung TP4056, GPS, DS18B20 |

Kotak 3 (motor) tidak butuh PCB. Kapasitor 100 nF disolder langsung di kedua kaki motor.

Untuk 2 kalung, cetak masing-masing PCB 2 kali. Isi `CETAK_SETRIKA_A4.pdf` sudah 2 × utama + 2 × daya. Semua muat di PCB polos 1 sisi ukuran 10 × 15 cm.

## 1. Membuat PCB (setrika / jasa lokal)

1. Cetak `CETAK_SETRIKA_A4.pdf` dengan **printer laser** di kertas glossy/foto.
   - Skala **100%**, matikan "fit to page".
   - **Jangan dicerminkan.**
   - Ukur garis skala, harus tepat 50 mm.
2. Gosok PCB polos sampai mengkilap, setrika 3–5 menit, rendam air, lalu kelupas kertasnya.
   - Tulisan "BALAT-U v1" / "BALAT-D v1" di tembaga harus **terbaca normal**. Kalau terbalik, berarti cetakan tercermin.
3. Larutkan di FeCl3, bersihkan toner, lalu bor:
   - **0,8 mm** untuk resistor, kapasitor kecil, transistor, LED.
   - **1,0 mm** untuk ESP32, header, buzzer, dioda, dan semua lubang kabel.
4. Kalau pakai jasa cetak PCB, kirim isi folder `utama/gerber` dan `daya/gerber` (Gerber + file bor), atau PDF tadi.

## 2. Memasang komponen

Lihat `PETA_KOMPONEN.pdf`. Gambar di sana dilihat dari sisi komponen, dengan pad kotak = kaki nomor 1.

Polaritas:
- **Transistor (Q1, Q2, Q3):** kaki E ke pad kotak, urutan E-B-C. Q3 = S8550 (PNP), jangan tertukar dengan S8050.
- **Dioda 1N5819 (D1, D2):** garis katoda ke pad kotak.
- **LED D3:** kaki pendek (katoda) ke pad kotak.
- **Elco C1:** kaki + ke pad kotak.
- **Buzzer:** kaki + ke pad kotak.

Tinggi komponen di kotak 1 (ruang ±12 mm di atas PCB):
- ESP32-C3 disolder langsung pakai pin header jantan, **tanpa soket perempuan** (soket membuat tumpukan ±15 mm, tidak muat).
- Elco 470 µF direbahkan, atau pakai 470 µF 6,3 V ukuran 6,3 × 11 mm.

Resistor R1, R2, R5, R7, R10, R9 dipasang **berdiri**. Resistor lain tidur.

## 3. Kabel antar-papan dan ke luar PCB

Semua lubang konektor berjarak 2,54 mm. Kabel boleh disolder langsung ke lubang (lebih tahan getar), atau pakai header/JST.

| Dari | Ke | Catatan |
|---|---|---|
| J1 PCB utama (EN, TX, DQ, 3V3, GND, VBAT) | J1 PCB daya, urutan sama | 6 kabel lewat engsel 1 |
| J2 PCB utama (M−, M+) | Motor PS di kotak 3 | Lewat kotak 2 dan engsel 2; 100 nF di kaki motor |
| J3 PCB utama (BTN, GND) | Tombol "mode lapor" di dinding kotak 1 | |
| JSW PCB daya (SW, SW) | Saklar geser ON/OFF | Kaki tengah + salah satu kaki samping |
| JTO PCB daya (OUT+, OUT−) | OUT+ / OUT− modul TP4056 | |
| JTI PCB daya (IN+, IN−) | IN+ / IN− modul TP4056 | |
| JPV PCB daya (PV+, PV−) | Ujung + dan ujung − rangkaian seri 3 panel | |
| JGPS PCB daya (VCC, TX, GND) | VCC, TX, GND modul GY-NEO6MV2 | RX modul dibiarkan |
| JT PCB daya (DQ, VDD, GND) | DS18B20 lewat kabel pendek | Tempelkan ke badan baterai |
| Baterai 18650 | B+ / B− modul TP4056 langsung | Tidak lewat PCB |

**Penting:** IN− TP4056 = B− (sebelum proteksi). PCB sengaja tidak menyambungkannya ke GND sistem (OUT−), supaya proteksi baterai tetap bekerja.

**Jangan sambungkan USB saat baterai/TP4056 terpasang atau saklar ON.** Net `VBAT` PCB terhubung ke pin `5V` modul Super Mini; USB VBUS dapat tersambung langsung ke rel baterai. Saklar OFF saja bukan pengganti revisi power-path dan verifikasi skematik modul yang dipakai. Untuk demo firmware sekarang gunakan Super Mini terpisah di breadboard dan daya USB saja.

## 4. Status pemeriksaan desain

Pernyataan pemeriksaan lama pada bagian ini sudah usang. DRC baru dengan KiCad
8.0.9 menemukan **7 error courtyard overlap** di PCB utama dan **2 error** di
PCB daya; masing-masing papan masih melaporkan 0 item tidak tersambung. Jika
peringatan ikut dihitung, ditemukan juga banyak masalah silkscreen dan
definisi library footprint lokal. Lihat laporan ringkas di
[`../../docs/PCB_LAYOUT_REVIEW_2026-11-08.md`](../../docs/PCB_LAYOUT_REVIEW_2026-11-08.md).

Pemetaan firmware ESP-IDF untuk profil PCB kini cocok dengan netlist: GPIO3
buzzer, GPIO4 motor, GPIO5 GPS power, GPIO6 tombol, GPIO10 LED, GPIO20 GPS TX
(menuju UART RX). Tombol GPIO6 dipakai sebagai hold-to-enable cue saat demo
bench; lepaskan tombol untuk mematikan keluaran. Tetap **HOLD** fabrikasi dan
power-up sampai temuan jalur daya serta DRC ditinjau dan diselesaikan. Jangan
sambungkan baterai/TP4056/solar atau aktuator sebelum power-path diverifikasi.

## 5. Mengubah desain

Folder `generator/` berisi skrip Python (butuh KiCad 7 + modul `pcbnew`):
- `tata_letak.py`: posisi komponen.
- `jalankan.py`: membangun, merutekan, cek DRC, dan ekspor ulang.
