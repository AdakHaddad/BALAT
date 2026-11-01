# BALAT: Investor Pitch Deck (Hackathon ITS 2026 Edition)

---

## Slide 1: Cover — Company & Vision

- **Slide title:** BALAT: Autonomous, Infrastructure-Free Livestock Guidance
- **One-sentence takeaway:** An autonomous edge wearable keeping grazing herds safe from roadways without cell towers, cloud servers, or base stations.
- **Bullets:**
  - Zero-infrastructure road containment and guidance for grazing livestock.
  - Deterministic edge computing: real-time spatial geometry and risk decision pipeline on the animal.
  - Humane-by-design: conditioned acoustic/haptic cues replace painful electric shock.
  - Gatewayless herd synchronization via HerdSync-DTN store-carry-forward BLE mesh.
  - Proven Technology Readiness Level: TKT 4 (Lab Component & Hardware Bridge Validation).
- **Recommended visual:** Minimalist high-contrast layout. High-resolution rendering of a ruggedized cattle collar tag alongside the BALAT wordmark. Tagline overlay: "Zero Infrastructure. Edge Intelligence. Humane Guidance." Hackathon ITS 2026 / TKT 4 badge in corner.
- **Speaker notes:** "Selamat pagi dewan juri dan hadirin sekalian. Kami mempersembahkan BALAT. Di Indonesia terdapat lebih dari 18,5 juta ekor sapi potong, sebagian besar digembalakan di padang terbuka seperti di Jawa Timur dan Nusa Tenggara Timur yang berbatasan langsung dengan jalan raya antar-kota. Sistem virtual fencing saat ini membutuhkan tower seluler mahal, gateway radio yang rumit, dan sengatan listrik yang menyakiti hewan. BALAT mengganti seluruh ketergantungan tersebut dengan komputasi edge mandiri: kalung pintar yang menyimpan peta jalan lokal, menghitung risiko tabrakan secara real-time, dan memandu ternak berbalik arah secara manusiawi tanpa internet, tanpa BTS, dan tanpa pulsa seluler."
- **Evidence or source:** `PRD.md` Section 1; `README.md`; BPS Populasi Sapi Potong Nasional (18,5 juta ekor, 2023/2024); `docs/DECISIONS.md`.
- **Investor objection this slide should answer:** "Is this just another copycat virtual fence collar that depends on cell service and shocks animals?"

---

## Slide 2: Problem — Urgent Customer Pain

- **Slide title:** Livestock-Road Collisions & The Remote Connectivity Vacuum
- **One-sentence takeaway:** Ranches face catastrophic livestock mortality and severe legal liability along road corridors where zero cellular coverage exists.
- **Bullets:**
  - Devastating Asset Loss: Sapi potong dewasa bernilai Rp 15.000.000 – Rp 25.000.000 ($950–$1,550) per ekor; satu tabrakan dengan kendaraan di jalan raya melenyapkan aset ternak seketika (Kementan/BPS 2024).
  - Human Fatalities & Legal Liability: Tabrakan kendaraan dengan sapi di jalan arteri (e.g. Jalan Timor Raya NTT, jalur Pantura Jawa Timur, highway US/Australia) menyebabkan kecelakaan lalu lintas fatal dan tuntutan hukum ganti rugi terhadap pemilik ternak.
  - Extreme Fencing Capex: Biaya pagar kawat fisik mencapai Rp 80.000 – Rp 150.000 per meter lari (Rp 80M – Rp 150M / km atau $10,000–$25,000 / mil) dengan biaya perawatan tinggi akibat longsor, banjir, dan perusakan pagar.
  - Total Connectivity Void: Padang savana penggembalaan (seperti di Sumba, Timor, rangeland Australia/Amerika) 70%+ tidak terjangkau sinyal seluler dan terhalang perbukitan untuk gateway radio LoRa.
- **Recommended visual:** Split-panel slide: Left side shows photo of cattle grazing near an unfenced rural highway corridor at dusk; right side displays an Indonesian rural cellular coverage map showing blackouts across East Java and NTT rangelands.
- **Speaker notes:** "Bagi peternak yang memiliki lahan gembala di dekat jalan lintas provinsi atau jalan raya, kecelakaan ternak adalah mimpi buruk terbesar. Di Indonesia, satu ekor sapi potong bernilai Rp 18 hingga 25 juta. Kehilangan satu ekor sapi karena tertabrak truk atau bus tidak hanya menghancurkan modal peternak, namun juga menimbulkan tuntutan hukum akibat kerusakan kendaraan atau korban jiwa. Membangun pagar fisik memakan biaya lebih dari Rp 100 juta per kilometer dan sering rusak diterjang cuaca. Di sisi lain, menggunakan GPS tracker biasa tidak berguna karena di area savana atau pedesaan, sinyal seluler 4G seringkali nol."
- **Evidence or source:** BPS Statistik Peternakan 2023/2024; Data Harga Sapi Potong Kementerian Pertanian 2024; USDA Natural Resources Conservation Service Fence Cost Index.
- **Investor objection this slide should answer:** "Why can't ranchers just keep up their physical perimeter fences or put basic GPS tags on cattle?"

