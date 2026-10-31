# PRODUCT_CONTEXT — BALAT: Road-Aware Livestock Guidance

## 1. Product Summary

**Product Name:** BALAT (Road-Aware Livestock Guidance)  
**Category:** Autonomous edge-computing livestock wearable / agricultural IoT  
**Target Hardware:** FPGA / low-power digital ASIC + GNSS receiver + COTS BLE module + modular cue transducer  
**Current Prototype:** Standalone RTL on Digilent Basys 3 (Xilinx Artix-7 XC7A35T)  

BALAT is an infrastructure-free, map-aware wearable collar for grazing livestock (specifically cattle). It integrates GNSS positioning with locally stored road geometry to evaluate real-time road approach risk and command non-aversive deterrent/recall cues (acoustic tones, vibration) before animals breach pasture boundaries or enter roadways. It operates with zero dependence on cellular towers, cloud APIs, internet connectivity, or fixed LoRaWAN base stations.

A companion delay-tolerant networking subsystem, **HerdSync-DTN**, enables peer-to-peer store-carry-forward telemetry exchange among collars over Bluetooth Low Energy (BLE), with the rancher's smartphone serving as a mobile data mule.

---

## 2. Problem Statement & Customer Need

### Target Customers
- Beef cattle ranchers with large acreage bordering or transected by public roads.
- Pastoralists and open-range livestock managers facing missing, downed, or costly perimeter fencing.
- Dairy and pasture managers operating rotational grazing near high-traffic rural corridors.

### Pain Points
1. **Collisions & Liability:** Livestock-vehicle collisions cause animal fatalities, vehicle destruction, human injury/death, and legal liability for ranchers.
2. **Infrastructure Failure in Remote Areas:** Traditional virtual fencing systems (e.g., Halter, Vence, Nofence, Gallagher eShepherd) rely heavily on cellular networks or dedicated base stations (LoRaWAN gateways). Rural pastures frequently suffer from zero cellular coverage and rugged terrain that obstructs line-of-sight RF gateways.
3. **Animal Welfare & Regulatory Pushback:** Commercial virtual fencing relies on electric shock stimuli. Aversive shock faces growing animal welfare scrutiny, legal restrictions in select jurisdictions, and consumer pushback.
4. **Capital & Operational Cost:** Existing commercial collars are expensive (often $40–$100+/collar/year subscription plus high upfront hardware costs), making herd-scale deployment cost-prohibitive for commercial cow-calf operations.

---

## 3. Product Architecture & Pipeline

### Core Autonomous Path (v0.1 Standalone RTL)
```text
GNSS Receiver (u-blox NEO-M8N)
      │ 9600 baud UART ($GNRMC)
      ▼
nmea_parser.v (Checksum, fix validity, fix age, lat/lon coordinate extraction)
      │
      ▼
coord_convert.v (Local metric conversion)
      │
      ▼
road_seg_rom.v (Preprocessed offline OSM road segments in local BRAM)
      │
      ▼
nearest_segment.v / road_geom.v (Point-to-segment distance, squared-distance comparator)
      │
      ▼
velocity_estimator.v (Successive fix delta, directional approach vector toward road)
      │
      ▼
risk_fsm.v (5-State FSM: INVALID, SAFE, CAUTION, DANGER, COOLDOWN with hysteresis)
      │
      ▼
cue_scheduler.v (Modular Cue Interface [MCI]: CUE_EN, PWM, max duration, quiet cooldown)
      │
      ▼
Modular Cue Actuator (Non-aversive buzzer / acoustic speaker / vibration motor)
```

### Telemetry & Sync Layer (HerdSync-DTN)
- Independent communications track; strictly separated from the real-time safety/cue path.
- Store-carry-forward delay-tolerant mesh over BLE.
- 36-byte signed location records (origin ID, epoch, sequence, timestamp, coordinates, quality, battery, risk state, truncated HMAC-SHA256).
- Version-vector anti-entropy exchange between collars during opportunistic contact.
- Rancher smartphone acts as mobile collection mule (pulls latest herd positions, pushes optional herd configuration).

---

## 4. Current Verification Status (Evidence vs. Unverified)

