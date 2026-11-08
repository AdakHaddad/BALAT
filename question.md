# BALAT — Bank Pertanyaan Juri (Pitch Deck)

Kumpulan pertanyaan yang mungkin muncul dari juri hackathon atau business pitching, dari yang paling umum sampai yang "tidak pernah terbayang". Setiap pertanyaan diberi **poin jawaban** berdasarkan desain BALAT saat ini.

Tanda **[isi data]** berarti jawabannya harus diisi dengan data asli dari uji coba, wawancara, atau sumber resmi. Jangan diisi dengan tebakan.

---

## Cara memakai dokumen ini

**Pola jawaban 30 detik:**
1. **Inti jawaban**, dalam satu kalimat.
2. **Bukti**: data uji, angka, atau sumber.
3. **Batasan yang jujur**: yang belum terbukti.
4. **Langkah berikutnya**: bagaimana batasan itu akan diatasi.

**Aturan emas:**
- Kalau tidak tahu, katakan: "Itu belum kami uji. Rencananya kami uji di tahap X dengan cara Y." Juri lebih menghargai ini daripada jawaban mengarang.
- Jangan pernah mengklaim sesuatu yang belum diuji sebagai fakta (misalnya "sapi pasti patuh").
- Siapkan **slide cadangan (backup)** untuk pertanyaan teknis yang berat: perhitungan daya, simulasi HerdSync, data uji.

**10 pertanyaan yang WAJIB dikuasai** (ditandai ⭐ di bawah):
masalah nyata, kenapa tanpa LoRa, apakah sapi patuh tanpa kejutan listrik, umur baterai, harga dan siapa yang membayar, beda dengan kompetitor, TKT dan bukti uji, data sampai berapa lama, kesejahteraan hewan, rencana setelah lomba.

---

## 1. Masalah dan validasi

1. ⭐ **Masalah apa yang sebenarnya kalian selesaikan? Seberapa besar?**
   - Ternak keluar area (masuk kebun warga, jalan raya, jurang, hutan), lalu hilang, celaka, atau memicu konflik antar-warga.
   - [isi data]: jumlah ternak, kasus ternak hilang atau kecelakaan, kerugian per kasus. Sumber: BPS, dinas peternakan, wawancara.
2. **Siapa yang paling merasakan masalah ini?**
   - Peternak kecil dan menengah dengan sistem gembala atau angon, serta peternak di lahan luas tanpa pagar.
3. **Sudah bicara dengan berapa peternak? Apa kata mereka?**
   - [isi data]: jumlah wawancara, lokasi, kutipan nyata, masalah nomor satu menurut mereka.
4. **Bagaimana peternak menyelesaikan masalah ini sekarang?**
   - Pagar fisik (mahal, kaku), digembalakan orang (biaya tenaga), diikat (ruang gerak terbatas, sapi stres).
   - [isi data]: biaya pagar per meter atau upah penggembala per bulan di daerah sasaran.
5. **Kenapa masalah ini belum terselesaikan sampai sekarang?**
   - Solusi pagar virtual yang ada mahal, bergantung pada sinyal seluler, LoRa, atau satelit, dan belum dirancang untuk peternak kecil di Indonesia.
6. **Apakah peternak benar-benar mau membayar untuk ini, atau hanya bilang "bagus"?**
   - [isi data]: tanyakan harga yang mau mereka bayar dan bandingkan dengan biaya pagar atau penggembala. Lebih kuat lagi kalau ada surat minat atau komitmen uji coba (LoI).
7. **Kalau BALAT tidak ada, apa yang hilang dari hidup peternak?**
   - Jawab dengan cerita satu peternak nyata, bukan dengan angka.

## 2. Solusi dan cara kerja

8. **Jelaskan BALAT dalam satu kalimat.**
   - "Kalung pintar bertenaga surya yang memberi peringatan suara dan getar saat sapi mendekati batas yang ditentukan peternak, dan tetap bekerja tanpa sinyal."
