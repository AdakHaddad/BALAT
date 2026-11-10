// BALAT Basys 3 dashboard driven NMEA demo.
// UART RX consumes raw checksummed NMEA from the dashboard at 115200 8N1.
// The existing HerdSync bridge returns FPGA position/risk frames on UART TX.
// SW2 enables the logic-level cue observation output; SW1 forces invalid;
// SW3 forces map invalid. BTNC is active-high reset. JA1 is not an actuator pin.
//
// Map: Sumbawa Besar road network, West Nusa Tenggara, Indonesia.
//   Origin: lat -8.490 deg, lon 117.420 deg (ORIGIN_LAT_DEG7=-84900000, ORIGIN_LON_DEG7=1174200000)
//   99 road segments from road_seg_rom.v. nearest_segment scans all segments
//   each time a valid GNSS fix arrives and feeds the closest one to risk_fsm.
//   Map data: © OpenStreetMap contributors (ODbL) — see data/road_manifest.json
//
// Pipeline: UART RX → nmea_parser → coord_convert → nearest_segment (99 segs)
//           → risk_fsm → cue_scheduler → herdsync_uart_bridge
module balat_basys3_dashboard_top #(
    parameter integer CLK_PER_MS = 100_000,
    parameter integer DEMO_TICK_INTERVAL_MS = 100,
    parameter integer STALE_MS = 500,
    parameter integer MAX_ON_TICKS = 5,
    parameter integer COOLDOWN_TICKS = 30,
    parameter integer HEARTBEAT_DIV = 50_000_000,
    parameter integer UART_CLK_HZ = 100_000_000,
    parameter integer UART_BAUD = 115200,
    // Sumbawa Besar origin (see coord_convert.v)
    parameter integer SEG_COUNT = 99
) (
    input wire clk,
    input wire btnC,
    input wire [3:0] sw,
    input wire RsRx,
    output wire [15:0] led,
    output wire cue_out,
    output wire RsTx
);
    localparam [2:0] ST_INVALID = 3'd0;
    (* ASYNC_REG = "TRUE" *) reg [2:0] rst_sync;
    wire rst = rst_sync[2];
    always @(posedge clk or posedge btnC) begin
        if (btnC) rst_sync <= 3'b111;
        else rst_sync <= {rst_sync[1:0], 1'b0};
    end

    wire [7:0] rx_data;
    wire rx_valid, rx_error;
    uart_rx #(.CLK_HZ(UART_CLK_HZ), .BAUD(UART_BAUD)) u_rx (
        .clk(clk), .rst(rst), .rx(RsRx), .data(rx_data), .valid(rx_valid), .error(rx_error)
    );

    wire signed [31:0] lat_deg7, lon_deg7;
    wire [15:0] speed_kn;
    wire [23:0] utc_time;
    wire fix_valid, fix_ready;
    nmea_parser u_parser (
        .clk(clk), .rst(rst), .rx_data(rx_data), .rx_valid(rx_valid),
        .lat_deg7(lat_deg7), .lon_deg7(lon_deg7), .speed_kn(speed_kn),
        .utc_time(utc_time), .fix_valid(fix_valid), .fix_ready(fix_ready)
    );

    wire signed [31:0] px, py;
    wire pos_valid, pos_ready;
    coord_convert u_coord (
        .clk(clk), .rst(rst), .lat_deg7(lat_deg7), .lon_deg7(lon_deg7),
        .fix_valid(fix_valid), .fix_ready(fix_ready), .px(px), .py(py),
        .pos_valid(pos_valid), .pos_ready(pos_ready)
    );

    // Align the sample event with the seven-cycle road_geom result. This also
    // leaves two cycles for coordinate conversion and geometry input capture.
    reg [9:0] sample_pipe;
    always @(posedge clk) begin
        if (rst) sample_pipe <= 10'd0;
        else sample_pipe <= {sample_pipe[8:0], pos_ready};
    end
    wire sample_tick = sample_pipe[9];

    // nearest_segment scans all SEG_COUNT road segments from road_seg_rom on
    // every valid position update and reports the closest one.
    // Start a new scan on each pos_ready pulse; latency ~(SEG_COUNT * 14) cycles.
    wire [15:0] rom_addr;
    wire [31:0] rom_data;
    wire [63:0] dist2;
    wire        ns_inside_span;
    wire        ns_done;
    wire        ns_busy;

    road_seg_rom #(.SEG_COUNT(SEG_COUNT)) u_seg_rom (
        .addr (rom_addr),
        .data (rom_data)
    );

    nearest_segment #(.SEG_COUNT(SEG_COUNT)) u_nearest (
        .clk            (clk),
        .rst            (rst),
        .start          (pos_ready),
        .px             (px),
        .py             (py),
        .rom_addr       (rom_addr),
        .rom_data       (rom_data),
        .min_dist2      (dist2),
        .nearest_seg_id (),
        .inside_span    (ns_inside_span),
        .done           (ns_done),
        .busy           (ns_busy)
    );

    // sample_tick fires when nearest_segment completes; this guarantees dist2
    // is stable and valid before risk_fsm samples it.
    wire sample_tick = ns_done;

    reg [63:0] prev_dist2;
    wire approaching = dist2 < prev_dist2;
    always @(posedge clk) begin
        if (rst) prev_dist2 <= 64'hFFFFFFFFFFFFFFFF;
        else if (sample_tick) prev_dist2 <= dist2;
    end

    reg [31:0] ms_count, stale_count;
    reg stale;
    wire ms_tick = ms_count >= (CLK_PER_MS - 1);
    always @(posedge clk) begin
        if (rst) begin
            ms_count <= 0; stale_count <= 0; stale <= 1'b1;
        end else begin
            if (ms_tick) ms_count <= 0; else ms_count <= ms_count + 1'b1;
            if (pos_ready && pos_valid) begin stale_count <= 0; stale <= 1'b0; end
            else if (ms_tick) begin
                if (stale_count >= (STALE_MS - 1)) stale <= 1'b1;
                else stale_count <= stale_count + 1'b1;
            end
        end
    end

    // Fixed 10 Hz tick keeps cue duration/cooldown in demo time even when the
    // dashboard changes the GPS replay interval.
    reg [15:0] demo_ms_count;
    reg demo_tick;
    always @(posedge clk) begin
        if (rst) begin demo_ms_count <= 0; demo_tick <= 0; end
        else begin
            demo_tick <= 0;
            if (ms_tick) begin
                if (demo_ms_count >= (DEMO_TICK_INTERVAL_MS - 1)) begin
                    demo_ms_count <= 0;
                    demo_tick <= 1;
                end else demo_ms_count <= demo_ms_count + 1'b1;
            end
        end
    end
    wire map_valid = ~sw[3];
    // The most recently parsed RMC status must remain active as a validity
    // gate; a void RMC forces INVALID immediately, independent of the timer.
    wire stale_now = stale | ~pos_valid | sw[1] | ~map_valid;
    wire [2:0] risk_state;
    wire cue_req, fault, cue_en, cooldown;
    risk_fsm u_risk (
        .clk(clk), .rst(rst), .sample_valid(sample_tick), .stale(stale_now),
        .map_valid(map_valid), .cooldown(cooldown), .approaching(approaching),
        .dist2(dist2), .state(risk_state), .cue_req(cue_req), .fault(fault)
    );
    cue_scheduler #(.MAX_ON_TICKS(MAX_ON_TICKS), .COOLDOWN_TICKS(COOLDOWN_TICKS)) u_cue (
        .clk(clk), .rst(rst), .tick(demo_tick), .enable(sw[2]), .request(cue_req),
        .cue_en(cue_en), .cooldown(cooldown)
    );
    wire [2:0] display_state = stale_now ? ST_INVALID : risk_state;
    wire cue_active = cue_en & sw[2] & ~stale_now & map_valid;

    // Match the existing bridge record format so the dashboard can consume
    // FPGA coordinates and state at 10 Hz, including INVALID after the local
    // stale watchdog expires even when dashboard replay is paused.
    reg signed [31:0] record_x, record_y;
    always @(posedge clk) begin
        if (rst) begin
            record_x <= 0; record_y <= 0;
        end
        else begin
            if (pos_ready) begin record_x <= px; record_y <= py; end
        end
    end
    wire [15:0] sent, received, crc_errors, tx_drops, rx_errors;
    wire [31:0] peer_id, peer_seq, peer_fix_s;
    wire [2:0] peer_risk;
    wire peer_seen, tx_busy;
    herdsync_uart_bridge #(.CLK_HZ(UART_CLK_HZ), .BAUD(UART_BAUD), .ORIGIN_ID(32'd1), .EPOCH(16'd1)) u_bridge (
        .clk(clk), .rst(rst), .sample_tick(demo_tick), .sample_valid(pos_valid & ~stale_now),
        .stale(stale_now), .risk(display_state), .x_cm(record_x), .y_cm(record_y),
        .uart_rx(RsRx), .uart_tx(RsTx), .tx_busy(tx_busy), .frames_sent(sent),
        .frames_received(received), .crc_errors(crc_errors), .tx_drops(tx_drops),
        .rx_errors(rx_errors), .last_peer_id(peer_id), .last_peer_seq(peer_seq),
        .last_peer_fix_s(peer_fix_s), .last_peer_risk(peer_risk), .peer_seen(peer_seen)
    );

    reg [31:0] hb_count;
    reg heartbeat;
    always @(posedge clk) begin
        if (rst) begin hb_count <= 0; heartbeat <= 0; end
        else if (hb_count >= (HEARTBEAT_DIV - 1)) begin hb_count <= 0; heartbeat <= ~heartbeat; end
        else hb_count <= hb_count + 1'b1;
    end
    assign cue_out = cue_active;
    assign led[2:0] = display_state;
    assign led[3] = pos_valid & ~stale_now;
    assign led[4] = approaching & ~stale_now;
    assign led[5] = cue_active;
    assign led[6] = sent[0];
    assign led[7] = fault | rx_error;
    assign led[15:8] = {8{heartbeat}};
endmodule