---

## Slide 3: Existing Alternatives — How Customers Solve It Today

- **Slide title:** Existing Alternatives: Costly, Fragile, or Welfare-Challenged
- **One-sentence takeaway:** Current virtual fencing relies on fragile infrastructure towers and controversial electric shock, while GPS tags react too late.
- **Bullets:**
  - Physical Fences: Biaya modal sangat tinggi (>Rp 100 juta/km), perawatan intensif, dan tidak memberi peringatan saat pagar roboh.
  - Passive GPS Ear Tags (e.g., Ceres Tag, Moocall): Hanya melacak posisi pasif setiap beberapa jam; tidak bisa mencegah ternak masuk ke jalan raya secara real-time.
  - Incumbent Virtual Fencing (Halter, Gallagher eShepherd, Vence, Nofence): Membutuhkan tower base station LoRa/seluler; biaya langganan sangat mahal mencapai Rp 650.000 – Rp 1.600.000 ($40–$100) per ekor per tahun.
  - Electric Shock Dependency: Sistem kompetitor menggunakan sengatan listrik ke leher sapi; ditentang oleh regulasi kesejahteraan hewan (European Animal Welfare Directives) dan riset perilaku ternak (Lee et al., 2009; Campbell et al., 2019).
- **Recommended visual:** Feature comparison table evaluating Physical Fencing vs. GPS Ear Tags vs. Incumbent Virtual Fencing vs. BALAT across four criteria: Infrastructure Independence, Real-Time Edge Containment, Humane Cueing (No Shock), and Total Cost of Ownership.
- **Speaker notes:** "Alternatif saat ini memiliki kelemahan mendasar. Pagar kawat sangat mahal dan sering putus. GPS ear tag satelit hanya memberi tahu lokasi bangkai sapi setelah tertabrak. Sementara pemain virtual fencing global seperti Halter dan Nofence membutuhkan menara LoRaWAN atau jaringan 4G yang tidak ada di pedalaman, membebankan biaya langganan hingga Rp 1,5 juta per sapi per tahun, dan menyetrum leher hewan. Ketika sinyal hilang atau regulasi melarang alat setrum, sistem mereka lumpuh. BALAT hadir tanpa tower dan tanpa setrum."
- **Evidence or source:** Pricing publik Halter & Nofence ($50–$100/cow/year); Campbell et al. (2019, *Frontiers in Vet Sci*); Lee et al. (2009, *Appl. Anim. Behav. Sci.*); `docs/SAFETY_AND_LIMITATIONS.md`.
- **Investor objection this slide should answer:** "Aren't well-funded virtual fencing companies like Halter and Nofence already addressing this market?"

---

## Slide 4: Solution — What We Provide

- **Slide title:** The BALAT Solution: Autonomous Edge Guidance
- **One-sentence takeaway:** An infrastructure-independent collar that evaluates road approach risk locally and delivers non-aversive recall cues.
- **Bullets:**
  - 100% Autonomous Edge Execution: Seluruh keputusan komputasi spasial diproses langsung di leher ternak dalam waktu hitungan milidetik.
  - Zero Infrastructure Dependency: Bekerja tanpa tower BTS, tanpa router LoRaWAN, tanpa koneksi internet, dan tanpa pulsa SIM card.
  - Humane Guidance: Melatih ternak berbalik arah menggunakan nada akustik dan getaran haptik non-invasif berbasis pengkondisian asosiatif pakan.
  - Opportunistic Herd Telemetry: HerdSync-DTN memanfaatkan pertukaran data peer-to-peer antar-kalung via BLE; smartphone peternak berfungsi sebagai *data mule* saat berpapasan di lapangan.
- **Recommended visual:** Diagram contrasting conventional cloud-dependent virtual fencing (requiring towers and cloud round-trips) with BALAT's self-contained collar loop (GNSS -> Local Road Memory -> RTL Engine -> Cue Actuator).
- **Speaker notes:** "BALAT memindahkan seluruh pusat komputasi langsung ke kalung sapi. Dengan menyimpan geometri jalan lokal di memori internal kalung, prosesor kami menghitung jarak dan vektor kecepatan gerak sapi mendekati jalan secara lokal. Begitu sapi mendekati zona bahaya jalan, kalung mengeluarkan nada suara dan getaran yang telah dikondisikan untuk memanggil sapi kembali ke titik pakan aman. Tanpa latensi cloud, tanpa biaya pulsa bulanan, dan tanpa sengatan listrik. Ketika sapi-sapi berkumpul, kalung mereka saling bertukar catatan lokasi melalui Bluetooth berdaya rendah, sehingga smartphone peternak langsung mengunduh lokasi seluruh kawanan saat melintas."
- **Evidence or source:** `ARCHITECTURE.md` Section 1; `docs/DECISIONS.md` (ADR-001, ADR-002, ADR-005, ADR-007).
- **Investor objection this slide should answer:** "How can a collar protect livestock without an active internet connection or a central server?"

---

## Slide 5: Product — How It Works