9. **Jelaskan cara kerjanya dari awal sampai akhir.**
   - Kalung membaca GPS, lalu membandingkan posisi dengan zona yang tersimpan. Saat sapi mendekati batas: bunyi. Saat melewati batas: bunyi dan getar. Kejadian disimpan, lalu dititipkan antar-kalung (HerdSync) sampai ke gateway, dan peternak melihatnya di HP.
10. **Kenapa keputusan diambil di kalung, bukan di server?**
    - Supaya peringatan tetap jalan walaupun tidak ada sinyal sama sekali. Internet hanya dipakai untuk melapor, bukan untuk mengendalikan sapi.
11. **Bagaimana peternak menggambar atau mengatur zona?**
    - Lewat halaman di HP yang tersambung ke Wi-Fi lokal gateway, tanpa perlu internet. Zona dikirim ke kalung lewat HerdSync.
    - Batasan saat ini: [isi status], misalnya zona masih diatur lewat program.
12. **Apa yang terjadi kalau sapi sudah terlanjur di luar batas?**
    - Ini penting. Kalung **tidak boleh terus menghukum** sapi yang sudah di luar, karena sapi bisa terjebak dan tidak mau kembali. Rancangannya: peringatan berhenti setelah jarak atau waktu tertentu, lalu kalung mengirim status "sapi keluar" ke peternak.
    - [isi status implementasi].
13. **Bagaimana sapi tahu harus kembali ke arah mana?**
    - Versi sekarang memakai sinyal "berhenti, putar balik". Mode arah (getar atau bunyi kiri-kanan dengan sensor kompas) adalah pengembangan berikutnya.
    - Produk komersial seperti Halter memakai suara kiri-kanan sebagai penunjuk arah.

## 3. Teknologi

14. ⭐ **Kenapa tidak pakai LoRa, NB-IoT, atau satelit?**
    - LoRa butuh gateway dan modul tambahan (biaya, daya). Seluler butuh sinyal yang sering tidak ada di padang. Satelit mahal.
    - HerdSync memanfaatkan radio yang **sudah ada** di ESP32-C3 (ESP-NOW/BLE), tanpa tambahan hardware. Sapi saling menitipkan data sampai ke gateway.
15. **Apa itu HerdSync? Apa bedanya dengan mesh biasa?**
    - HerdSync adalah DTN (*delay-tolerant network*): data disimpan, dibawa, lalu diteruskan saat kalung bertemu. Mesh biasa butuh semua node tersambung terus-menerus. DTN tidak, jadi lebih cocok untuk sapi yang berpencar dan radio yang tidur untuk hemat baterai.
16. **Berapa lama data sampai ke peternak?**
    - Tergantung seberapa sering sapi saling bertemu atau mendekati gateway.
    - [isi data dari simulasi]: % data sampai dan rata-rata tunda, untuk jumlah sapi dan sebaran tertentu.
    - Yang penting: keterlambatan data **tidak membahayakan sapi**, karena peringatan sudah terjadi di kalung.
17. **Seberapa akurat GPS-nya? Cukup untuk batas jurang atau jalan?**
    - Modul kelas NEO-6M umumnya akurat beberapa meter di langit terbuka. Karena itu ada zona waspada sekitar 20 m sebelum batas, sebagai penyangga.
    - [isi data uji]: sebaran titik GPS saat kalung diam di satu tempat.
18. **Bagaimana kalau sinyal GPS hilang, misalnya di bawah pohon lebat atau di kandang?**
    - Kalung memakai posisi terakhir yang valid dan tidak memberi peringatan dari data yang meragukan. Saat GPS hilang lama, kalung mengirim status ke peternak.
    - [isi status implementasi].
19. ⭐ **Berapa lama baterainya tahan?**
    - Kebutuhan sekitar 71 mAh per hari. Panel 3 × 2V seri menghasilkan sekitar 156–260 mAh per hari, jadi masih surplus.
    - Baterai 18650 (2000–3000 mAh) cukup sekitar 3–4 minggu **tanpa matahari sama sekali**.
    - [isi data uji nyata].
