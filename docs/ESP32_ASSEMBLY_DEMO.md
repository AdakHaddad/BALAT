# ESP32-C3 PCB Assembly and Dashboard Demo

## Board and power gate

The ESP-IDF defaults now match the main PCB nets: buzzer GPIO3, motor GPIO4,
GPS power GPIO5, cue-enable GPIO1, LED GPIO10, and GPS TX to UART RX on GPIO20.
USB commands/logs use native USB Serial/JTAG so the console does not share
GPIO20 with the GPS receiver. GPIO1 is used as a
**hold-to-enable** for bounded cues; releasing it disables outputs. Synthetic
mock mode can drive the status LED and, while the button is held, the bounded
vibration and buzzer outputs. The dashboard cannot enable cues.

The standalone breadboard firmware maps green SAFE to GPIO10, yellow
CAUTION/COOLDOWN to GPIO21, red DANGER to GPIO7, and blinks red for INVALID.
GPIO7 and GPIO21 are not routed on PCB v1. Its fitted GPIO10 LED therefore
shows green for SAFE only; use the separate breadboard setup for all three
colors.

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
- A button or jumper from GPIO1 to GND; hold it only for an intentional bounded-output
  bench check. Releasing it immediately disarms cue outputs.
- Breadboard, jumper wires, and multimeter.

## Wiring

All grounds must be common. Verify receiver voltage and UART logic before
connection. The PCB routes receiver TX to GPIO20; GPS power is switched through
GPIO5. USB console uses the ESP32-C3 native USB Serial/JTAG interface.

| ESP32-C3 signal | Bench connection |
|---|---|
| GPIO3 / `BUZ_CTRL` | PCB Q1 buzzer-driver control; for a separate breadboard module, connect to 3.3 V-compatible active-buzzer `SIG` |
| GPIO4 / `MOT_CTRL` | PCB Q2 vibration-driver control; for a separate breadboard module, connect to driver `IN`, never to a bare motor |
| GPIO5 / `GPS_EN` | PCB Q3 high-side GPS switch; active low |
| GPIO1 / `CUE_EN` | Hold jumper/button to GND to physically permit bounded cues |
| GPIO10 / `LED_CTRL` | PCB D3 status LED through existing R10 220 Ω resistor |
| GPIO7 | Red LED on standalone breadboard only; not routed on PCB v1 |
| GPIO21 | Yellow LED on standalone breadboard only; not routed on PCB v1 |
| GPIO20 / UART1 RX | GPS module TX, 3.3 V UART input |
| Native USB Serial/JTAG | Dashboard bridge commands and firmware logs |
| GND | Common logic and peripheral ground |
| 3V3 / 5V | Module `VCC` only at its marked/datasheet-rated voltage; verify the supply can provide module current |

For standalone breadboard modules, GPIO3 and GPIO4 connect only to their
3.3 V-compatible, active-high logic inputs (`SIG`/`IN`). A 3-pin vibration
module with `IN`, `VCC`, and `GND` and an integrated driver needs no additional
driver board. Connect module GND to ESP32 GND. Use 3V3 or 5V at module VCC only
when that matches its rating; use a separate current-limited supply if the
module's current exceeds the ESP32 board supply rating. A bare two-wire
vibration motor removed from a PS controller still needs a suitable protected
driver stage. Never connect a motor or buzzer load directly to an ESP32 pin.
Keep actuator loads disconnected during first logic checks. Mock GPS cannot
arm cues; only a physically held GPIO1 jumper/button can do that.

Current firmware behavior on valid GNSS: `CAUTION` gives a bounded vibration
pulse on GPIO4 only; `DANGER` activates the protected buzzer and vibration
outputs together. GPIO1 must be held to enable cues. Each pulse is limited to
500 ms. A transition into DANGER may override the 30-second cooldown once so
the danger cue is not delayed; repeated cues at the same risk level still
follow the cooldown. Mock/demo mode uses the same cue mapping while the button
is held.

## First power-up and firmware

1. Inspect for shorts between 3V3 and GND. Leave the battery, TP4056, solar
   panels, motor, and buzzer disconnected. Do not power PCB v1 until its
   USB/battery power path has been checked; use the breadboard setup below to
   flash and validate firmware until safe PCB bench power is confirmed.