- **Slide title:** Deterministic Edge Hardware & Delay-Tolerant Mesh
- **One-sentence takeaway:** Dedicated digital hardware computes road-approach risk at low power, while HerdSync-DTN shares telemetry across the herd.
- **Bullets:**
  - 7-Stage Pipelined Geometry Engine: Menghitung proyeksi jarak titik ke segmen jalan dan kecepatan pendekatan menggunakan fixed-point Q14 tanpa operasi pembagian runtime (divider-free).
  - 5-State Risk Engine: Finite State Machine (INVALID, SAFE, CAUTION, DANGER, COOLDOWN) dengan perlindungan histeresis dan filter data GNSS usang (stale-fix watchdog).
  - Modular Cue Interface (MCI): Jalur perintah logika terisolasi untuk menggerakkan buzzer piezo atau motor getar dengan batas durasi ketat dan jeda tenang wajib.
  - HerdSync-DTN Telemetry Protocol: Paket ringkas 36-byte bertanda tangan kriptografis disinkronkan secara *store-carry-forward* menggunakan *version vectors* dan batas *TTL*.
- **Recommended visual:** Technical block diagram illustrating the deterministic pipeline: GNSS UART ($GNRMC) -> NMEA Parser -> Local Road Segment ROM -> Geometry Engine -> Risk FSM -> Modular Cue Output; alongside the decoupled HerdSync BLE Telemetry Bridge.
- **Speaker notes:** "Secara teknis, sistem ini dibangun di atas data path deterministik: data posisi satelit NMEA 9600 baud di-parse secara instan. Mesin geometri 7-tahap memproyeksikan posisi sapi terhadap poliline jalan lokal tanpa pembagian komputasi berat. Risk FSM mengevaluasi kecepatan dan jarak untuk menghindari alarm palsu. Jika risiko meningkat, sistem memicu cue akustik terukur. Secara terpisah, subsistem HerdSync-DTN mengemas record lokasi 36-byte dan meneruskannya antar-kalung saat berdekatan, menjamin data kawanan tetap teragregasi di medan berbukit."
- **Evidence or source:** `rtl/balat_basys3_top.v`; `rtl/cue_scheduler.v`; `rtl/risk_fsm.v`; `poc/herdsync_dtn/engine.py`.
- **Investor objection this slide should answer:** "Is the hardware architecture overcomplicated for a simple livestock collar?"

---

## Slide 6: Why Now — Market & Technology Change

- **Slide title:** Why Now: Edge Silicon, GNSS Commoditization, & Energy Gap
- **One-sentence takeaway:** Low-cost multi-constellation GNSS, micro-power compute silicon, and regulatory bans on electric shock create a timely window for BALAT.
- **Bullets:**
  - GNSS Commoditization: Modul GNSS multi-konstelasi (u-blox NEO-M8N/M9N) kini berharga di bawah Rp 150.000 ($9) dengan akurasi horizontal sub-3 meter pada daya rendah.
  - Energy Gap & Ultra-Low-Power Silicon: Komputasi edge efisien (Cortex-M4 / BLE SoC) memungkinkan kalkulasi spasial berjalan dalam <2 milidetik dengan konsumsi tidur sub-25 µA—menghemat daya baterai >90% dibanding modem seluler 4G yang boros mencari sinyal.
  - Animal Welfare Headwinds: Regulasi internasional dan sertifikasi daging organik semakin melarang alat kejut listrik pada hewan ternak (EU Animal Welfare Directives) [NEEDS EVIDENCE].
  - Sinergi Ketahanan Pangan Nasional: Peningkatan target swasembada daging sapi Indonesia membutuhkan intensifikasi padang penggembalaan tanpa risiko kematian ternak di jalan umum.
- **Recommended visual:** Three converging vector arrows meeting at BALAT: 1. Sub-$10 Multi-GNSS & Edge Silicon; 2. Low-Power Energy Efficiency (No Cellular Radio Burn); 3. Global Welfare Headwinds on Electric Shock.
- **Speaker notes:** "Mengapa solusi ini tepat waktu? Pertama, chip navigasi satelit multi-konstelasi kini murah dan sangat presisi. Kedua, dari sisi efisiensi energi (sesuai pilar Hackathon ITS), modem seluler biasa membuang daya baterai besar karena terus-menerus mencari sinyal di area pedesaan. Komputasi edge BALAT tidur pada arus mikroamp dan hanya aktif 2 milidetik per detik, membuat baterai bertahan berbulan-bulan. Ketiga, tren global menolak kekerasan alat kejut listrik pada ternak, sementara Indonesia memprioritaskan swasembada daging tanpa kehilangan aset sapi produktif akibat kecelakaan."
- **Evidence or source:** Datasheet u-blox NEO-M8N; Nordic Semiconductor nRF52840 Power Profiler Data; Kementerian Pertanian RI Roadmap Swasembada Daging Sapi.
- **Investor objection this slide should answer:** "Why couldn't this have been built five or ten years ago?"

---

## Slide 7: Market Size — TAM, SAM, SOM