20. **Bagaimana kalau musim hujan, mendung berminggu-minggu?**
    - Cadangan baterai 3–4 minggu. Kalung juga bisa masuk mode hemat: GPS dibaca lebih jarang, dan sisa baterai dilaporkan lewat HerdSync.
21. **Komponen apa yang paling boros daya?**
    - GPS, sekitar 56% dari total. GPS dimatikan total lewat saklar transistor di antara pembacaan. Kalau dibaca tiap 10 menit (bukan 5), kebutuhan turun ke sekitar 42 mAh per hari.
22. **Seberapa jauh jangkauan antar-kalung?**
    - Radio 2,4 GHz teredam badan sapi, jadi di lapangan jangkauannya lebih pendek dari spesifikasi.
    - [isi data uji jangkauan di lapangan terbuka dan di dekat sapi].
23. **Kalau ada 100 sapi, apakah sinyal saling bertabrakan?**
    - Radio bangun serentak berdasarkan jam GPS, dengan jeda acak sebelum mengirim. Kalung saling bertukar daftar data dulu, lalu hanya mengirim yang belum dimiliki lawannya.
    - Batas sebenarnya adalah kepadatan sinyal, bukan jumlah perangkat. Untuk kawanan besar: bagi wilayah per gateway.
24. **Memori kalung cukup untuk berapa sapi?**
    - Posisi disimpan satu slot terbaru per sapi (sekitar 18 byte). Kejadian penting disimpan sampai terkirim. Data yang sudah sampai dihapus lewat daftar ACK dari gateway. Dengan aturan ini, cukup untuk ratusan sapi.
25. **Bagaimana keamanan datanya? Bisakah diretas, misalnya ada orang yang mengirim zona palsu?**
    - Versi prototipe belum dienkripsi. Rencana: enkripsi ESP-NOW dan tanda tangan (autentikasi) untuk perintah zona, sehingga hanya gateway resmi yang bisa mengubah zona.
26. **Bisakah orang menggiring sapi curian memakai kalung ini?**
    - Kalung hanya memberi peringatan di batas yang tersimpan. Perubahan zona harus terautentikasi (lihat no. 25). Ini justru alasan fitur keamanan wajib ada sebelum produk dijual.
27. **Apa yang terjadi kalau gateway mati, misalnya listrik kandang padam?**
    - Kalung tetap bekerja penuh (peringatan dan penyimpanan data). Data menunggu sampai gateway hidup lagi. Gateway bisa diberi powerbank atau UPS kecil.
28. **Bagaimana kalau ESP32 hang atau error?**
    - Watchdog timer me-restart otomatis. Zona tersimpan di memori yang tidak hilang saat restart.
29. **Kenapa ESP32-C3, bukan mikrokontroler lain?**
    - Murah, mudah didapat, sudah ada Wi-Fi dan BLE untuk HerdSync dan Wi-Fi lokal, deep sleep hemat, ukuran kecil.
30. **Apakah alat ini tahan air, panas, dan benturan?**
    - Segel silikon, cable gland, silica gel, PCB dilapis, bumper karet, akrilik pelindung panel, box warna terang, sensor suhu baterai.
    - [isi data uji]: suhu box saat dijemur, uji siram air, uji jatuh.
31. **Kenapa engselnya di bawah (sisi kulit)?**
    - Supaya ketiga box bisa melengkung mengikuti bulatnya leher. Sudah dicek di model 3D: bisa menekuk sampai 40° tanpa bertabrakan.

## 4. Kesejahteraan hewan dan etika

32. ⭐ **Apakah sapi akan patuh hanya dengan bunyi dan getar, tanpa kejutan listrik?**
    - Jawab jujur: **ini hipotesis utama kami yang sedang diuji.**
    - Penelitian menunjukkan sapi cenderung terbiasa dengan sinyal yang hanya berupa suara. Karena itu BALAT memakai getaran yang makin kuat sebagai pengganti kejutan.
    - [isi data uji TKT 5]: reaksi sapi, berapa kali diabaikan, perubahan dari hari ke hari.
