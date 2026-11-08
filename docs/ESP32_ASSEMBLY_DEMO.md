# ESP32-C3 PCB Assembly and Dashboard Demo

## Board and power gate

The ESP-IDF defaults now match the main PCB nets: buzzer GPIO3, motor GPIO4,
GPS power GPIO5, button GPIO6, LED GPIO10, and GPS TX to UART RX on GPIO20.
USB commands/logs use native USB Serial/JTAG so the console does not share
GPIO20 with the GPS receiver. GPIO6's existing button is used as a
**hold-to-enable** for bounded buzzer and motor cues; releasing it disables
both outputs. The dashboard cannot enable cues.

The board is signal-mapped, but PCB v1 remains **HOLD for power-up with its
battery/TP4056/solar system**. Do not attach a battery, charger, solar panel,
or motor load until the power-path review is closed. The initial PCB check is
logic-only with outputs disconnected; use the independent breadboard setup
below if safe bench power has not been confirmed. See
[the PCB review](PCB_LAYOUT_REVIEW_2026-11-08.md).

## Bench bill of materials

- ESP32-C3 Super Mini and a USB data cable.
- 3.3 V UART GNSS receiver with antenna for live input, or no receiver for the
  mock NMEA demo.
- Assembled main PCB with its fitted 220 Ω status LED and protected buzzer and
  motor transistor stages, or a breadboard equivalent.
- The PCB button on GPIO6; hold it only for an intentional bounded-output
  bench check. Releasing it immediately disarms cue outputs.
- Breadboard, jumper wires, and multimeter.

## Wiring

All grounds must be common. Verify receiver voltage and UART logic before
connection. The PCB routes receiver TX to GPIO20; GPS power is switched through
GPIO5. USB console uses the ESP32-C3 native USB Serial/JTAG interface.

| ESP32-C3 signal | Bench connection |
|---|---|
| GPIO3 / `BUZ_CTRL` | PCB Q1 driver control net |
| GPIO4 / `MOT_CTRL` | PCB Q2 driver control net |
| GPIO5 / `GPS_EN` | PCB Q3 high-side GPS switch; active low |
| GPIO6 / `BTN` | Hold button to GND to physically permit bounded cues |
| GPIO10 / `LED_CTRL` | PCB D3 status LED through existing R10 220 Ω resistor |
| GPIO20 / UART1 RX | GPS module TX, 3.3 V UART input |
| Native USB Serial/JTAG | Dashboard bridge commands and firmware logs |
| GND | Common logic and peripheral ground |

Never connect a motor or buzzer directly to an ESP32 pin. The PCB's protected
driver stages handle the loads, but keep the motor disconnected during the
first logic checks. Mock GPS cannot arm outputs; only a physically held PCB
button can do that.

## First power-up and firmware

1. Inspect for shorts between 3V3 and GND. Leave the battery, TP4056, solar
   panels, motor, and buzzer disconnected. Do not power PCB v1 until its
   USB/battery power path has been checked; use the breadboard setup below to
   flash and validate firmware until safe PCB bench power is confirmed.
2. Connect the board and identify its port (`/dev/ttyACM0`, `/dev/ttyUSB0`, or
   the matching COM port). Close any serial monitor before another program
   opens that port.
3. From the repository root, build and flash:

   ```bash
   cd esp32
   . /home/muqtada/esp/esp-idf/export.sh
   idf.py set-target esp32c3
   idf.py build
   idf.py -p /dev/ttyACM0 flash monitor
   ```

4. Confirm the boot prints the command list and `MAP` reports a valid map.
   The status LED should blink while the fix is INVALID. Run `STATUS` and inspect
   the `risk`, `fix_valid`, `map_valid`, `fault`, and `cue_active` fields.
5. Close IDF Monitor before starting the web bridge; only one application can
   own the USB serial port at a time.

The USB console is also the mock NMEA command input. Hold the PCB button to
GND only when intentionally checking bounded output; releasing it disables
the buzzer and motor controls.

## Mock GPS and dashboard demonstration

Install the serial package once if needed: `python3 -m pip install pyserial`.
From the repository root, start the ESP32 bridge without `--mock-gps` to
control replay from the dashboard:

```bash
python3 scripts/web_demo.py --esp32-serial /dev/ttyACM0 --interval 0.1
```

The bridge reads decision logs and exposes them at `/api/state`. Dashboard
buttons provide Start, Pause, Reset, and GPS mode plus the fix interval. These
controls only send the checksummed NMEA mock input; they cannot arm cues. The
bridge transforms `data/demo_trace.csv` around the firmware origin, and the
firmware parses it through the normal NMEA, fix-gate, map, risk, and cue path.
The trace is synthetic, not GPS reception or a field measurement. Keep the PCB
button released during setup and dashboard checks.

In another terminal:

```bash
cd web
NEXT_PUBLIC_BALAT_API_URL=http://localhost:8888 bun run dev
```

Open `http://localhost:3000/?pitch=1`. When ESP32 logs arrive, the header says
`LIVE ESP32 TELEMETRY`; the collar risk, distance, and marker use the ESP32
state/local coordinates. The map view switches to the manifest origin
(-33.825, 18.65) and labels the position as a bench demo. The point overlay is
approximate, and the page does not draw the firmware's exact road-segment
geometry. Dashboard controls affect mock GPS input only; cue enable remains a
physical hold on the PCB button. Stop the bridge with Ctrl-C.

For real GNSS, choose **GPS mode** on the dashboard (or send `MOCK STOP`), then
connect receiver TX to GPIO20 and receiver GND to ESP32 GND. The PCB GPIO5
switch powers the receiver. Firmware requires recent valid GGA quality/HDOP
data before accepting RMC.

## Collar PCB assembly gate

The current KiCad DRC run found 7 courtyard-overlap errors on the main PCB and
2 on the power PCB (KiCad 8.0.9). The boards have no unconnected pads, but the
errors should be reviewed before fabrication. Silkscreen warnings are also
present. Firmware now matches the main PCB signal nets; GPIO6's button is
repurposed as a hold-to-enable for this bench demo. Resolve power-path findings
before applying power to the collar assembly.

Initial tests must use simulation, USB replay, LEDs, and protected dummy loads
only. This prototype
does not establish animal-guidance effectiveness and is not a substitute for
fencing, supervision, or road-safety infrastructure.
