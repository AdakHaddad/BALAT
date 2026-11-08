# BALAT PCB v1 layout and firmware compatibility review

Review date: 2026-11-08. KiCad CLI used: 8.0.9. Boards reviewed:
`BALAT_PCB_v1/BALAT_PCB_v1/utama/balat_utama.kicad_pcb` and
`BALAT_PCB_v1/BALAT_PCB_v1/daya/balat_daya.kicad_pcb`.

## Decision

**HOLD: do not power the collar PCB until the power-path, component, and DRC
items below are resolved.** The firmware now has a PCB signal profile matching
the main-board netlist, and repurposes the existing GPIO6 button as a
hold-to-enable for a bench demo. This follow-up resolves the original firmware
pin mismatch for signal-only integration; it does not clear the PCB power or
fabrication holds.

This is the review-time pin comparison from 2026-11-08. The current PCB profile
and dashboard mock-input procedure are documented in
[`ESP32_ASSEMBLY_DEMO.md`](ESP32_ASSEMBLY_DEMO.md).

## Pin map conflict

The schematic's `generator/cek_netlist.py` explicitly maps the Super Mini pads
as follows. This mapping is also reflected by the integrated schematic nets.

| Signal | PCB v1 route | Current firmware default | Finding |
|---|---|---|---|
| GPIO0 | Battery voltage divider | Manual-disable input | Analog battery signal is not a disable switch |
| GPIO1 | DS18B20 data | Physical cue-enable input | Sensor bus is not a dedicated cue-enable switch |
| GPIO3 | Buzzer driver `BUZ_CTRL` | Caution LED output | Firmware would drive the buzzer transistor as an LED |
| GPIO4 | Motor driver `MOT_CTRL` | GNSS UART1 RX | GNSS input collides with motor-driver control |
| GPIO5 | GPS power switch `GPS_EN` | GNSS UART1 TX | UART TX can affect GPS power gate |
| GPIO6 | Report button `BTN` | Buzzer driver output | Firmware buzzer output collides with button net |
| GPIO7 | Not routed | Motor driver output | No PCB connection for configured output |
| GPIO10 | Status LED `LED_CTRL` | Invalid LED | Compatible signal, subject to polarity verification |
| GPIO20 | GPS receiver TX | UART0 RX in current default console config | GNSS/console net collision |
| GPIO21 | Not routed | UART0 TX in current default console config | No PCB pad route |

The netlist's GPS receiver signal is labelled `GPS_TX` and terminates at GPIO20.
The firmware expects the receiver's TX on GPIO4. A change to just the Kconfig
defaults is insufficient: GPIO0 and GPIO1 are occupied, GPIO5 is a power
control, GPIO20 is also the configured UART0 RX, and no separate cue-enable
switch is present. Produce a reviewed schematic revision with a complete
pin-allocation and power plan, then build and verify against that revision.

## Power-path concern

In the schematic, ESP32 Super Mini pin 1 (`5V`) is connected to the PCB's
`VBAT` rail. When the battery switch is on, USB VBUS may therefore be tied to
the battery/motor supply rail through the board's 5V pin. Do not program over
USB with the collar battery switched on or connected until the actual Super
Mini board's USB/5V topology is checked and the power path is redesigned to
prevent USB from being connected directly to a Li-ion cell. The current note
to switch the collar off before USB upload is not enough protection if a
second power source is connected elsewhere; isolate the battery and TP4056
output during bench programming.

Also confirm the actual Super Mini regulator's input range against the full
18650 voltage range. The PCB feeds a single-cell battery rail to the module's
5V pin; do not assume the 3.3 V rail stays regulated as the cell discharges.

## DRC and visual layout

Fresh `kicad-cli pcb drc --severity-error` runs report:

- Main PCB: **7 errors**, all `courtyards_overlap`; 0 unconnected items.
- Power PCB: **2 errors**, all `courtyards_overlap`; 0 unconnected items.

When warning severities are included, the main board reports 123 violations
and the power board 25. Most are silkscreen overlaps/clipping and missing local
footprint library definitions. The old `PANDUAN_PCB.md` statement that there
are no DRC errors is stale. Courtyard intersections do not by themselves prove
copper shorts, but they need footprint/body/assembly clearance review and the
DRC report should be brought to zero errors before fabrication. Check the
silkscreen around connectors and the ESP32 antenna keepout in the fabrication
view as well.

## Required before PCB assembly

1. Confirm the firmware PCB profile against the assembled module revision and
   check schematic/netlist parity before using the board.
2. For a production collar revision, add a dedicated default-off cue-enable
   switch and a separate manual-disable control. The current bench firmware
   temporarily uses the existing GPIO6 button as hold-to-enable.
3. Add a proper USB/battery power-path solution; validate battery charging,
   protection, regulator input range, motor current, and ground return.
4. Confirm the buzzer and motor drivers, transistor pinouts, diode polarity,
   connector pin order, and LED polarity against the actual parts.
5. Regenerate fabrication outputs and run current KiCad DRC plus schematic
   parity. Resolve all DRC errors and record the final report with the PCB
   revision.
6. First power with USB only and all dummy outputs disconnected. Measure
   rails before connecting the GNSS module; then validate with LEDs and a
   protected dummy load. Keep animal and road-side use out of scope.
