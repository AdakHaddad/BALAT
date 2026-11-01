# Connected Basys 3 Bench POC

This procedure demonstrates one connected bench data path:

```text
Synthetic FPGA trace -> risk RTL -> LEDs / JA1 logic output
                       -> USB-UART record -> dashboard -> local CSV evidence
```

The dashboard is read-only. It cannot change FPGA switches, risk state, or the
cue output. This is a bench POC, not a production collar, GNSS demonstration,
Bluetooth system, or animal-safety validation.

## 1. Prepare

Use the Basys 3 USB cable for power, JTAG, and USB-UART. Install the host
dependency once:

```bash
python3 -m pip install pyserial
```

Build and program the bridge image:

```bash
vivado -mode batch -source scripts/build_basys3_herdsync.tcl
```

Program `build/basys3_herdsync/balat_basys3_herdsync.bit` through Vivado
Hardware Manager. The expected serial port on this host is `/dev/ttyUSB1`;
confirm yours with:

```bash
python3 -m poc.herdsync_dtn.host --list-ports
```

## 2. Run the board and connected dashboard

Set `SW0=1` (run), `SW1=0` (no forced stale fault), `SW2=1` (enable the bounded
logic-level cue), and `SW3=0` (map valid), then press `BTNC` once.

Start the dashboard against the same FPGA UART records:

```bash
python3 scripts/web_demo.py --serial /dev/ttyUSB1
```

Open `http://localhost:8888`. The badge must say **BASYS3 UART** and the status
must say that it is receiving validated FPGA records. A different badge means
the dashboard is not connected to the board.

## 3. What to observe

- Board `LED0..LED4` and the dashboard risk state match directly: `SAFE`,
  `CAUTION`, `DANGER`, `COOLDOWN`, and `INVALID/fault`, respectively. Each UART
  record is latched from the same state the LEDs display, and the dashboard
  polls at 50 ms, so a transition appears within one refresh.
- Board `LED6` blinks as UART records are transmitted.
- Board `LED5` is the actual cue logic indication. The v1 UART record does not
  export this signal, so the dashboard intentionally reports it unavailable.
- `LED4` remains off during a normal run. Toggle `SW1` briefly only to show the
  fail-safe INVALID/fault response; return it low for normal capture.
- The interactive map uses OpenStreetMap tiles and is centered on the local-map
  origin. Red is the active fixed horizontal FPGA demo segment; light-blue OSM
  geometry is reference-only and is not an FPGA runtime map. Internet access is
  required for the base-map tiles.

## 4. Capture POC evidence

In the dashboard, enter a session label, press **Start**, run at least one full
~20.1-second trace cycle, then press **Stop** and **Download CSV**. The CSV is
also retained locally in `build/poc_records/` and contains one row per validated
FPGA record, including UTC capture time, sequence, position, risk, quality,
battery, and transition events.

Keep together:

- the downloaded CSV;
- a short video showing LEDs and the dashboard at the same time;
- `build/basys3_herdsync/timing_summary.rpt` and `utilization.rpt`;
- output from `bash scripts/run_herdsync_sims.sh`.

## 5. Boundaries

The trace is synthetic and the active FPGA road is one fixed segment. GNSS,
runtime map loading, BLE, a physical cue driver, and animal response are not
demonstrated. Do not connect a motor or speaker directly to JA1, do not use the
POC near live traffic, and do not make animal-welfare or road-safety claims from
this bench result.
