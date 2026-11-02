# BALAT Field Console

This Next.js dashboard is a read-only presentation layer for the BALAT bench
telemetry bridge. It polls the bridge's validated `/api/state` endpoint and
falls back to the built-in synthetic collar snapshot when the bridge is not
available. It never sends commands to the FPGA or cue output.

## Run with the telemetry bridge

From the repository root, start the bridge:

```bash
python3 scripts/web_demo.py --simulate --port 8888
```

In another terminal, start the Next.js app:

```bash
cd web
npm run dev
```

The dashboard defaults to `http://localhost:8888`. To use another bridge host
or port, set `NEXT_PUBLIC_BALAT_API_URL` before starting Next.js:

```bash
NEXT_PUBLIC_BALAT_API_URL=http://192.168.1.20:8888 npm run dev
```

Use `--serial /dev/ttyUSB1` instead of `--simulate` when reading validated
Basys 3 USB-UART records. The browser-facing bridge remains read-only; recording
controls belong to the legacy bridge page and are intentionally not exposed as
FPGA controls by this dashboard.

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

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
- Publish directory: `.next`

Set `NEXT_PUBLIC_BALAT_API_URL` in the Netlify site environment variables when
the deployed dashboard should poll a reachable telemetry bridge. If it is not
set, the dashboard uses its built-in synthetic snapshot.

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
