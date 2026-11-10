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
- Modul buzzer aktif dengan pin `SIG`, `VCC`, dan `GND`; `SIG` harus menerima
  logika aktif-tinggi 3,3 V.
- Modul getar tiga pin `IN`, `VCC`, dan `GND` dengan driver internal; `IN`
  harus kompatibel dengan logika aktif-tinggi 3,3 V.
- Jika perangkatnya hanya motor getar PS dua-kabel tanpa modul driver, perlu
  driver terpisah yang sesuai. Jangan tertukar dengan modul analog joystick.
- Catu DC bench terisolasi dan current-limited bila modul membutuhkan suplai
  terpisah. Tegangan harus sesuai rating modul. Jangan gunakan baterai.
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
| GPIO3 (`BUZ_CTRL`) | Ke `SIG`/input modul buzzer aktif yang kompatibel 3,3 V |
| GPIO4 (`MOT_CTRL`) | Ke `IN` modul getar tiga-pin (driver internal) |
| GND | Ke katoda ketiga LED dan GND ESP32, buzzer, dan driver getar |
| 3V3 atau 5V | Ke `VCC` modul sesuai rating yang tercetak/datasheet; jangan menebak |
| GPIO6 (`BTN`) | Opsional: tombol antara GPIO6 dan GND; firmware PCB memakai tombol aktif-rendah sebagai hold-to-enable |
| USB | Ke ESP32-C3 saja; jangan sambungkan ke PCB kalung atau rel baterai |

Setiap LED harus memiliki resistor seri sendiri. Jangan menyatukan anoda LED
merah/kuning/hijau ke satu resistor. Pada setup ini GPIO7 merah, GPIO21 kuning,
dan GPIO10 hijau dikendalikan firmware sebagai status risiko. GPIO7 dan GPIO21
tidak dirutekan pada PCB kalung v1, jadi LED merah/kuning hanya bekerja pada
ESP32-C3 lepas di breadboard. Jangan menambah wiring ini ke PCB kalung.

`SIG` buzzer dan `IN` modul getar tiga-pin adalah input logika, bukan terminal
beban. Karena modul getar sudah memiliki driver, GPIO4 dapat dihubungkan
langsung ke `IN`; tidak perlu papan driver tambahan. Pastikan kedua input
menerima sinyal aktif-tinggi 3,3 V dari ESP32. Hubungkan VCC modul ke rel 3V3
atau 5V hanya jika sesuai ratingnya dan sumbernya mampu menyuplai arus modul.
Gunakan catu bench current-limited terpisah bila perlu, dengan GND bersama.
Jangan memberi daya motor mentah dari GPIO atau pin daya ESP32.

Lihat [gambar pinout dan wiring](../diagrams/esp32-c3-super-mini-led-pinout.png).
Gambar menghadap sisi komponen dengan USB-C di bawah. Ikuti nama GPIO tercetak
pada board; jangan menentukan pin hanya dari posisi fisik bila revisi board
berbeda.

Hanya jika yang tersedia adalah motor dua-kabel tanpa modul driver, gunakan
driver terpisah sesuai motor dan ikuti diagram/pinout drivernya:

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

1. Dengan semua daya terputus, periksa polaritas LED, jalur ground, dan label
   pin modul. Biarkan VCC modul terputus.
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
5. Setelah rating modul dan kebutuhan arusnya dipastikan, sambungkan VCC ke
   suplai yang sesuai dan current-limited. Jangan lanjutkan bila rating modul
   atau kemampuan sumber dayanya tidak diketahui.
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
- Pada GNSS valid, `CAUTION` memberi pulsa getar GPIO4 saja. `DANGER`
  mengaktifkan GPIO3 (buzzer) dan GPIO4 (getar) bersama. GPIO6 harus ditahan
  untuk mengizinkan cue; reset, fix tidak valid, atau tombol yang dilepas
  menonaktifkan keluaran. Setiap pulsa maksimum 500 ms.
- Transisi baru ke `DANGER` boleh melewati cooldown 30 detik agar cue bahaya
  tidak menunggu. Pengulangan pada tingkat risiko yang sama tetap mengikuti
  cooldown. Mode mock memaksa GPIO4 tetap mati, jadi replay dashboard tidak
  membuktikan getaran.
- Jangan menjumper GPIO3/GPIO4 untuk melewati pembatas firmware. Jika perlu
  menguji modul sebelum ada GNSS valid, gunakan firmware uji bench terpisah
  yang dibatasi dan ditinjau terlebih dahulu.

Setup ini hanya memvalidasi rangkaian di meja. Ini bukan uji efektivitas perilaku
hewan dan bukan perangkat keselamatan jalan.