33. **Kenapa tidak pakai kejutan listrik seperti produk luar negeri?**
    - Lebih ramah hewan, lebih aman (tanpa tegangan tinggi), dan lebih mudah diterima peternak dan masyarakat. Konsekuensinya, efektivitasnya harus dibuktikan lewat uji.
34. ⭐ **Apakah kalung ini membuat sapi stres atau sakit?**
    - Peringatan hanya muncul di dekat batas. Sebagian besar waktu kalung diam.
    - Ada bantalan karet, tepi membulat, dan bobot ringan (sekitar 300–400 g total). Sebagai pembanding, satu perangkat komersial sekitar 725 g.
    - [isi data]: pemantauan perilaku, nafsu makan, luka kulit selama uji.
35. **Bagaimana kalau kalung tersangkut pagar atau ranting dan mencekik sapi?**
    - Perlu **gesper lepas otomatis** (*breakaway*) yang terbuka kalau tertarik sangat kuat. Ini harus masuk desain sebelum uji lapangan.
36. **Sudah punya izin etik untuk uji ke hewan?**
    - [isi status ethical clearance]. Uji di sapi asli dilakukan setelah izin keluar.
37. **Bagaimana dengan anak sapi atau sapi bunting?**
    - Ukuran kalung disesuaikan, dan intensitas getar bisa diatur per kalung. Untuk sapi bunting tua, perlu konsultasi dokter hewan. [isi rencana].

## 5. Validasi, TKT, dan bukti

38. ⭐ **TKT berapa sekarang? Apa buktinya?**
    - [isi]: TKT 4 = tiap subsistem divalidasi di lab: GPS dan geofence, peringatan (dB, akselerasi getar), HerdSync dengan 3 ESP32, pengisian surya, daya harian.
    - Tunjukkan tabel hasil uji dan video.
39. **Apa yang membedakan TKT kalian sekarang dengan TKT 6?**
    - TKT 5: subsistem diuji di kandang atau lapangan. TKT 6: seluruh sistem (2–3 kalung dan gateway) diuji di sapi asli. [isi jadwal].
40. **Uji apa yang sudah dilakukan, dan apa yang gagal?**
    - Siapkan cerita kegagalan dan perbaikannya. Juri menyukai tim yang belajar dari kegagalan.
41. **Simulasi kalian realistis atau tidak?**
    - Jujur soal batasannya: gerakan sapi disederhanakan, dan radio dianggap ideal. Langkah berikutnya: memakai data GPS sapi asli dan data jangkauan nyata.
42. **Kalau di uji lapangan ternyata sapi mengabaikan peringatan, apa rencana kalian?**
    - Ubah pola peringatan (nada naik, getar makin kuat, kombinasi kiri-kanan), uji motor yang lebih kuat, dan evaluasi ulang. Hasil negatif tetap data yang berharga.

## 6. Pasar dan bisnis

43. ⭐ **Berapa harga jualnya, dan siapa yang membayar?**
    - Biaya komponen prototipe sekitar Rp350 ribu per kalung (termasuk casing). Di produksi massal biasanya bisa ditekan. [isi harga jual dan margin].
    - Pembayar bisa peternak, kelompok ternak atau koperasi, pemerintah daerah lewat program bantuan, atau perusahaan perkebunan.
44. **Model bisnisnya apa? Jual putus, sewa, atau langganan?**
    - Pilihan: jual kalung + gateway, sewa per ekor per bulan untuk peternak kecil, atau paket untuk kelompok ternak. [isi pilihan dan alasannya].
45. **Siapa pelanggan pertama kalian?**
    - [isi]: nama kelompok ternak, lokasi, dan jumlah sapi untuk uji coba awal.
46. **Seberapa besar pasarnya?**
    - [isi data]: jumlah sapi atau peternak di daerah sasaran (BPS), lalu hitung pasar yang realistis bisa dijangkau dalam 1–3 tahun.