2. Connect the board and identify its port (`/dev/ttyACM0`, `/dev/ttyUSB0`, or
   the matching COM port). Before flashing, stop the dashboard bridge with
   Ctrl-C and close any serial monitor or other program using that port. Only
   one program can own the ESP32 USB serial port at a time.
3. From the repository root, build and flash:

   ```bash
   cd esp32
   . /home/muqtada/esp/esp-idf/export.sh
   idf.py set-target esp32c3
   idf.py build
   idf.py -p /dev/ttyACM0 flash monitor
   ```

4. Confirm the boot prints the command list and `MAP` reports a valid map.
   On the standalone breadboard, red blinks for INVALID, yellow indicates
   CAUTION/COOLDOWN, red indicates DANGER, and green indicates SAFE. On PCB v1,
   only its GPIO10 green SAFE indicator is connected. Run `STATUS` and inspect
   the `risk`, `fix_valid`, `map_valid`, `fault`, and `cue_active` fields.
5. After confirming boot, exit IDF Monitor with Ctrl-] before starting the web
   bridge. Do not run flashing, IDF Monitor, and the dashboard bridge against
   the same serial port concurrently.

The USB console is also the mock NMEA command input. Hold the GPIO1 jumper/button to
GND only when intentionally checking bounded output; releasing it disables
the buzzer and motor controls.

## Mock GPS and dashboard demonstration

### Direct BLE demo (no USB serial bridge)

The ESP32-C3 firmware advertises as `BALAT-C3`. In Chrome or Edge, open the
dashboard from `http://localhost:3000` or an HTTPS deployment, choose **Connect
ESP32 BLE**, and select `BALAT-C3` in the browser prompt. Web Bluetooth is not
available to pages served from an insecure LAN address such as
`http://192.168.x.x`.

Use **Start replay** to run the 201 synthetic fixes compiled into the ESP32
firmware. The dashboard receives risk and position updates over BLE
notifications. **Pause**, **Reset**, and **GPS mode** control that replay; while
paused, clicking the map selects a geographic mock location and dragging the
marker sends individual synthetic positions. The map overlays the same OSM
segments and projection metadata used by the firmware map. A single fixed
point does not imply approach; drag toward a mapped road to provide consecutive
approach fixes. This direct BLE path uses firmware fixes and does not exercise
the NMEA parser. Keep actuator loads disconnected during the demonstration.

### USB serial NMEA replay

Install the serial package once if needed: `python3 -m pip install pyserial`.
From the repository root, start the ESP32 bridge without `--mock-gps` to
control replay from the dashboard:

```bash
python3 scripts/web_demo.py --esp32-serial /dev/ttyACM0 --interval 0.1
```

The bridge reads decision logs and exposes them at `/api/state`. Dashboard
buttons provide Start, Pause, Reset, and GPS mode plus the fix interval. In
ESP32 mode, clicking or dragging the interactive map sends the selected
geographic location as checksummed NMEA through the same parser and fix gate.
The map overlays the OSM segments loaded by the firmware. These controls only
send synthetic input; they cannot arm cues. The trace is synthetic, not GPS
reception or a field measurement. Keep the PCB
button released during setup and dashboard checks. For the buzzer/motor demo,
hold the physical button as the hold-to-enable; the mock trace alone cannot arm
cues.

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
physical hold on the GPIO1 jumper/button. Stop the bridge with Ctrl-C.

For real GNSS, choose **GPS mode** on the dashboard (or send `MOCK STOP`), then
connect receiver TX to GPIO20 and receiver GND to ESP32 GND. The PCB GPIO5
switch powers the receiver. Firmware requires recent valid GGA quality/HDOP
data before accepting RMC.

## Collar PCB assembly gate

The current KiCad DRC run found 7 courtyard-overlap errors on the main PCB and
2 on the power PCB (KiCad 8.0.9). The boards have no unconnected pads, but the
errors should be reviewed before fabrication. Silkscreen warnings are also
present. This bench image uses GPIO1 (not GPIO6/MOSI) as a dedicated
hold-to-enable jumper/button. Resolve power-path findings
before applying power to the collar assembly.

Initial tests must use simulation, USB replay, LEDs, and protected dummy loads
only. This prototype
does not establish animal-guidance effectiveness and is not a substitute for
fencing, supervision, or road-safety infrastructure.
