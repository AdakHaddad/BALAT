# Unresolved Product & Business Questions, Assumptions, and Action Plan

## 1. Most Important Unresolved Product / Business Question

**Question:**  
*Can grazing cattle be reliably conditioned to halt or reverse their trajectory away from road corridors using non-aversive cues (acoustic tone / haptic vibration) alone, without an electric shock backing?*

### Why this is the existential question:
- Every digital architecture achievement (FPGA pipeline, 7-stage pipelined road projection, 100 MHz timing closure, DTN mesh simulation) depends on the animal turning around when cued.
- Incumbent virtual fencing systems (Halter, Vence, Gallagher eShepherd, Nofence) utilize acoustic cues as a pre-warning paired with an electric pulse. The shock provides the negative reinforcement that prevents habituation.
- BALAT explicitly rejects electric shock on animal welfare grounds (PRD Section 3, ADR-005, `docs/SAFETY_AND_LIMITATIONS.md`).
- If cattle ignore acoustic/haptic cues, habituate within days, or flee unpredictably into oncoming traffic, the entire product value proposition collapses regardless of hardware performance.

---

## 2. Recommended PM Framework

**Framework:** **Riskiest Assumption Test (RAT)** via the **Assumption Prioritization Canvas (Impact × Risk Matrix)**.

### Why this framework:
- Traditional backlog prioritization (e.g. MoSCoW, RICE for features) assumes problem-solution fit is already established. It prioritizes *what to build*, not *what will kill the venture*.
- The Assumption Prioritization Canvas plots assumptions along two axes:
  1. **Impact / Criticality (1–10):** How severely the venture fails if this assumption is false.
  2. **Risk / Uncertainty (1–10):** (1 - Confidence) × Effort to discover.
- High-Impact, High-Risk assumptions are isolated as Riskiest Assumption Tests (RATs) to design minimal, falsifiable behavioral experiments before committing engineering capital.

---

## 3. Evidence and Assumptions Analysis

| ID | Assumption | Category | Impact (1–10) | Confidence (1–10) | Evidence Status |
|---|---|---|---|---|---|
| A-01 | Cattle turn away from road upon hearing non-aversive acoustic/vibration cue. | Animal Behavior | 10 | 2 | **Unverified.** [NEEDS EVIDENCE]. Academic literature shows habituation risk without negative reinforcer. |
| A-02 | Standalone digital pipeline can evaluate road distance and risk in real time. | Hardware / RTL | 8 | 10 | **Verified.** Basys 3 bench demo met timing (WNS +1.701 ns, 885 LUTs). Replays 201-point trace deterministically. |
| A-03 | Opportunistic BLE store-carry-forward syncs herd location without cellular towers. | Networking | 7 | 8 | **Partially Verified.** Phase 0 simulation passed 26 unit tests + 5 scenarios. Bench USB-UART bridge verified on hardware (1200 frames, 0 errors). Radio RF field tests [NEEDS EVIDENCE]. |
| A-04 | Offline OSM road maps are accurate and complete enough for livestock safety. | Spatial / Data | 8 | 4 | **Unverified in field.** [NEEDS EVIDENCE]. OSM often lacks rural unpaved roads and private tracks. Manual correction tool exists in repo (`osm_to_segments.py`), but field validation missing. |
| A-05 | Collar GNSS maintains acceptable accuracy on a moving, grazing cow. | Sensor / Physics | 8 | 4 | **Unverified in field.** [NEEDS EVIDENCE]. Collar rotation, ground reflection, and tree canopy cause multipath and fix dropouts. |
| A-06 | Ranchers will pay upfront hardware + maintenance fees for offline road guidance. | Business / Market | 9 | 3 | **Unverified.** [NEEDS EVIDENCE]. Willingness to pay, herd sizing, and unit economics require rancher discovery interviews. |
| A-07 | Custom ASIC is necessary and economically justified over a COTS BLE SoC/MCU. | Hardware Strategy | 6 | 3 | **Unverified.** [NEEDS EVIDENCE]. Ultra-low-power MCUs (e.g., Nordic nRF52840) run the identical geometry math in <1 ms, consuming microamps while sleeping. ASIC requires millions in NRE. |

---

## 4. Top Three Actions Ranked by Impact and Confidence

### Ranking Formula:
- **Impact (1–10):** Venture survival and strategic clarity.
- **Confidence (1–10):** Predictability of executing the test and obtaining unambiguous data.
- **Ease (1–10):** Resource, time, and capital feasibility.
- **ICE Score:** $\text{Impact} \times \text{Confidence} \times \text{Ease}$

```text
Action 1: Animal Cue Efficacy RAT (Impact: 10, Confidence: 8, Ease: 6 -> ICE = 480)
Action 2: COTS MCU/BLE Architecture Benchmark (Impact: 8, Confidence: 9, Ease: 8 -> ICE = 576)
Action 3: Collar GNSS Field Logging Test (Impact: 8, Confidence: 8, Ease: 7 -> ICE = 448)
```

### Action 1 (Rank 1 by Strategic Impact): Animal Behavioral Cue Conditioning Trial
- **Objective:** Test whether cattle can be trained to reverse course on an acoustic/haptic cue without electric shock.
- **Method:** 14-day controlled trial with 5–10 cattle in an enclosed pasture. Use positive reinforcement (feed reward at central trough) paired with distinctive audio tone when approaching a marked boundary line.
- **Success Metric:** $\ge 80\%$ directional reversal rate within 5 seconds of cue onset; zero habituation decline across 14 days.
- **Stop Rule:** If cattle ignore cue or panic, halt and re-evaluate stimulus modalities.

### Action 2 (Rank 2 by Feasibility & Architecture Impact): Port Algorithm to COTS BLE SoC
- **Objective:** Determine whether custom FPGA/ASIC is justified or if a $3 COTS MCU (Nordic nRF52840) fulfills power, memory, and compute requirements.
- **Method:** Implement fixed-point coordinate projection and 5-state risk FSM on nRF52840 Cortex-M4. Benchmark execution time, flash/RAM footprint, and sleep current (duty-cycled 1 Hz GNSS read).
- **Success Metric:** Active calculation time $< 2\text{ ms}$, average sleep current $< 25\,\mu\text{A}$, bill of materials (BOM) cost reduction $> 80\%$ vs FPGA.

### Action 3 (Rank 3 by Technical Risk): Real-Collar GNSS Multipath & Motion Test
- **Objective:** Measure real-world GNSS fix availability, horizontal error, and fix latency on grazing cattle.
- **Method:** Mount u-blox NEO-M8N with patch antenna on dummy harness or cattle halter; record raw NMEA sentences for 72 hours under open sky, brush, and tree canopy.
- **Success Metric:** Horizontal 95% error $\le 3.5\text{ m}$; fix outage rate $< 2\%$ during daylight grazing.

---

## 5. Next Executive Decision Required

**Decision:**  
*Formally approve Action 1 (supervised animal behavioral pilot) as the mandatory stage-gate before committing engineering funds or hardware spin-up for collar miniaturization.*

If behavioral conditioning succeeds, product-market validation proceeds immediately. If behavioral conditioning fails, pivot away from direct road containment cueing toward passive perimeter telemetry and herd health tracking.
