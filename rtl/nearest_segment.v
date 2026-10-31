// nearest_segment — sequential scanner over road segment ROM to find
// the closest road segment to animal position (px, py).
//
// Sequentially feeds segments from road_seg_rom through road_geom.
// Compares squared distances and registers the minimum.
//
// Latency: ~(SEG_COUNT * 14) clk cycles. At 100 MHz for 16 segments, ~2.3 us.
// Completion signaled by single-cycle `done` pulse.

module nearest_segment #(
    parameter integer SEG_COUNT = 7
) (
    input  wire               clk,
    input  wire               rst,
    input  wire               start,
    input  wire signed [31:0] px,
    input  wire signed [31:0] py,

    // ROM read port
    output reg  [15:0]        rom_addr,
    input  wire [31:0]        rom_data,

    // Results
    output reg  [63:0]        min_dist2,
    output reg  [7:0]         nearest_seg_id,
    output reg                inside_span,
    output reg                done,
    output reg                busy
);

    // FSM States
    localparam S_IDLE       = 3'd0;
    localparam S_FETCH      = 3'd1;
    localparam S_WAIT_GEOM  = 3'd2;
    localparam S_CHECK      = 3'd3;
    localparam S_DONE       = 3'd4;

    reg [2:0]  state;
    reg [7:0]  curr_seg;
    reg [2:0]  word_idx;
    reg [3:0]  geom_wait_cnt;

    // Segment buffer
    reg signed [31:0] ax, ay, bx, by;
    reg signed [15:0] ux_q14, uy_q14;
    reg [7:0]         rclass;

    // road_geom instance
    wire [63:0] geom_dist2;
    wire        geom_inside;

    road_geom u_geom (
        .clk         (clk),
        .rst         (rst),
        .px          (px),
        .py          (py),
        .ax          (ax),
        .ay          (ay),
        .bx          (bx),
        .by          (by),
        .ux_q14      (ux_q14),
        .uy_q14      (uy_q14),
        .dist2       (geom_dist2),
        .inside_span (geom_inside)
    );

    always @(posedge clk) begin
        if (rst) begin
            state          <= S_IDLE;
            curr_seg       <= 8'd0;
            word_idx       <= 3'd0;
            geom_wait_cnt  <= 4'd0;
            min_dist2      <= 64'hFFFFFFFFFFFFFFFF;
            nearest_seg_id <= 8'd0;
            inside_span    <= 1'b0;
            done           <= 1'b0;
            busy           <= 1'b0;
            rom_addr       <= 16'd0;
            ax <= 32'sd0; ay <= 32'sd0; bx <= 32'sd0; by <= 32'sd0;
            ux_q14 <= 16'sd0; uy_q14 <= 16'sd0; rclass <= 8'd0;
        end else begin
            done <= 1'b0;

            case (state)
                S_IDLE: begin
                    busy <= 1'b0;
                    if (start) begin
                        busy           <= 1'b1;
                        curr_seg       <= 8'd0;
                        word_idx       <= 3'd0;
                        min_dist2      <= 64'hFFFFFFFFFFFFFFFF;
                        nearest_seg_id <= 8'd0;
                        inside_span    <= 1'b0;
                        rom_addr       <= 16'd0; // first word of seg 0
                        state          <= S_FETCH;
                    end
                end

                S_FETCH: begin
                    case (word_idx)
                        3'd0: begin
                            ax       <= $signed(rom_data);
                            rom_addr <= curr_seg * 16'd6 + 16'd1;
                            word_idx <= 3'd1;
                        end
                        3'd1: begin
                            ay       <= $signed(rom_data);
                            rom_addr <= curr_seg * 16'd6 + 16'd2;
                            word_idx <= 3'd2;
                        end
                        3'd2: begin
                            bx       <= $signed(rom_data);
                            rom_addr <= curr_seg * 16'd6 + 16'd3;
                            word_idx <= 3'd3;
                        end
                        3'd3: begin
                            by       <= $signed(rom_data);
                            rom_addr <= curr_seg * 16'd6 + 16'd4;
                            word_idx <= 3'd4;
                        end
                        3'd4: begin
                            ux_q14   <= $signed(rom_data[31:16]);
                            uy_q14   <= $signed(rom_data[15:0]);
                            rom_addr <= curr_seg * 16'd6 + 16'd5;
                            word_idx <= 3'd5;
                        end
                        3'd5: begin
                            rclass        <= rom_data[7:0];
                            geom_wait_cnt <= 4'd0;
                            state         <= S_WAIT_GEOM;
                        end
                        default: state <= S_IDLE;
                    endcase
                end

                S_WAIT_GEOM: begin
                    // road_geom pipeline is 7 cycles
                    if (geom_wait_cnt >= 4'd7) begin
                        state <= S_CHECK;
                    end else begin
                        geom_wait_cnt <= geom_wait_cnt + 4'd1;
                    end
                end

                S_CHECK: begin
                    if (geom_dist2 < min_dist2) begin
                        min_dist2      <= geom_dist2;
                        nearest_seg_id <= curr_seg;
                        inside_span    <= geom_inside;
                    end

                    if (curr_seg + 1 < SEG_COUNT) begin
                        curr_seg <= curr_seg + 8'd1;
                        word_idx <= 3'd0;
                        rom_addr <= (curr_seg + 8'd1) * 16'd6;
                        state    <= S_FETCH;
                    end else begin
                        state <= S_DONE;
                    end
                end

                S_DONE: begin
                    done <= 1'b1;
                    busy <= 1'b0;
                    state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