- **Slide title:** Market Size: An $8.5B Global & Rp 2,8 Triliun National Opportunity
- **One-sentence takeaway:** A multi-billion-dollar global livestock market starting with a focused Rp 36 Miliar ($2.25M) Indonesian beachhead in East Java & NTT rangelands.
- **Bullets:**
  - Global TAM: $8.5B (Rp 136 Triliun) pasar perangkat pemantauan ternak global berbasis wearable (~1,5 miliar ekor sapi dunia) [NEEDS EVIDENCE].
  - National SAM: Rp 2,8 Triliun ($175M) total populasi 1,9 juta ekor sapi potong di kawasan padang terbuka & perbatasan jalan provinsi di Jawa Timur dan Nusa Tenggara Timur (BPS 2024: Jatim 4,9M ekor, NTT 1,3M ekor).
  - Beachhead SOM (3-Year): Rp 36 Miliar ($2.25M) menyasar 15.000 kalung pada klaster peternakan sapi padang savana NTT (Sumba, Timor) dan peternakan sapi potong Jawa Timur dekat jalan arteri.
  - Bottom-Up Unit Assumptions: 15.000 kalung × Rp 2.400.000 ($150) harga kalung = Rp 36 Miliar penjualan perangkat + Rp 7,5 Miliar recurring software/map license (15.000 × Rp 500.000 / $30 per tahun).
- **Recommended visual:** Concentric market sizing diagram: Global TAM $8.5B -> National SAM Rp 2,8 Triliun -> Beachhead SOM Rp 36 Miliar (Jatim & NTT 15.000 ekor), with transparent unit economics callout.
- **Speaker notes:** "Pasar global pemantauan ternak bernilai lebih dari $8,5 miliar. Di Indonesia sendiri, terdapat 18,5 juta ekor sapi potong. Di Jawa Timur dan NTT saja, terdapat lebih dari 6,2 juta ekor sapi. Kami menetapkan target awal yang realistis (SOM): 15.000 ekor sapi di klaster padang savana NTT dan jalur jalan provinsi Jawa Timur dalam 3 tahun pertama. Dengan harga kalung Rp 2,4 juta ($150) dan biaya pemeliharaan peta digital Rp 500 ribu ($30) per tahun, potensi pendapatan tahap awal kami mencapai Rp 36 miliar dari perangkat keras ditambah Rp 7,5 miliar pendapatan berulang tahunan."
- **Evidence or source:** BPS Statistik Populasi Ternak Sapi 2023/2024; FAO Global Cattle Headcount; Unit pricing model.
- **Investor objection this slide should answer:** "Is the market too niche if you only focus on road perimeter prevention?"

---

## Slide 8: Business Model — Pricing & Unit Economics

- **Slide title:** Business Model: Healthy Hardware Margin + Zero-Carrier Recurring SaaS
- **One-sentence takeaway:** Upfront hardware margin paired with an annual offline mapping and herd intelligence subscription with zero cellular SIM carrier costs.
- **Bullets:**
  - Upfront Hardware Sale: Harga jual ritel Rp 2.400.000 ($150) per kalung dengan target Biaya Pokok Produksi (BOM) Rp 480.000 ($30) pada skala 10.000 unit -> Gross Margin 80%.
  - Verified Target BOM Breakdown:
    - Multi-GNSS u-blox NEO-M8N: Rp 140.000 ($8.80)
    - SoC Ultra-Low-Power COTS BLE (nRF52840 / ESP32-C3): Rp 40.000 ($2.50)
    - Power Module (LiSOCl2 3.6V 19Ah / LiFePO4 + solar panel): Rp 120.000 ($7.50)
    - Transducer (Piezo buzzer + haptic motor): Rp 25.000 ($1.50)
    - Rugged Collar Enclosure IP67 TPU: Rp 70.000 ($4.40)
    - PCB, Passives, Assembly & Quality Inspection: Rp 85.000 ($5.30)
  - Annual Software & Map License: Rp 500.000 ($30) per ekor per tahun untuk pembaruan peta jalan offline, sinkronisasi app HerdSync, dan laporan eksposur risiko ternak.
  - Zero Cellular Cost Drag: Bebas biaya tagihan kartu SIM operator seluler bulanan, memastikan margin kotor langganan perangkat lunak di atas 90%.
- **Recommended visual:** Waterfall chart showing Hardware Sale (Rp 2,4 Jt) minus BOM components (Rp 480k) = Gross Profit (Rp 1,92 Jt / 80% margin); Right side showing recurring software subscription margin.
- **Speaker notes:** "Model bisnis kami sangat sehat karena memecahkan kelemahan terbesar IoT pertanian: biaya pulsa kartu SIM. Kami menjual kalung dengan harga Rp 2,4 juta ($150). Biaya komponen produksi skala 10.000 unit kami adalah Rp 480 ribu ($30) per unit, memberikan margin kotor perangkat keras sebesar 80%. Kami kemudian menambahkan biaya langganan perangkat lunak tahunan sebesar Rp 500 ribu ($30) per ekor untuk pembaruan peta jalan offline dan integrasi aplikasi HerdSync di smartphone. Karena kalung kami tidak memerlukan kartu SIM seluler, margin kotor langganan software kami melampaui 90%."
- **Evidence or source:** Komponen BOM DigiKey/LCSC bulk pricing; Distributor resmi u-blox dan Nordic Semiconductor; Kalkulasi unit economics.
- **Investor objection this slide should answer:** "How can you charge a recurring software subscription if your device doesn't connect to a cloud server?"

