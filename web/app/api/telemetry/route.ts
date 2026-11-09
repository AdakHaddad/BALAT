import { timingSafeEqual } from "node:crypto";
import { NextResponse } from "next/server";

const MAX_LIMIT = 500;
const DEFAULT_LIMIT = 100;

function tokenMatches(request: Request): boolean {
  const expected = process.env.BALAT_DASHBOARD_TOKEN;
  const supplied = request.headers.get("authorization")?.replace(/^Bearer\s+/i, "");
  if (!expected || !supplied) return false;

  const expectedBytes = Buffer.from(expected);
  const suppliedBytes = Buffer.from(supplied);
  return expectedBytes.length === suppliedBytes.length
    && timingSafeEqual(expectedBytes, suppliedBytes);
}

function parseLimit(value: string | null): number {
  if (!value) return DEFAULT_LIMIT;
  const limit = Number(value);
  if (!Number.isInteger(limit) || limit < 1 || limit > MAX_LIMIT) {
    throw new Error(`limit must be an integer between 1 and ${MAX_LIMIT}`);
  }
  return limit;
}

export async function GET(request: Request) {
  if (!tokenMatches(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const supabaseUrl = process.env.BALAT_SUPABASE_URL;
  const serviceRoleKey = process.env.BALAT_SUPABASE_SERVICE_ROLE_KEY;
  if (!supabaseUrl || !serviceRoleKey) {
    return NextResponse.json({ error: "Telemetry storage is not configured" }, { status: 503 });
  }

  const url = new URL(request.url);
  let limit: number;
  try {
    limit = parseLimit(url.searchParams.get("limit"));
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Invalid limit" }, { status: 400 });
  }

  const siteId = url.searchParams.get("site_id");
  const query = new URLSearchParams({
    select: "id,captured_at,site_id,source,seq,x_cm,y_cm,dist_m,risk,risk_name,speed_kmh,approaching,cue_active,cooldown,battery_mv,quality,fix_time_s,link_status",
    order: "captured_at.desc",
    limit: String(limit),
  });
  if (siteId) query.set("site_id", `eq.${siteId}`);

  let response: Response;
  try {
    response = await fetch(`${supabaseUrl.replace(/\/$/, "")}/rest/v1/telemetry_events?${query}`, {
      headers: {
        apikey: serviceRoleKey,
        Authorization: `Bearer ${serviceRoleKey}`,
      },
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ error: "Telemetry storage is unreachable" }, { status: 502 });
  }

  if (!response.ok) {
    return NextResponse.json({ error: "Telemetry storage request failed" }, { status: 502 });
  }

  const rows: unknown = await response.json();
  return NextResponse.json({ rows });
}
