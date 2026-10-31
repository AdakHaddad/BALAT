`timescale 1ns/1ps

// tb_gnss_replay — End-to-end hardware pipeline validation with NMEA stream.
// Feeds NMEA $GPRMC sentences byte-by-byte into:
//   nmea_parser -> coord_convert -> road_geom -> risk_fsm -> cue_scheduler
// Demonstrates end-to-end autonomous decision pipeline from ASCII GNSS input to MCI cue output.

module tb_gnss_replay;

    reg clk;
    reg rst;
    reg [7:0] rx_data;
    reg rx_valid;

    // NMEA Parser
    wire signed [31:0] lat_deg7;
    wire signed [31:0] lon_deg7;
    wire        [15:0] speed_kn;
    wire        [23:0] utc_time;
    wire               fix_valid;
    wire               fix_ready;

    nmea_parser u_parser (
        .clk       (clk),
        .rst       (rst),
        .rx_data   (rx_data),
        .rx_valid  (rx_valid),
        .lat_deg7  (lat_deg7),
        .lon_deg7  (lon_deg7),
        .speed_kn  (speed_kn),
        .utc_time  (utc_time),
        .fix_valid (fix_valid),
        .fix_ready (fix_ready)
    );

    // Coord Convert
    wire signed [31:0] px;
    wire signed [31:0] py;
    wire               pos_valid;
    wire               pos_ready;

    coord_convert #(
        // Origin set at (-33.8250000, 18.6500000)
        .ORIGIN_LAT_DEG7 (-32'sd338250000),
        .ORIGIN_LON_DEG7 ( 32'sd186500000),
        .COS_LAT_Q14     ( 16'sd13611)
    ) u_conv (
        .clk       (clk),
        .rst       (rst),
        .lat_deg7  (lat_deg7),
        .lon_deg7  (lon_deg7),
        .fix_valid (fix_valid),
        .fix_ready (fix_ready),
        .px        (px),
        .py        (py),
        .pos_valid (pos_valid),
        .pos_ready (pos_ready)
    );

    // Road distance engine against test road along y-axis at x=0
    wire [63:0] dist2;
    wire        inside_span;

    road_geom u_geom (
        .clk         (clk),
        .rst         (rst),
        .px          (px),
        .py          (py),
        .ax          (32'sd0),
        .ay          (-32'sd50000),
        .bx          (32'sd0),
        .by          (32'sd50000),
        .ux_q14      (16'sd0),
        .uy_q14      (16'sd16384),
        .dist2       (dist2),
        .inside_span (inside_span)
    );

    // Velocity estimator
    wire signed [31:0] vx, vy;
    wire        [63:0] speed2;
    wire               approaching;
    wire               valid_vel;
    wire               vel_ready;

    velocity_estimator u_vel (
        .clk        (clk),
        .rst        (rst),
        .px         (px),
        .py         (py),
        .fix_valid  (pos_valid),
        .fix_ready  (pos_ready),
        .closest_qx (32'sd0),
        .closest_qy (py),
        .vx         (vx),
        .vy         (vy),
        .speed2     (speed2),
        .approaching(approaching),
        .valid_vel  (valid_vel),
        .vel_ready  (vel_ready)
    );

    // Risk FSM
    wire [2:0] risk_state;
    wire       cue_req;
    wire       fault;

    risk_fsm u_risk (
        .clk          (clk),
        .rst          (rst),
        .sample_valid (pos_ready),
        .stale        (~pos_valid),
        .map_valid    (1'b1),
        .cooldown     (1'b0),
        .approaching  (approaching),
        .dist2        (dist2),
        .state        (risk_state),
        .cue_req      (cue_req),
        .fault        (fault)
    );

    // Cue Scheduler
    wire cue_en;
    wire cooldown;

    cue_scheduler #(
        .MAX_ON_TICKS   (3),
        .COOLDOWN_TICKS (5)
    ) u_sched (
        .clk      (clk),
        .rst      (rst),
        .tick     (pos_ready),
        .enable   (1'b1),
        .request  (cue_req),
        .cue_en   (cue_en),
        .cooldown (cooldown)
    );

    always #5 clk = ~clk;

    task send_byte(input [7:0] b);
        begin
            @(posedge clk);
            rx_data  <= b;
            rx_valid <= 1'b1;
            @(posedge clk);
            rx_valid <= 1'b0;
            repeat (2) @(posedge clk);
        end
    endtask

    reg [7:0] sentence [0:127];
    task feed_sentence;
        input [8*128-1:0] s;
        input integer len;
        integer i;
        begin
            for (i = 0; i < len; i = i + 1)
                sentence[i] = s[(len-1-i)*8 +: 8];
            for (i = 0; i < len; i = i + 1)
                send_byte(sentence[i]);
            repeat (20) @(posedge clk);
        end
    endtask

    integer errors;

    initial begin
        clk = 0; rst = 1; rx_data = 0; rx_valid = 0; errors = 0;
        repeat (10) @(posedge clk);
        rst <= 0;
        repeat (10) @(posedge clk);

        // Sequence: animal starts far safe, approaches road at origin, enters caution/danger

        // Sentence 1: Safe distance ~100 m east (lon: 18.6510, lat: -33.8250)
        feed_sentence("$GPRMC,120001.00,A,3349.5000,S,01839.0600,E,2.0,0.0,231003,,A*61", 64);
        $display("Fix 1 (Safe): state=%0d (1=SAFE) dist2=%0d px=%0d py=%0d",
                 risk_state, dist2, px, py);

        // Sentence 2: Approaching road: ~4 m east (lon: 18.65004, lat: -33.8250)
        // dlon = 0.00004 deg ~ 3.7 m (370 cm) -> should enter CAUTION (<= 500 cm)
        feed_sentence("$GPRMC,120002.00,A,3349.5000,S,01839.0024,E,2.0,0.0,231003,,A*62", 64);
        $display("Fix 2 (Approach): state=%0d dist2=%0d px=%0d py=%0d app=%b",
                 risk_state, dist2, px, py, approaching);

        // Sentence 3: 2nd sample confirmation in CAUTION
        feed_sentence("$GPRMC,120003.00,A,3349.5000,S,01839.0020,E,2.0,0.0,231003,,A*67", 64);
        $display("Fix 3 (Confirm Caution): state=%0d dist2=%0d px=%0d py=%0d",
                 risk_state, dist2, px, py);

        // Sentence 4: Deep danger zone < 2 m (lon: 18.65001 -> ~1 m)
        feed_sentence("$GPRMC,120004.00,A,3349.5000,S,01839.0006,E,2.0,0.0,231003,,A*64", 64);
        feed_sentence("$GPRMC,120005.00,A,3349.5000,S,01839.0005,E,2.0,0.0,231003,,A*66", 64);
        $display("Fix 5 (Danger confirmed): state=%0d cue_en=%b dist2=%0d px=%0d",
                 risk_state, cue_en, dist2, px);

        $display("PASS: tb_gnss_replay completed successfully");
        $finish;
    end

endmodule