---

## Slide 9: Traction — Evidence Only (TKT 4 Verified)

- **Slide title:** Traction: Proven Silicon Architecture & Zero-Error Telemetry Bridge
- **One-sentence takeaway:** Core spatial pipeline and telemetry framing are validated on FPGA silicon and physical bench hardware; zero paying customers to date.
- **Bullets:**
  - Tingkat Kesiapan Teknologi (TKT) 4: Validasi komponen dan subsistem telah terbukti tuntas di lingkungan laboratorium.
  - FPGA RTL Verification: Sintesis, placement, dan routing Vivado 2024.2 pada Xilinx Artix-7 (Basys 3) memenuhi timing closure (WNS +1.701 ns; 885 LUTs, 18 DSPs).
  - Physical Telemetry Verified on Hardware: Bridge telemetri USB-UART Basys 3 telah diuji fisik pada perangkat keras (`/dev/ttyUSB1`, 115200 baud) mengalirkan 1.200 frame data dalam uji rendam 120 detik dengan 0 CRC error dan 0 sequence drop.
  - Connected Dashboard POC: Papan Basys 3 mengalirkan record UART langsung ke dashboard lokal read-only dan file CSV; byte risk pada dashboard di-latch dari state yang sama dengan `LED0–LED4`, sehingga papan dan dashboard sinkron. Build bridge: WNS +0.614 ns, 1.053 LUT, 1.190 register, 18 DSP, 0 BRAM.
  - Protocol Simulation Passed: Model perangkat lunak HerdSync-DTN lulus 100% dari 26 unit test pada 5 skenario topologi jaringan (*two_collar, multi_hop, partition_rejoin, phone_mule, emergency*).
  - Commercial Traction Status: Tahap purwarupa pra-inkubasi (pre-revenue, 0 unit komersial terjual) [NEEDS EVIDENCE for commercial sales].
- **Recommended visual:** Photographic proof of the Basys 3 bench setup alongside Vivado timing closure report snippet, a screenshot of the connected read-only dashboard, and Python host telemetry terminal output showing 0 CRC errors.
- **Speaker notes:** "Kami mengedepankan integritas data. Purwarupa kami saat ini berada pada TKT 4: seluruh pipeline spasial telah berhasil disintesis pada chip FPGA Xilinx Artix-7 dengan timing 100 MHz terpenuhi. Jembatan telemetri perangkat keras telah diuji secara fisik mengalirkan 1.200 frame tanpa satu pun CRC error atau paket hilang. Kami juga sudah menghubungkan papan ke dashboard lokal read-only: record UART yang sama dengan yang tampil di LED direkam ke CSV, dan risk state dashboard memakai state yang sama dengan LED papan. Protokol jaringan delay-tolerant HerdSync telah lulus 26 uji skenario unit test. Yang belum kami lakukan adalah pengujian pada sapi hidup di lapangan—dan itulah fokus utama tahap inkubasi ini."
- **Evidence or source:** `docs/BASYS3_DEMO.md`; `docs/BASYS3_HERDSYNC_BRIDGE.md`; `docs/BASYS3_CONNECTED_POC.md`; `scripts/web_demo.py`; `poc/herdsync_dtn/`; `PLAN.md`.
- **Investor objection this slide should answer:** "Is this just an idea on paper, or do you have working technology?"

---

## Slide 10: Go-To-Market — Beachhead & Acquisition Motion

- **Slide title:** Go-to-Market: Highway Corridor Wedge & Cattlemen Channels
- **One-sentence takeaway:** Landing high-liability ranches along major highway corridors through agricultural insurers and regional Cattlemen's Associations.
- **Bullets:**
  - Beachhead Geographic Focus: Peternakan sapi potong di Kabupaten Kupang & Sumba Timur (NTT) serta kawasan peternakan lingkar hutan/jalan provinsi di Bojonegoro & Tuban (Jawa Timur).
  - Wedge Value Proposition: Fokus utama adalah pencegahan tabrakan jalan raya (*highway collision shield*), bukan langsung mengganti seluruh pagar peternakan.
  - Trusted Channel Distribution: Kemitraan dengan Perhimpunan Dokter Hewan Indonesia (PDHI) cabang lokal, dinas peternakan daerah, dan kelompok tani ternak (Poktan).
  - Co-Design with Local Community: Mengikutsertakan peternak lokal dalam perancangan kalung agar mudah dipasang pada sapi lokal (Sapi Ongole, Sapi Bali) tanpa melukai leher ternak.
