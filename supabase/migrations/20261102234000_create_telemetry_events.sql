create table if not exists public.telemetry_events (
  id bigint generated always as identity primary key,
  captured_at timestamptz not null default now(),
  site_id text not null default 'default',
  source text not null,
  seq bigint not null,
  x_cm integer not null,
  y_cm integer not null,
  dist_m double precision not null,
  risk smallint not null,
  risk_name text not null,
  speed_kmh double precision not null,
  approaching boolean not null,
  cue_active boolean,
  cooldown boolean not null,
  battery_mv integer not null,
  quality smallint not null,
  fix_time_s bigint not null,
  link_status text not null,
  created_at timestamptz not null default now(),
  constraint telemetry_events_risk_check check (risk between 0 and 4),
  constraint telemetry_events_quality_check check (quality between 0 and 100),
  constraint telemetry_events_battery_check check (battery_mv >= 0),
  constraint telemetry_events_source_check check (length(source) between 1 and 64),
  constraint telemetry_events_risk_name_check check (risk_name in ('INVALID', 'SAFE', 'CAUTION', 'DANGER', 'COOLDOWN'))
);

create index if not exists telemetry_events_site_captured_idx
  on public.telemetry_events (site_id, captured_at desc);

create index if not exists telemetry_events_site_seq_idx
  on public.telemetry_events (site_id, seq);

alter table public.telemetry_events enable row level security;

-- Ingestion uses the server-side service role. Add a narrowly scoped read
-- policy later when the dashboard starts querying historical telemetry.

create or replace function public.purge_old_telemetry_events()
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  deleted_count integer;
begin
  delete from public.telemetry_events
  where captured_at < now() - interval '90 days';
  get diagnostics deleted_count = row_count;
  return deleted_count;
end;
$$;

revoke all on function public.purge_old_telemetry_events() from public;
