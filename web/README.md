# BALAT Field Console

This Next.js dashboard displays BALAT bench telemetry. With an ESP32 source it
also exposes controls for synthetic GPS input (start, pause, reset, GPS mode,
and fix interval). Those controls cannot arm the cue output; the PCB button is
the physical hold-to-enable. The dashboard falls back to its built-in synthetic
collar snapshot when the telemetry bridge is unavailable.

## Run with the telemetry bridge

From the repository root, start the bridge:

```bash
python3 scripts/web_demo.py --simulate --port 8888
```

In another terminal, start the Next.js app:

```bash
cd web
bun run dev
```

The dashboard defaults to `http://localhost:8888`. To use another bridge host
or port, set `NEXT_PUBLIC_BALAT_API_URL` before starting Next.js:

```bash
NEXT_PUBLIC_BALAT_API_URL=http://192.168.1.20:8888 bun run dev
```

Use `--serial /dev/ttyUSB1` instead of `--simulate` when reading validated
Basys 3 USB-UART records. The browser-facing bridge remains read-only; recording
controls belong to the legacy bridge page and are intentionally not exposed as
FPGA controls by this dashboard.

## ESP32-C3 BLE demo and mock NMEA

For a direct BLE demo without a serial bridge, flash the ESP32-C3 firmware,
open the dashboard in Chrome or Edge on `localhost` or HTTPS, and connect to
`BALAT-C3`. The BLE panel replays the 201 synthetic fixes compiled into the
firmware and displays live status notifications. This is a firmware fixture
replay, not live GPS or NMEA-parser input. Keep the physical cue-enable button
released. Detailed board setup and safety checks are in
[`../docs/ESP32_ASSEMBLY_DEMO.md`](../docs/ESP32_ASSEMBLY_DEMO.md).

In ESP32 mode the map is centered on the firmware map origin, overlays its
OSM-derived road segments, and lets you click or drag a synthetic point. Drag
toward a road to send consecutive mock fixes and exercise approach detection;
the selected point is synthetic and does not come from a GNSS receiver.

### USB serial NMEA input

The same bridge can read ESP32 key/value decision logs. Connect and flash the
ESP32-C3 using [`../docs/ESP32_ASSEMBLY_DEMO.md`](../docs/ESP32_ASSEMBLY_DEMO.md),
then start the bridge without `--mock-gps` to control simulated fixes from the
dashboard:

```bash
python3 scripts/web_demo.py --esp32-serial /dev/ttyACM0 --interval 0.1
```

The replay controls send checksummed GGA/RMC commands over USB serial, and
firmware uses its regular NMEA parser and fix gate. A manually selected map
point instead sends interpolated `FIX <x_cm> <y_cm>` synthetic fixes at the
chosen interval, moving toward the selected point at up to 5 m/s. This cap is
for smooth mock movement only; firmware fix, stale, and risk checks remain
enabled. Both are simulated inputs, not live GNSS; map-point mode turns GPS
module power off and does not require the receiver. In a second terminal:

```bash
cd web
NEXT_PUBLIC_BALAT_API_URL=http://localhost:8888 bun run dev
```

Open `http://localhost:3000/?pitch=1`, select or drag a map point, and the
bridge smoothly moves the GPS-free mock fix toward it. The simplified panel
offers Pause and Use map point; it does not switch on GPS-module power. In the
full operator view, Start/Pause/Reset control the NMEA trace and GPS mode is
for an actually connected receiver. Close IDF Monitor before the bridge takes
the USB port. Hold the PCB button only for a deliberate bounded-output bench
demo; leave it released during setup and mock-input checks.

ESP32 local coordinates use the South Africa map origin in the firmware map
manifest. The dashboard centres its bench map there. A manually selected
synthetic point remains visible while replaying. The last reported position
also remains visible after a fix becomes invalid, labeled as invalid rather
than presented as live. Invalid/stale data cannot enable a cue. The
pitch-mode bench view labels a rejected manual mock-point fix `WAITING FOR
FIX`, while retaining the red LED and cue-held indication; the full operator
view keeps the explicit INVALID classification. The pitch-mode bench view
shows the three status LED pins and resistors:
GPIO7/red, GPIO21/yellow, GPIO10/green, each through its own 220 Ω resistor,
with all LED cathodes connected to GND. The geographic point overlay is
approximate, and the page does not draw the firmware's exact road-segment lines.
Other collars remain sample data only when ESP32 telemetry is absent.
Firmware pin defaults match the PCB signal nets, but its power path remains on
HOLD. Review [`../docs/PCB_LAYOUT_REVIEW_2026-11-08.md`](../docs/PCB_LAYOUT_REVIEW_2026-11-08.md)
before powering the collar PCB.

## Getting Started

First, run the development server:

```bash
npm run dev
# or, with Bun
bun dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

For a production-style pitch demonstration, open
`http://localhost:3000/?pitch=1`. This view opens on the functional dashboard:
an OpenStreetMap view of the configured corridor, collar status, risk state,
telemetry health, events, and bench evidence. The map is a real external map
surface; local collar/map-manifest overlays remain separate until a production
tile and geospatial data service is configured.
The **How it works** explainer is available as a separate view from the pitch
header or the operator sidebar; it is not placed above the dashboard.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Netlify

The repository includes a root-level [`netlify.toml`](../netlify.toml) configured
with `web/` as the Netlify base directory. In Netlify, connect the repository
and leave the build settings at their detected values:

- Base directory: `web`
- Build command: `npm run build`

Set `NEXT_PUBLIC_BALAT_API_URL` in the deployment environment variables when
the dashboard should poll a reachable telemetry bridge. If it is not set, the
dashboard uses its built-in synthetic snapshot.

The authenticated telemetry history endpoint requires these server-only
variables:

- `BALAT_SUPABASE_URL`
- `BALAT_SUPABASE_SERVICE_ROLE_KEY`
- `BALAT_DASHBOARD_TOKEN`

Send the dashboard token as `Authorization: Bearer <token>`. Never use a
`NEXT_PUBLIC_*` variable for either secret.

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

## Hardware dashboard demos

For the ESP32-C3 PCB demo, the local Python bridge can send dashboard-controlled
checksummed mock NMEA sentences to firmware using `--esp32-serial PORT`. Browser
replay controls cannot enable the buzzer or motor; the physical PCB button is
still required.

For the FPGA GPS-input demo, build/program the separate Basys 3 image described
in [`../docs/BASYS3_DASHBOARD_NMEA.md`](../docs/BASYS3_DASHBOARD_NMEA.md), then run
`python3 scripts/web_demo.py --basys3-nmea-serial PORT`. The same replay controls
stream checksummed NMEA into the RTL parser and display FPGA telemetry records.
The FPGA cue is observable on its board LED/JA1; JA1 is not an actuator output.