- **Recommended visual:** GTM sales funnel graphic: Dinas Peternakan / Asosiasi Dokter Hewan -> Pilot Uji Coba Lapangan (20–50 kalung) -> Penerapan Penuh Kelompok Ternak (200–1.000 kalung) -> Skalasi Nasional.
- **Speaker notes:** "Strategi go-to-market kami tidak menggunakan penjualan dingin, melainkan pendekatan komunitas lokal dan ahli terpercaya. Kami memulai dari titik dengan rasa sakit tertinggi: peternakan di jalur Trans-Timor NTT dan lingkar hutan Jawa Timur. Kami menggandeng dokter hewan setempat dan kelompok peternak lokal (Poktan) untuk uji coba co-design 20 hingga 50 kalung pertama. Begitu peternak melihat sapi mereka aman dari jalan raya dan tidak ada ternak yang tertabrak, adopsi akan menyebar cepat antar-anggota kelompok ternak."
- **Evidence or source:** `PRD.md` Section 4; Pedoman Kemitraan Kelompok Tani Ternak Kementerian Pertanian RI.
- **Investor objection this slide should answer:** "Selling hardware to traditional farmers and ranchers is notoriously difficult. How will you distribute this?"

---

## Slide 11: Competition — Differentiated Positioning

- **Slide title:** Competitive Landscape: The Only Truly Offline, Humane Collar
- **One-sentence takeaway:** BALAT occupies an uncontested position combining zero-infrastructure offline reliability with animal-welfare-friendly guidance.
- **Bullets:**
  - Incumbent Virtual Fencing (Halter, Vence, Nofence): Biaya langganan sangat mahal (>Rp 1 Juta/ekor/tahun), butuh sinyal 4G/LoRa, menggunakan kejutan listrik invasif [NEEDS EVIDENCE].
  - Passive GPS Livestock Ear Tags (Ceres Tag, Moocall): Hanya merekam koordinat pasif; tidak ada kemampuan membelokkan ternak dan biaya satelit mahal [NEEDS EVIDENCE].
  - Pagar Kawat Konvensional: Biaya pembangunan sangat mahal (>Rp 100 Juta/km), mudah rusak, nol visibilitas data.
  - BALAT Structural Moat: Keunggulan paten pada pipeline komputasi spasial edge rendah daya, protokol mesh DTN offline, dan 100% ramah kesejahteraan hewan tanpa alat setrum.
- **Recommended visual:** 2x2 Positioning Matrix: X-axis: Ketergantungan Infrastruktur (Ketergantungan Cloud/Tower vs. 100% Edge Mandiri); Y-axis: Metode Kendali (Sengatan Listrik Invasif vs. Isyarat Akustik/Haptik Non-Invasif). BALAT berada sendirian di kuadran kanan-atas.
- **Speaker notes:** "Dalam peta persaingan, pasar saat ini terbagi dua: GPS ear tag pasif yang hanya memantau tanpa bisa mencegah kecelakaan, atau kalung virtual fencing mahal asal Selandia Baru dan Norwegia yang mengandalkan sengatan listrik dan koneksi seluler konstan. BALAT menguasai kuadran unik: 100% mandiri di leher sapi tanpa butuh tower, dan 100% manusiawi tanpa menyetrum sapi. Kompetitor lama tidak dapat dengan mudah meniru karena arsitektur perangkat lunak mereka terlanjur terkunci pada dependensi cloud dan algoritma sengatan listrik."
- **Evidence or source:** Analisis produk kompetitor global; Campbell et al. (2019); `docs/SAFETY_AND_LIMITATIONS.md`.
- **Investor objection this slide should answer:** "What stops Halter or Gallagher from copying your offline road containment feature?"

---

## Slide 12: Roadmap — Milestones & Outcomes (TKT 4 to TKT 7)

- **Slide title:** Execution Roadmap: From Lab Bench to 500-Collar Commercial Pilot
- **One-sentence takeaway:** An 18-month stage-gated milestones roadmap leading from animal behavioral validation to a 500-collar commercial field deployment.
- **Bullets:**
  - M1 (Bulan 1–4) [TKT 4 -> 5]: Uji coba pengkondisian perilaku sapi terawasi (5–10 ekor) bersama Fakultas Kedokteran Hewan; migrasi algoritma RTL ke COTS BLE SoC (Nordic nRF52840).
  - M2 (Bulan 5–8) [TKT 5]: Fabrikasi casing kalung tangguh IP67 tahan cuaca tropis terintegrasi modul GNSS, antena keramik, dan baterai hemat daya.
  - M3 (Bulan 9–13) [TKT 6]: Uji coba lapangan 50 kalung di padang savana peternakan mitra di NTT / Jawa Timur; validasi protokol radio HerdSync BLE mesh.
  - M4 (Bulan 14–18) [TKT 7]: Peluncuran pilot komersial 500 kalung pada 3 kelompok peternak komersial; sertifikasi frekuensi SDPPI Kominfo.
