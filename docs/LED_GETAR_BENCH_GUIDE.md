# Panduan bench LED dan getar BALAT (tanpa baterai/solar)

Panduan ini untuk uji meja awal dengan **ESP32-C3 Super Mini terpisah di
breadboard**, bukan untuk menyalakan PCB kalung BALAT v1. Baterai 18650,
TP4056, dan panel surya boleh dilewati seluruhnya.

> **Jangan hubungkan USB ke PCB kalung v1.** Review PCB masih berstatus HOLD:
> jalur VBAT terhubung ke pin 5V ESP32-C3 dan berpotensi bertemu USB VBUS.
> Jangan rakit atau beri daya ke PCB kalung sebelum temuan power-path dan DRC
> ditutup. Lihat [review PCB](./PCB_LAYOUT_REVIEW_2026-11-08.md) dan
> [panduan PCB](../BALAT_PCB_v1/BALAT_PCB_v1/PANDUAN_PCB.md).

## Komponen untuk setup terpisah

- ESP32-C3 Super Mini dan kabel USB data; USB hanya memberi daya ke board ini.
- Breadboard dan kabel jumper.
- LED merah, kuning, dan hijau; masing-masing memakai resistor seri 220 Ω
  tersendiri.
- Driver motor siap pakai yang menerima logika 3,3 V dan memiliki proteksi
  beban induktif/flyback, dengan rating sesuai motor.
- Motor getar/rumble yang dilepas dari stik/controller PlayStation bekas
  (motor DC kecil dengan pemberat eksentrik), dengan tegangan kerja dan arus
  stall yang diketahui. Jangan tertukar dengan modul analog joystick.
- Catu DC bench terisolasi dan current-limited untuk motor; setel sesuai
  spesifikasi motor dan driver. Jangan gunakan baterai.
- Multimeter. Tombol tekan opsional untuk GPIO6 jika memakai firmware demo
  yang memerlukan hold-to-enable.

Motor dari controller berbeda boleh memiliki rating berbeda. Jangan menebak
tegangan dari bentuk/ukuran motor atau tegangan USB/controller; cek label,
datasheet, atau spesifikasi komponen terlebih dahulu. Jika rating tegangan,
arus stall, atau rating driver belum diketahui, jangan menyalakannya. Jangan
menghubungkan motor langsung ke GPIO ESP32.

Saat melepas motor dari controller, pastikan controller sudah dicabut dan
baterainya dilepas. Hindari merusak atau menjepit pemberat kecil yang menempel
pada poros motor. Isolasi kedua kabel motor agar tidak saling menyentuh.

## Wiring breadboard

Matikan USB dan catu motor saat memasang kabel. Cocokkan label pin pada board
ESP32-C3 yang dipakai; jangan mengandalkan posisi pin tanpa memeriksa silkscreen.

| ESP32-C3 | Sambungan |
|---|---|
| GPIO7 | Ke resistor 220 Ω, lalu ke anoda LED merah |
| GPIO21 | Ke resistor 220 Ω, lalu ke anoda LED kuning |
| GPIO10 | Ke resistor 220 Ω, lalu ke anoda LED hijau |
| GND | Ke katoda ketiga LED dan GND logika driver motor |
| GPIO4 (`MOT_CTRL`) | Ke input logika driver motor (`IN`/`SIG`) |
| GPIO6 (`BTN`) | Opsional: tombol antara GPIO6 dan GND; firmware PCB memakai tombol aktif-rendah sebagai hold-to-enable |
| USB | Ke ESP32-C3 saja; jangan sambungkan ke PCB kalung atau rel baterai |

Setiap LED harus memiliki resistor seri sendiri. Jangan menyatukan anoda LED
merah/kuning/hijau ke satu resistor. Pada setup ini GPIO7 merah, GPIO21 kuning,
dan GPIO10 hijau dikendalikan firmware sebagai status risiko. GPIO7 dan GPIO21
tidak dirutekan pada PCB kalung v1, jadi LED merah/kuning hanya bekerja pada
ESP32-C3 lepas di breadboard. Jangan menambah wiring ini ke PCB kalung.

