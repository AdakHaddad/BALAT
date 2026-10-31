# Non-project Vivado build for the Basys 3 HerdSync-DTN UART bridge demo.
# Usage: vivado -mode batch -source scripts/build_basys3_herdsync.tcl
# Outputs: build/basys3_herdsync/balat_basys3_herdsync.bit plus reports.

set script_dir [file normalize [file dirname [info script]]]
set repo_dir   [file normalize [file join $script_dir ..]]
set build_dir  [file join $repo_dir build basys3_herdsync]

file mkdir $build_dir

set rtl_files [list \
    [file join $repo_dir rtl balat_herdsync_basys3_top.v] \
    [file join $repo_dir rtl trace_player.v] \
    [file join $repo_dir rtl demo_trace_rom.v] \
    [file join $repo_dir rtl road_geom.v] \
    [file join $repo_dir rtl risk_fsm.v] \
    [file join $repo_dir rtl cue_scheduler.v] \
    [file join $repo_dir rtl uart_tx.v] \
    [file join $repo_dir rtl uart_rx.v] \
    [file join $repo_dir rtl herdsync_uart_bridge.v] \
]

read_verilog $rtl_files
read_xdc [file join $repo_dir constraints basys3_herdsync.xdc]

synth_design -top balat_herdsync_basys3_top -part xc7a35tcpg236-1
opt_design
place_design
route_design

write_checkpoint -force [file join $build_dir balat_basys3_herdsync_routed.dcp]
write_bitstream -force [file join $build_dir balat_basys3_herdsync.bit]
report_utilization -file [file join $build_dir utilization.rpt]
report_timing_summary -file [file join $build_dir timing_summary.rpt]

puts "BALAT Basys 3 HerdSync bridge build complete: $build_dir"