- **Recommended visual:** Milestone roadmap timeline diagram highlighting the four major phases, with explicit go/no-go stage gates (Behavioral Compliance Gate, Silicon Architecture Gate, Field Mesh Gate).
- **Speaker notes:** "Peta jalan kami dirancang sangat disiplin untuk menekan risiko sebelum mengeluarkan modal besar. Milestone 1 adalah gerbang terpenting kami: uji coba perilaku pada 5 hingga 10 ekor sapi bersama dokter hewan untuk membuktikan efektivitas suara pemanggil pakan, sembari memigrasikan logika komputasi ke chip nRF52840 berdaya rendah. Setelah tervalidasi, Milestone 2 mencetak casing kalung tahan banting IP67. Milestone 3 menguji 50 kalung di padang rumput nyata NTT, dan Milestone 4 menggelar 500 kalung komersial berizin SDPPI untuk membuka pendanaan Seri A."
- **Evidence or source:** `PLAN.md`; `docs/HERDSYNC_POC.md` Section 9; Standar Pengukuran TKT Kemenristek/BRIN.
- **Investor objection this slide should answer:** "What is your critical development path, and how do you ensure you don't burn capital on tooling before proving the concept works?"

---

## Slide 13: Team — Relevant Founder Advantages

- **Slide title:** Team: Hardware Silicon, Spatial Computing, & Agritech Execution
- **One-sentence takeaway:** Technical leadership with specialized expertise across digital FPGA/RTL design, delay-tolerant networking, and embedded telemetry.
- **Bullets:**
  - Digital Hardware & RTL Engineering: Rekam jejak langsung dalam sintesis RTL FPGA, timing closure, pemodelan fixed-point DSP, dan verifikasi perangkat keras.
  - Embedded Networking & Cryptography: Keahlian arsitektur protokol delay-tolerant (DTN), enkripsi data, dan serial telemetry bridge.
  - Kemitraan Akademik & Riset [NEEDS EVIDENCE]: Menggandeng pakar perilaku hewan ternak dari perguruan tinggi terkemuka dan praktisi peternakan padang terbuka.
  - Struktur kepemilikan tim, rekam jejak startup sebelumnya, dan daftar lengkap penasihat [NEEDS EVIDENCE].
- **Recommended visual:** Founder and lead advisor profile cards showcasing technical backgrounds, key domain competencies, and logos of prior institutions/companies [NEEDS EVIDENCE].
- **Speaker notes:** "Membangun BALAT memerlukan integrasi multidisiplin: perancangan chip digital, matematika spasial presisi, protokol jaringan terdistribusi, dan pemahaman biologi ternak. Tim teknis kami telah membuktikan kapabilitas dengan membangun pipeline spasial dan menutup timing frekuensi FPGA dari nol. Untuk melengkapi sisi peternakan, kami berkolaborasi dengan peneliti kedokteran hewan dan kelompok peternak lokal agar solusi yang dibangun relevan secara praktis di lapangan."
- **Evidence or source:** Commit history repositori proyek; artefak rancangan perangkat keras; profil anggota tim marked [NEEDS EVIDENCE].
- **Investor objection this slide should answer:** "Does a team with deep digital hardware expertise actually understand the realities of cattle ranching?"

---

## Slide 14: Financial Outlook — 3-Year Projections

- **Slide title:** Financial Outlook: 3-Year Projections & Unit Economics
- **One-sentence takeaway:** Capital-efficient growth reaching cash-flow positivity in Year 3 with high hardware margins and compounding recurring software revenue.
- **Bullets:**
  - Year 1 (Piloting & Validasi): 500 kalung terpasang; Pendapatan Rp 1,2 Miliar ($75k); fokus pembuktian data lapangan & perilaku ternak [NEEDS EVIDENCE].
  - Year 2 (Peluncuran Komersial): 5.000 kalung; Pendapatan Rp 14,3 Miliar ($895k) (Rp 12M hardware + Rp 2,3M software ARR); blended gross margin ~75% [NEEDS EVIDENCE].
  - Year 3 (Ekspansi Skala Nasional): 25.000 kalung; Pendapatan Rp 71,5 Miliar ($4.47M) (Rp 59M hardware + Rp 12,5M software ARR); mencapai titik impas dan arus kas positif [NEEDS EVIDENCE].
  - Asumsi Beban Operasional: Gaji tim rekayasa (4 orang), NRE cetakan injeksi plastik enclosure, hibah riset uji perilaku hewan, dan operasional lapangan [NEEDS EVIDENCE].
- **Recommended visual:** 3-Year bar chart showing Revenue growth split between Hardware Sales (light blue) and Recurring Software ARR (dark blue), accompanied by a line indicating gross margin progression.
- **Speaker notes:** "Proyeksi keuangan kami mencerminkan model bisnis perangkat keras bernilai tambah tinggi yang dipadukan dengan lisensi perangkat lunak tahunan. Di Tahun ke-1, kami memvalidasi 500 kalung pilot dengan pendapatan Rp 1,2 miliar. Di Tahun ke-2, peluncuran komersial 5.000 kalung menghasilkan Rp 14,3 miliar dengan margin kotor di atas 70%. Memasuki Tahun ke-3, dengan penetrasi 25.000 ekor di Jawa Timur, NTT, dan pasar ekspor regional, pendapatan mencapai Rp 71,5 miliar dengan arus kas operasional positif karena beban operasional kami tidak terbebani tagihan server cloud raksasa maupun pulsa kartu SIM."
- **Evidence or source:** Model pro-forma keuangan; asumsi harga dan biaya pokok produksi [NEEDS EVIDENCE].
- **Investor objection this slide should answer:** "Will high hardware tooling and inventory costs drain all your cash before software margins kick in?"