Lihat [gambar pinout dan wiring](../diagrams/esp32-c3-super-mini-led-pinout.png).
Gambar menghadap sisi komponen dengan USB-C di bawah. Ikuti nama GPIO tercetak
pada board; jangan menentukan pin hanya dari posisi fisik bila revisi board
berbeda.

Sambungkan sisi motor mengikuti diagram/pinout driver yang digunakan:

```text
ESP32 GPIO4 ──> IN driver
ESP32 GND ─────> GND driver ─────> negatif catu motor
positif catu motor ─────────────> VM/V+ driver
motor ──────────────────────────> OUT driver
```

Ground ESP32 dan ground catu motor harus tersambung bersama melalui GND driver
agar sinyal GPIO4 memiliki referensi yang sama. **Jangan** menyambungkan
positif catu motor ke pin 3V3 atau 5V ESP32. Jangan menambah dioda eksternal
tanpa memeriksa apakah driver sudah memilikinya dan mengikuti dokumentasi
driver.

## Urutan uji

1. Dengan semua daya terputus, periksa polaritas LED, jalur ground, serta
   sambungan `IN`, `VM/V+`, dan `OUT` pada driver. Motor tetap dilepas.
2. Nyalakan ESP32-C3 dari USB saja. Pastikan tidak ada hubungan singkat antara
   3V3 dan GND.
3. Uji tiga LED terlebih dahulu dengan mock trace. Statusnya: hijau = SAFE,
   kuning = CAUTION/COOLDOWN, merah = DANGER, dan merah berkedip saat INVALID.
   Semua output LED aktif-tinggi. Matikan USB sebelum memperbaiki wiring.
4. Replay mock tidak menghasilkan pulsa GPIO4. Verifikasi sinyal kontrol hanya
   saat firmware menerima fix GNSS normal yang valid dan memang menghasilkan
   cue; biarkan catu motor mati dan gunakan indikator input driver atau alat
   ukur. Jika belum ada jalur uji tersebut, berhenti setelah uji LED—jangan
   memaksa GPIO4 dengan jumper.
5. Setelah tegangan kerja dan arus stall motor rumble diketahui, pastikan
   keduanya berada dalam rating driver. Sambungkan motor saat catu masih mati,
   atur tegangan dan current limit bench supply sesuai spesifikasi motor serta
   driver, lalu nyalakan. Jika rating motor tidak dapat ditemukan, jangan
   lanjutkan uji dengan daya.
6. Lepas catu atau USB segera bila ada panas, bau, reset ESP32, atau arus tak
   terduga.
7. Lepaskan tombol GPIO6 untuk menonaktifkan cue kapan saja. Jauhkan semua uji
   dari hewan dan lalu lintas.

## Batasan firmware saat ini

- Replay dashboard/USB (`MOCK`, NMEA sintetis, atau demo replay) dapat
  memperlihatkan LED status, tetapi firmware **memaksa GPIO4/motor tetap mati**
  pada mode mock. Jadi replay bukan cara untuk membuktikan getaran.
- Pada jalur GNSS normal, cue dibatasi maksimum 500 ms dengan jeda minimum
  30 detik. GPIO6 harus ditahan untuk mengizinkan cue; reset, fix tidak valid,
  atau tombol yang dilepas menonaktifkan keluaran.
- Cue normal firmware juga mengaktifkan keluaran buzzer GPIO3. Untuk uji ini
  jangan sambungkan buzzer. Jangan menjumper GPIO4 untuk melewati pembatas
  firmware. Jika uji getar perlu dilakukan sebelum ada GNSS valid, gunakan
  firmware uji bench terpisah yang dibatasi dan ditinjau terlebih dahulu.

Setup ini hanya memvalidasi rangkaian di meja. Ini bukan uji efektivitas perilaku
hewan dan bukan perangkat keselamatan jalan.