### Verified Hard Evidence
- **Technology Readiness Level (TKT):** TKT 4 (Lab Component & Hardware Bridge Validation).
- **Synthesizable RTL Bench Demo (Basys 3):** Vivado 2024.2 synthesis, placement, and routing passed. Timing met with positive slack (WNS +1.701 ns). Resource utilization: 885 LUTs, 628 FFs, 18 DSPs.
- **Hardware Telemetry Bridge (Basys 3):** USB-UART bridge (`balat_herdsync_basys3_top.v`) at 115200 baud streaming 43-byte framed records to host Python collector. Met timing (WNS +2.451 ns, 1248 LUTs, 1328 FFs, 18 DSPs). Verified on physical hardware (`/dev/ttyUSB1`): 320 records streamed with 0 CRC errors, 1200-frame 120-second soak test with zero sequence drops or resets.
- **HerdSync-DTN Protocol Simulation:** 26/26 unit tests passed. 5 deterministic network scenarios passed (`two_collar`, `multi_hop`, `partition_rejoin`, `phone_mule`, `emergency`).
- **NMEA Parser Verification:** Testbench coverage with valid and corrupted NMEA sentence vectors (bad checksums, malformed fields, stale data rejection).
- **Map Preprocessing Toolchain:** Python script `osm_to_segments.py` converts OSM road polylines into bounded local-coordinate segment arrays with manifest and checksums.
- **Component BOM Teardown (10k volume estimate):**
  - Multi-GNSS u-blox NEO-M8N: Rp 140.000 ($8.80)
  - COTS BLE SoC (Nordic nRF52840 / ESP32-C3): Rp 40.000 ($2.50)
  - Battery (LiSOCl2 3.6V 19Ah / LiFePO4 + solar panel): Rp 120.000 ($7.50)
  - Transducer (Piezo buzzer + haptic motor): Rp 25.000 ($1.50)
  - Rugged IP67 TPU Enclosure: Rp 70.000 ($4.40)
  - PCB, Passives, SMT Assembly & Testing: Rp 85.000 ($5.30)
  - **Total Target BOM:** Rp 480.000 ($30.00).

### Unverified Assumptions & Gaps [NEEDS EVIDENCE]
- **Animal Behavioral Efficacy:** No behavioral testing on livestock conducted to date. Assumption that cattle can be conditioned reliably to acoustic/vibration recall cues without electric shock is unproven. Academic studies (Campbell et al. 2019, Lee et al. 2009) show habituation risk if sound is unreinforced.
- **Collar GNSS Performance:** GNSS receiver performance on a moving, grazing animal (neck orientation, ground reflection, tree canopy attenuation) is untested.
- **Hardware Form Factor & Power:** Basys 3 FPGA is a development bench prototype, consuming excessive power for a collar. Power consumption, battery sizing, solar harvesting, enclosure IP-rating, and mechanical collar mounting are undefined.
- **Field Wireless Performance:** Physical BLE range, body shadowing from cattle tissue, and packet loss in rural terrain are unmeasured.
- **Market Sizing & Pricing Elasticity:** TAM, SAM, SOM, rancher willingness-to-pay, and business model economics require field discovery interviews [NEEDS EVIDENCE]. Target benchmarks: Rp 2.400.000 ($150) retail price, Rp 500.000 ($30) annual map update license. Sapi potong asset value in Indonesia: Rp 15M–Rp 25M (BPS/Kementan 2024).

---

## 5. Strategic Differentiators vs. Incumbents

| Dimension | Existing Virtual Fencing (Halter, Vence, Nofence) | BALAT Approach |
|---|---|---|
| **Connectivity Dependency** | Continuous cellular or fixed LoRaWAN base stations | Zero infrastructure; fully autonomous edge computation |
| **Aversive Stimulus** | Electric shock pulse | Conditioned non-aversive cues (acoustic/vibration) |
| **Telemetry Network** | Cloud backend via cellular / gateway | Opportunistic peer-to-peer DTN mesh + mobile phone mule |
| **System Complexity** | High recurring subscription ($40–$100+/cow/year) | Low-cost offline hardware; local compute; lower recurring overhead |
| **Failure Mode** | Network outage or dead zone disables dynamic fencing | Safety logic runs locally in collar hardware regardless of radio link |

---

## 6. Open Product & Business Questions

1. **Animal Response:** Will free-ranging cattle reliably alter course away from a road upon receiving a non-aversive acoustic/haptic cue without an electric shock backing?
2. **Silicon Architecture:** What is the production compute platform: ultra-low-power MCU (e.g. Nordic nRF52/nRF53), FPGA, or dedicated custom ASIC?
3. **Map Maintenance:** How are farm-specific road updates, unpaved ranch tracks, and boundary modifications provisioned onto offline collars without manual physical cabling?
4. **Commercial Model:** Is BALAT a pure hardware sale, a hardware-enabled SaaS, or a per-head seasonal lease?