47. ⭐ **Apa bedanya dengan kompetitor?**
    - Produk luar negeri (misalnya Halter, Nofence, eShepherd) mahal dan bergantung pada jaringan seluler, menara khusus, atau satelit, serta umumnya memakai kejutan listrik.
    - BALAT: murah, bekerja tanpa sinyal (HerdSync + Wi-Fi lokal), tanpa kejutan listrik, dan dirancang untuk peternak kecil Indonesia.
    - [isi]: pemain lokal yang serupa, kalau ada.
48. **Kalau perusahaan besar meniru ide kalian, bagaimana?**
    - Keunggulan ada di pemahaman peternak lokal, harga, jaringan distribusi lewat kelompok ternak, dan data uji di kondisi Indonesia. Pertimbangkan juga perlindungan HKI (paten sederhana atau desain industri).
49. **Bagaimana cara menjual ke peternak yang tidak akrab teknologi?**
    - Lewat kelompok ternak, penyuluh peternakan, dan koperasi. Demo langsung di kandang. Antarmuka sederhana: lampu, bunyi, dan SMS.
50. **Kenapa peternak harus percaya pada produk mahasiswa?**
    - Bukti uji, pendampingan dosen dan fakultas, garansi, dan uji coba gratis untuk kelompok pertama.

## 7. Operasional dan produksi

51. **Bagaimana memproduksi 1.000 unit?**
    - PCB dibuat di pabrik (bukan rakitan tangan), casing dicetak injeksi setelah desain stabil, komponen dibeli dalam jumlah besar. [isi rencana].
52. **Siapa yang memasang dan merawat alat di lapangan?**
    - Pelatihan untuk perwakilan kelompok ternak, video tutorial, dan layanan purna jual. [isi rencana].
53. **Berapa umur pakai alat? Apa yang paling cepat rusak?**
    - Perkiraan: baterai 18650 sekitar 2–3 tahun pemakaian harian. Panel bisa tergores. Kabel di engsel perlu dicek berkala. [isi data uji ketahanan].
54. **Kalau kalung hilang atau rusak, siapa yang menanggung?**
    - [isi kebijakan garansi]. Kalung bisa dilacak lewat posisi terakhir yang terekam.
55. **Bagaimana nasib baterai bekas? Tidak menambah sampah elektronik?**
    - Program tukar baterai bekas, desain yang mudah dibongkar (box dengan sekrup, konektor JST), dan komponen yang bisa diganti satu per satu.

## 8. Regulasi dan legalitas

56. **Apakah perangkat radio ini perlu sertifikasi untuk dijual?**
    - Perangkat telekomunikasi yang dijual di Indonesia umumnya perlu sertifikasi dari Kementerian Komunikasi dan Digital. [isi]: cek status sertifikasi modul ESP32 yang dipakai dan prosedur untuk produk jadi.
57. **Siapa pemilik data lokasi ternak?**
    - Peternak. Data tersimpan di gateway lokal milik peternak. Kalau nanti ada layanan cloud, perlu persetujuan dan mengikuti UU Pelindungan Data Pribadi.
58. **Apakah ada aturan kesejahteraan hewan yang perlu dipenuhi?**
    - [isi]: aturan yang berlaku, dan konsultasi dengan dokter hewan atau fakultas terkait.

## 9. Tim

59. **Kenapa kalian tim yang tepat untuk ini?**
    - [isi]: latar teknik elektro, pengalaman IoT, akses ke peternak, pembimbing.
60. **Siapa mengerjakan apa?**
    - [isi pembagian peran]: hardware, firmware, casing 3D, bisnis, lapangan.
61. **Setelah lulus, apakah proyek ini akan dilanjutkan?**
    - [isi rencana nyata dan komitmen tim].
62. **Siapa mentor atau penasihat kalian di bidang peternakan?**
    - [isi]: dosen peternakan, dokter hewan, atau peternak senior.

## 10. Keuangan

63. **Berapa dana yang kalian butuhkan, dan untuk apa?**
    - [isi]: rincian untuk uji lapangan, perbaikan desain, sertifikasi, produksi awal.
