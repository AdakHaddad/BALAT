# Build the Basys 3 FPGA image that accepts dashboard-driven mock NMEA.
# Usage: vivado -mode batch -source scripts/build_basys3_dashboard.tcl
set script_dir [file normalize [file dirname [info script]]]
set repo_dir [file normalize [file join $script_dir ..]]
set build_dir [file join $repo_dir build basys3_dashboard]
file mkdir $build_dir
file delete -force [file join $build_dir balat_basys3_dashboard.bit]

set rtl_files [list \
    [file join $repo_dir rtl balat_basys3_dashboard_top.v] \
    [file join $repo_dir rtl uart_rx.v] \
    [file join $repo_dir rtl coord_convert.v] \
    [file join $repo_dir rtl nmea_parser.v] \
    [file join $repo_dir rtl road_geom.v] \
    [file join $repo_dir rtl risk_fsm.v] \
    [file join $repo_dir rtl cue_scheduler.v] \
    [file join $repo_dir rtl uart_tx.v] \
    [file join $repo_dir rtl herdsync_uart_bridge.v] \
]
read_verilog $rtl_files
read_xdc [file join $repo_dir constraints basys3_dashboard.xdc]
synth_design -top balat_basys3_dashboard_top -part xc7a35tcpg236-1
opt_design
place_design
route_design
write_checkpoint -force [file join $build_dir balat_basys3_dashboard_routed.dcp]
report_utilization -file [file join $build_dir utilization.rpt]
report_timing_summary -file [file join $build_dir timing_summary.rpt]
set worst_path [get_timing_paths -setup -max_paths 1]
if {[llength $worst_path] == 0} {
    error "No constrained setup path found; refusing to produce a demo bitstream."
}
set worst_slack [get_property SLACK [lindex $worst_path 0]]
if {$worst_slack < 0.0} {
    error "Setup timing is not met (WNS ${worst_slack} ns); refusing to produce a demo bitstream."
}
write_bitstream -force [file join $build_dir balat_basys3_dashboard.bit]
puts "BALAT Basys 3 dashboard demo build complete: $build_dir"
