# Pitch Deck Review & Critique — BALAT (Hackathon ITS 2026 Edition)

## 1. Narrative Flow Analysis
- **Strengths:** 
  - The deck moves logically from an acute, relatable local pain (livestock-highway collisions in rural dead zones like NTT and East Java) to the structural failure of existing alternatives (capex of physical fences, cellular/LoRa tower dependency, and electric shock controversy).
  - Clear architectural transition from Problem -> Solution -> Technical Proof on FPGA (TKT 4) -> Business Model -> GTM Beachhead -> Fundraising Ask.
  - Aligns with Hackathon ITS 2026 rubrics:
    - **Sustainable / Green Tech:** Micro-power edge computing replaces power-hungry cellular searches in dead zones.
    - **AI / Digital Enablement:** Real-time spatial edge inference and 5-state risk FSM on animal.
    - **Local Impact:** Targeted at 18.5M Indonesian cattle population (BPS 2024), focusing on East Java & NTT rangelands.
    - **TKT 3–6 Requirement:** Exactly meets TKT 4 (laboratory subsystem validation on Basys 3 FPGA).

---

## 2. Currency Strategy Analysis: Rupiah (IDR) vs. Dollar (USD)
- **Recommendation:** Dual-currency representation: **Rupiah (IDR) as primary, USD in parentheses**.
  - Example: `Rp 2.400.000 ($150)` retail price, `Rp 480.000 ($30)` BOM, `Rp 4 Miliar ($250k)` Pre-Seed ask.
- **Strategic Justification:**
  1. *Local Judges & Mentors (ITS Faculty, Indonesian Agtech Investors):* Need to evaluate practical adoption for Indonesian cattle farmers (*peternak sapi*). An adult cow is worth Rp 18M–Rp 25M; a Rp 2.4M collar is ~10-12% of asset value, proving compelling ROI in Rupiah.
  2. *International Strategic Partners (InvestHK, Tsinghua University, Garage Plus Taiwan, CityU HK):* Need USD figures to benchmark hardware BOM ($30), global market TAM ($8.5B), and venture capital ticket size ($250k Pre-Seed).

---

## 3. Unsupported Claims & Missing Evidence Audit

| Slide | Stated Claim / Assumption | Evidence Status | Risk Level | Resolution / Evidence Cited |
|---|---|---|---|---|
| 2, 6, 7 | Fencing costs Rp 100M/km; cow value Rp 18M–25M; national cattle population 18.5M. | **Supported** | Low | Cited BPS Statistik Peternakan 2023/2024; Kementan RI beef pricing; USDA NRCS fence indices. |
| 3, 4, 11 | Cattle will reliably turn away from roads based solely on acoustic/vibration cues without electric shock. | `[NEEDS EVIDENCE]` | **Critical (Existential)** | Literature cited: Campbell et al. (2019) & Lee et al. (2009) show animals habituate without paired associative reward. Stage-Gate: Supervised 14-day conditioning trial required. |
| 7, 8, 14 | Rp 2.4M ($150) collar price, Rp 480k ($30) volume BOM. | **Supported by Component Tear-down** | Medium | Component level breakdown: u-blox NEO-M8N ($8.80), nRF52840 ($2.50), LiSOCl2 battery ($7.50), IP67 casing ($4.40), buzzer ($1.50), PCB/assembly ($5.30). Total $30 / Rp 480k. |
| 9 | Pre-revenue, zero commercial deployments, bench demo only (TKT 4). | **Accurate** (Reflects true repository state) | Low | Total transparency builds investor and judge trust; highlights WNS +1.701 ns and 0 CRC errors across 1,200 hardware frames. |
| 13 | Specific founder bios, cap table, and advisory board members. | `[NEEDS EVIDENCE]` | Medium | Formalize founder biographies and secure letters of intent (LOI) from veterinary faculty and regional livestock associations. |
| 15 | Rp 4 Miliar ($250k) Pre-Seed round size and 18-month budget allocations. | `[NEEDS EVIDENCE]` | Medium | Sized appropriately for incubation stage under Hackathon ITS / strategic partner angel co-investment. |

---

## 4. Differentiation Assessment
- **Versus Incumbent Virtual Fencing (Halter, Vence, Gallagher eShepherd, Nofence):**
  - *Current Strength:* High differentiation on two dimensions: (1) Zero cellular/gateway infrastructure required; (2) Non-aversive humane guidance (no electric shock).
  - *Vulnerability:* Incumbents already possess venture capital and field sales teams. BALAT wins on unit economics (Rp 2.4M vs >Rp 10M+) and operation in 100% cellular blackouts.
- **Versus Ear Tags (Ceres Tag, Moocall):**
  - *Strength:* Clear distinction between passive tracking (reporting a dead animal after the strike) and active prevention (real-time edge approach trajectory prediction).

---

## 5. Summary Verdict & Readiness
The deck is optimized for Hackathon ITS 2026. It directly satisfies the competition's criteria (TKT 3–6 requirement, sustainable energy efficiency, local livestock impact in East Java and NTT, and international investor scalability for partners like InvestHK and Garage Plus).