64. **Kapan balik modal?**
    - [isi perhitungan]: biaya per unit, harga jual, jumlah unit per tahun.
65. **Kalau diberi Rp100 juta sekarang, apa yang dilakukan pertama kali?**
    - Jawab dengan 3 prioritas yang jelas dan terukur, misalnya: uji lapangan 20 sapi selama 3 bulan, perbaikan desain, persiapan sertifikasi.

## 11. Dampak

66. **Dampak sosial dan lingkungannya apa?**
    - Mengurangi kerugian peternak, konflik antar-warga karena ternak masuk kebun, dan kecelakaan di jalan. Memungkinkan penggembalaan bergilir sehingga lahan lebih terjaga. Tenaga surya.
67. **SDGs mana yang terkait?**
    - Misalnya SDG 1 (tanpa kemiskinan), SDG 2 (tanpa kelaparan), SDG 8 (pekerjaan layak), SDG 15 (ekosistem daratan). Pilih yang paling kuat argumennya.
68. **Bagaimana mengukur keberhasilan dampaknya?**
    - [isi indikator]: jumlah kasus ternak keluar per bulan sebelum dan sesudah, jam kerja penggembala yang dihemat, kerugian yang dicegah.

## 12. Risiko

69. **Apa risiko terbesar proyek ini?**
    - Sapi tidak patuh tanpa kejutan listrik. Ketahanan alat di lapangan. Harga yang belum terjangkau peternak kecil. Siapkan rencana untuk tiap risiko.
70. **Apa asumsi terbesar yang belum terbukti?**
    - Jawab jujur, sama dengan no. 32, dan jelaskan cara mengujinya.
71. **Apa yang bisa membuat proyek ini gagal dalam 2 tahun?**
    - Tunjukkan bahwa tim sudah memikirkan kegagalan: tidak ada pelanggan yang membayar, biaya produksi tidak turun, atau efektivitas tidak terbukti.

## 13. Pertanyaan "di luar dugaan"

72. **Jelaskan BALAT ke anak SD dalam satu kalimat.**
    - "Kalung yang berbunyi dan bergetar supaya sapi tidak tersesat, dan kalung-kalungnya saling titip pesan seperti teman sekelas."
73. **Kenapa namanya BALAT?**
    - [isi cerita di balik nama].
74. **Kalau boleh mengganti satu komponen dengan apa pun tanpa batas biaya, apa yang diganti?**
    - Misalnya: GPS yang jauh lebih hemat daya, karena GPS memakan lebih dari separuh energi.
75. **Bisa dipakai untuk kambing, domba, atau kerbau?**
    - Prinsipnya sama, tapi ukuran, berat, dan pola peringatan harus disesuaikan per hewan dan diuji ulang.
76. **Bagaimana kalau peternak hanya punya 1–2 sapi?**
    - HerdSync kurang berguna kalau sapinya sedikit, tapi peringatan di kalung tetap jalan. Data bisa diambil lewat gateway saku saat peternak mendekat. Model berbasis kelompok ternak (gabungan beberapa peternak) membuatnya lebih ekonomis.
77. **Bagaimana kalau sapi berbaring di atas panel atau menggosokkan leher ke pohon terus-menerus?**
    - Panel ada di atas leher, jadi jarang tertindih. Ada bumper dan pelindung akrilik. [isi data uji ketahanan].
78. **Kenapa tidak pakai HP bekas saja sebagai kalung?**
    - Terlalu berat dan boros baterai, tidak tahan air dan benturan, tidak punya motor getar yang kuat, dan sulit dipasang dengan aman di leher.
79. **Kenapa tidak pakai drone untuk menggiring sapi?**
    - Drone butuh operator, baterainya hanya tahan menit, dan bisa membuat sapi panik. Kalung bekerja 24 jam secara otomatis.
