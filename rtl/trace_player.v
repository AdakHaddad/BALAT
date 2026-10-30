// trace_player — advances a compiled trace ROM at a fixed sample rate.
//
// tick is a one-cycle pulse at the sample rate while run is high. index holds
// the current trace address and wraps at LAST_INDEX. The consumer should sample
// the ROM data on the tick that corresponds to the current index; index then
// advances for the next period.
module trace_player #(
    parameter integer CLK_PER_TICK = 10_000_000, // 100 ms at 100 MHz
    parameter integer LAST_INDEX   = 200
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        run,
    output reg         tick,
    output reg  [15:0] index
);

    localparam [15:0] LAST = LAST_INDEX[15:0];

    reg [31:0] div_cnt;

    always @(posedge clk) begin
        if (rst) begin
            div_cnt <= 32'd0;
            tick    <= 1'b0;
            index   <= 16'd0;
        end else begin
            tick <= 1'b0;
            if (!run) begin
                div_cnt <= 32'd0;
            end else if (div_cnt == (CLK_PER_TICK - 1)) begin
                div_cnt <= 32'd0;
                tick    <= 1'b1;
                if (index == LAST)
                    index <= 16'd0;
                else
                    index <= index + 16'd1;
            end else begin
                div_cnt <= div_cnt + 32'd1;
            end
        end
    end

endmodule