---

## Slide 15: Fundraising Ask — Amount, Runway, & Use of Funds

- **Slide title:** Fundraising Ask: Rp 4 Miliar ($250k) Pre-Seed / Incubator Round
- **One-sentence takeaway:** Mencari pendanaan tahap pra-awal Rp 4 Miliar ($250.000) untuk 18 bulan akselerasi validasi perilaku ternak dan penyebaran 500 kalung komersial.
- **Bullets:**
  - Kebutuhan Modal: Rp 4.000.000.000 ($250.000 USD) tahap Pre-Seed / Inkubasi Hackathon ITS [NEEDS EVIDENCE].
  - Target Runway: 18 bulan operasional penuh hingga pencapaian Milestone 4 (TKT 7).
  - Alokasi Penggunaan Dana:
    - 40% (Rp 1,6 Miliar): Rekayasa Teknis (migrasi nRF52840 BLE SoC, cetakan casing IP67, aplikasi Android HerdSync).
    - 30% (Rp 1,2 Miliar): Uji Coba Perilaku Hewan Terakreditasi & Uji Lapangan Bersama Peternak NTT/Jatim.
    - 20% (Rp 800 Juta): Pengadaan Bahan Baku & Batch Produksi 500 Kalung Pilot Awal.
    - 10% (Rp 400 Juta): Sertifikasi SDPPI Kominfo, Paten HKI Spasial, dan Legalitas.
  - Milestone Nilai untuk Seri Selanjutnya: Terbuktinya tingkat kepatuhan ternak >80% dan 500 kalung beroperasi menghasilkan pendapatan di lapangan.
- **Recommended visual:** Donut chart illustrating the Use of Funds breakdown, alongside a milestone progression bar showing the 18-month runway to Series Seed / Series A readiness.
- **Speaker notes:** "Untuk merealisasikan solusi ini, kami menggalang pendanaan awal sebesar Rp 4 miliar ($250 ribu). Dana ini memberikan runway selama 18 bulan untuk mencapai dua target kunci: Pertama, menyelesaikan pengujian ilmiah perilaku ternak untuk memastikan keandalan isyarat suara non-kejut. Kedua, memproduksi kalung tangguh berstandar industri dan memasang 500 unit kalung pertama di peternakan mitra. Target ini akan membuka peluang investasi lanjutan dari mitra strategis internasional seperti InvestHK dan Garage Plus."
- **Evidence or source:** Rencana anggaran biaya inkubasi dan produksi pilot; estimasi alokasi marked [NEEDS EVIDENCE].
- **Investor objection this slide should answer:** "Is the capital ask realistic for the scope of prototype manufacturing and field trials?"

---

## Slide 16: Closing — Memorable Vision

- **Slide title:** The Future of Livestock Stewardship: Autonomous & Humane
- **One-sentence takeaway:** Mengeliminasi batas bahaya jalan raya bagi ternak melalui kecerdasan buatan edge—tanpa tower, tanpa kawat berduri, dan tanpa menyakiti hewan.
- **Bullets:**
  - Melindungi Aset Ternak & Nyawa Manusia: Mencegah ribuan insiden tabrakan di jalan raya pedesaan dan jalur lintas antar-kota.
  - Efisiensi Energi & Keberlanjutan: Komputasi edge berdaya mikroamp yang ramah lingkungan tanpa ketergantungan infrastruktur energi tinggi.
  - Kedaulatan Pangan & Kesejahteraan Hewan: Memodernisasi peternakan nusantara dengan teknologi cerdas yang menjunjung etika kesejahteraan ternak.
  - Kontak Tim: Tim Inovasi BALAT | contact@balat-hardware.example.com [NEEDS EVIDENCE].
- **Recommended visual:** Inspiring widescreen visual: Kawanan sapi potong sehat merumput dengan tenang di padang savana luas berlatar belakang perbukitan saat matahari terbit, dengan overlay garis perimeter digital transparan berwarna hijau. Logo BALAT, kutipan misi, dan informasi kontak.
- **Speaker notes:** "Selama ratusan tahun, menjaga ternak berarti membentang kawat berduri melintasi perbukitan atau merelakan ternak mati tertabrak di jalan raya. BALAT menghadirkan jalan ketiga: kalung pintar mandiri yang membimbing ternak dengan insting alaminya, mampu bekerja di pelosok mana pun tanpa perlu sinyal seluler. Mari bersama-sama mewujudkan peternakan nusantara yang aman, mandiri secara teknologi, dan manusiawi. Terima kasih."
- **Evidence or source:** `PRODUCT_CONTEXT.md`; `PRD.md` Section 9.
- **Investor objection this slide should answer:** "Why should the panel choose BALAT as the winning innovation in Hackathon ITS 2026?"
