#!/usr/bin/env bash
# Run the Basys 3 HerdSync-DTN UART bridge simulations.
# Usage: bash scripts/run_herdsync_sims.sh
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p build/sim

TOP_RTL="rtl/balat_herdsync_basys3_top.v rtl/trace_player.v rtl/demo_trace_rom.v rtl/road_geom.v rtl/risk_fsm.v rtl/cue_scheduler.v rtl/uart_tx.v rtl/uart_rx.v rtl/herdsync_uart_bridge.v"

iverilog -g2012 -o build/sim/tb_uart_tx tb/tb_uart_tx.v rtl/uart_tx.v
vvp build/sim/tb_uart_tx

iverilog -g2012 -o build/sim/tb_uart_rx tb/tb_uart_rx.v rtl/uart_rx.v
vvp build/sim/tb_uart_rx

iverilog -g2012 -o build/sim/tb_herdsync_uart_bridge tb/tb_herdsync_uart_bridge.v rtl/herdsync_uart_bridge.v rtl/uart_tx.v rtl/uart_rx.v
vvp build/sim/tb_herdsync_uart_bridge

iverilog -g2012 -o build/sim/tb_balat_herdsync_top tb/tb_balat_herdsync_top.v $TOP_RTL
vvp build/sim/tb_balat_herdsync_top

echo "All Basys 3 HerdSync-DTN simulations passed."