80. **Apa bedanya dengan pelacak seperti AirTag?**
    - Pelacak hanya memberi tahu lokasi, dan butuh jaringan HP orang lain di sekitarnya. BALAT juga **mencegah** sapi keluar, dan bekerja di tempat tanpa orang dan tanpa sinyal.
81. **Bisakah sapi saling "mengajari" untuk menghindari batas?**
    - Sapi adalah hewan kawanan yang cenderung mengikuti sapi lain. Kalau sapi pemimpin belajar menghindari batas, kawanan cenderung ikut. Ini bisa menjadi hal menarik untuk diamati dan dicatat saat uji lapangan.
82. **Bisakah BALAT dipakai di perkebunan sawit (integrasi sapi-sawit)?**
    - Peluang menarik: sapi bisa digembalakan di blok tertentu dan dijauhkan dari tanaman muda. Perusahaan perkebunan juga bisa menjadi pembeli dalam jumlah besar. [isi validasi].
83. **Bisakah membantu saat bencana, misalnya erupsi Merapi?**
    - Posisi terakhir tiap sapi bisa dilihat untuk membantu evakuasi atau pencarian. Zona bahaya bisa ditandai. Ini ide pengembangan, belum diuji.
84. **Bisakah dikembangkan untuk memantau kesehatan sapi?**
    - Bisa: sensor suhu tubuh atau gerakan untuk mendeteksi sapi sakit, birahi, atau tidak bergerak. Data aktivitas juga bisa membantu asuransi ternak. Ini pengembangan, bukan fitur sekarang.
85. **Kalau besok tidak boleh pakai GPS sama sekali, apa yang kalian lakukan?**
    - Alternatif: batas berbasis jarak dari suar (beacon) radio di titik-titik batas. Kalung mengukur kekuatan sinyal suar. Akurasinya lebih rendah, tapi tanpa GPS.
86. **Apakah AI bisa membuat ini dalam semalam? Apa keunggulan kalian?**
    - Merakit prototipe bisa cepat. Yang sulit adalah membuktikan alat bekerja di sapi asli, membuatnya tahan di lapangan, dan membangun kepercayaan peternak. Itu yang tim kerjakan.
87. **Kalau sapinya tuli atau buta?**
    - Getaran tetap terasa walaupun sapi tuli. Peringatan berlapis (suara dan getar) membuat sistem tidak bergantung pada satu indra saja.
88. **Apa yang membuat kalian sendiri ragu dengan proyek ini?**
    - Jawab jujur dengan satu keraguan nyata, lalu jelaskan cara tim mengujinya. Pertanyaan ini menguji kejujuran, bukan mencari kelemahan.
89. **Apa yang akan kalian lakukan berbeda kalau mulai dari awal?**
    - Ceritakan satu pelajaran nyata dari proses desain, misalnya perubahan tata letak baterai atau pemilihan motor getar berdasarkan uji.
90. ⭐ **Apa langkah berikutnya setelah lomba ini?**
    - [isi]: uji lapangan di kandang, perbaikan desain, pilot dengan kelompok ternak, dengan tanggal yang jelas.

---

## Slide cadangan yang sebaiknya disiapkan

- Perhitungan daya harian dan grafik pemakai daya per komponen
- Grafik simulasi HerdSync: data sampai (%) dibanding pengiriman langsung
- Diagram arsitektur 4 lapis (kalung, HerdSync, gateway, aplikasi)
- Foto atau video uji: suara (dB), getar (akselerasi), estafet data dengan 3 ESP32
- Rincian biaya per unit (BOM)
- Tabel perbandingan dengan kompetitor
- Peta jalan TKT 4 → 5 → 6 dengan tanggal

## Catatan sumber

Klaim tentang produk lain sebaiknya dicek ulang dari situs resminya sebelum dipakai di slide:
- Cara kerja isyarat suara dan getar pada Halter: halterhq.com
- Berat perangkat pagar virtual komersial (±725 g) dan temuan bahwa sapi cenderung terbiasa dengan sinyal suara saja: artikel "The application of virtual fencing technology" di jurnal Animal Production Science (connectsci.au)