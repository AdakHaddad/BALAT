// balat_basys3_top — Basys 3 demo integration for the BALAT risk pipeline.
//
// This demo replays a compiled synthetic local-coordinate trace through the
// road-distance engine, risk FSM, and bounded cue scheduler. It does not
// include a GNSS receiver or NMEA parser; the trace stands in for recorded
// position fixes. cue_out is a 3.3 V logic-level observation output on JA1.
// It must never drive a speaker, motor, or other actuator directly.
//
// Controls (Basys 3):
//   SW0  run / pause trace replay
//   SW1  force stale/invalid input
//   SW2  enable cue output
//   SW3  force map fault
//   BTNC reset (active high)
//
// LEDs:
//   LED[2:0]  risk state: 0 INVALID, 1 SAFE, 2 CAUTION, 3 DANGER, 4 COOLDOWN
//   LED[3]    input valid (not stale)
//   LED[4]    approaching
//   LED[5]    cue active
//   LED[6]    cooldown
//   LED[7]    fault (stale or map invalid)
//   LED[8]    distance <= 1 m
//   LED[9]    distance <= 2 m
//   LED[10]   distance <= 3 m
//   LED[11]   distance <= 4 m
//   LED[12]   distance <= 5 m
//   LED[13]   distance <= 7 m
//   LED[14]   distance <= 10 m
//   LED[15]   1 Hz heartbeat
module balat_basys3_top #(
    parameter integer CLK_PER_TICK    = 10_000_000, // 100 ms at 100 MHz
    parameter integer LAST_INDEX      = 200,
    parameter integer CLK_PER_MS      = 100_000,    // 1 ms at 100 MHz
    parameter integer STALE_MS        = 500,
    parameter integer MAX_ON_TICKS    = 5,
    parameter integer COOLDOWN_TICKS  = 30,
    parameter integer HEARTBEAT_DIV   = 50_000_000
) (
    input  wire        clk,
    input  wire        btnC,
    input  wire [3:0]  sw,
    output wire [15:0] led,
    output wire        cue_out
);

    localparam [2:0] ST_INVALID = 3'd0;

    localparam [63:0] DIST_1M2  = 64'd10000;   // (100 cm)^2
    localparam [63:0] DIST_2M2  = 64'd40000;
    localparam [63:0] DIST_3M2  = 64'd90000;
    localparam [63:0] DIST_4M2  = 64'd160000;
    localparam [63:0] DIST_5M2  = 64'd250000;
    localparam [63:0] DIST_7M2  = 64'd490000;
    localparam [63:0] DIST_10M2 = 64'd1000000;

    (* ASYNC_REG = "TRUE" *) reg [2:0] rst_sync;
    wire rst;

    always @(posedge clk or posedge btnC) begin
        if (btnC)
            rst_sync <= 3'b111;
        else
            rst_sync <= {rst_sync[1:0], 1'b0};
    end
    assign rst = rst_sync[2];

    wire run          = sw[0];
    wire force_stale  = sw[1];
    wire cue_enable   = sw[2];
    wire map_valid    = ~sw[3];

    wire        sample_tick;
    wire [15:0] trace_index;
    wire signed [31:0] rom_data;

    trace_player #(
        .CLK_PER_TICK (CLK_PER_TICK),
        .LAST_INDEX   (LAST_INDEX)
    ) u_trace_player (
        .clk   (clk),
        .rst   (rst),
        .run   (run),
        .tick  (sample_tick),
        .index (trace_index)
    );

    demo_trace_rom u_trace_rom (
        .addr (trace_index),
        .data (rom_data)
    );

    wire signed [15:0] trace_x16 = rom_data[31:16];
    wire signed [15:0] trace_y16 = rom_data[15:0];
    wire signed [31:0] px = {{16{trace_x16[15]}}, trace_x16};
    wire signed [31:0] py = {{16{trace_y16[15]}}, trace_y16};

    wire [63:0] dist2;

    road_geom u_road_geom (
        .clk     (clk),
        .rst     (rst),
        .px      (px),
        .py      (py),
        .ax      (-32'sd2000),
        .ay      (32'sd0),
        .bx      (32'sd2000),
        .by      (32'sd0),
        .ux_q14  (16'sd16384),
        .uy_q14  (16'sd0),
        .dist2   (dist2),
        .inside_span ()
    );

    reg [63:0] prev_dist2;
    wire approaching = (dist2 < prev_dist2);

    always @(posedge clk) begin
        if (rst)
            prev_dist2 <= 64'hFFFFFFFFFFFFFFFF;
        else if (sample_tick)
            prev_dist2 <= dist2;
    end

    reg [31:0] ms_cnt;
    reg [31:0] stale_cnt;
    reg        stale;
    reg        sample_seen;
    wire       ms_tick = (ms_cnt >= (CLK_PER_MS - 1));

    always @(posedge clk) begin
        if (rst) begin
            ms_cnt      <= 32'd0;
            stale_cnt   <= 32'd0;
            stale       <= 1'b1;
            sample_seen <= 1'b0;
        end else begin
            if (ms_tick)
                ms_cnt <= 32'd0;
            else
                ms_cnt <= ms_cnt + 32'd1;

            if (sample_tick)
                sample_seen <= 1'b1;

            if (ms_tick) begin
                if (sample_seen) begin
                    sample_seen <= 1'b0;
                    stale_cnt   <= 32'd0;
                    stale       <= 1'b0;
                end else if (stale_cnt >= (STALE_MS - 1)) begin
                    stale <= 1'b1;
                end else begin
                    stale_cnt <= stale_cnt + 32'd1;
                end
            end
        end
    end

    wire stale_now = stale | force_stale | ~map_valid;

    wire [2:0] risk_state;
    wire       cue_req;
    wire       fault;
    wire       cue_en;
    wire       cooldown;

    risk_fsm u_risk_fsm (
        .clk          (clk),
        .rst          (rst),
        .sample_valid (sample_tick),
        .stale        (stale_now),
        .map_valid    (map_valid),
        .cooldown     (cooldown),
        .approaching  (approaching),
        .dist2        (dist2),
        .state        (risk_state),
        .cue_req      (cue_req),
        .fault        (fault)
    );

    cue_scheduler #(
        .MAX_ON_TICKS   (MAX_ON_TICKS),
        .COOLDOWN_TICKS (COOLDOWN_TICKS)
    ) u_cue_scheduler (
        .clk      (clk),
        .rst      (rst),
        .tick     (sample_tick),
        .enable   (cue_enable),
        .request  (cue_req),
        .cue_en   (cue_en),
        .cooldown (cooldown)
    );

    wire cue_active = cue_en & cue_enable & ~stale_now & map_valid;

    reg [31:0] hb_cnt;
    reg        heartbeat;

    always @(posedge clk) begin
        if (rst) begin
            hb_cnt    <= 32'd0;
            heartbeat <= 1'b0;
        end else if (hb_cnt >= (HEARTBEAT_DIV - 1)) begin
            hb_cnt    <= 32'd0;
            heartbeat <= ~heartbeat;
        end else begin
            hb_cnt <= hb_cnt + 32'd1;
        end
    end

    assign cue_out = cue_active;

    assign led[2:0]  = stale_now ? ST_INVALID : risk_state;
    assign led[3]    = ~stale_now;
    assign led[4]    = approaching & ~stale_now;
    assign led[5]    = cue_active;
    assign led[6]    = cooldown;
    assign led[7]    = fault;
    assign led[8]    = ~stale_now & (dist2 <= DIST_1M2);
    assign led[9]    = ~stale_now & (dist2 <= DIST_2M2);
    assign led[10]   = ~stale_now & (dist2 <= DIST_3M2);
    assign led[11]   = ~stale_now & (dist2 <= DIST_4M2);
    assign led[12]   = ~stale_now & (dist2 <= DIST_5M2);
    assign led[13]   = ~stale_now & (dist2 <= DIST_7M2);
    assign led[14]   = ~stale_now & (dist2 <= DIST_10M2);
    assign led[15]   = heartbeat;

endmodule
