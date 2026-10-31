// uart_tx — 8N1 UART transmitter.
//
// send is a one-cycle request; data is captured on that cycle. busy is high
// while the start, data, and stop bits are being shifted. tx idles high.
// CLKS_PER_BIT is rounded from CLK_HZ/BAUD, so keep the baud error small.
module uart_tx #(
    parameter integer CLK_HZ = 100_000_000,
    parameter integer BAUD   = 115200
) (
    input  wire       clk,
    input  wire       rst,
    input  wire       send,
    input  wire [7:0] data,
    output reg        tx,
    output reg        busy
);

    localparam integer CLKS_PER_BIT = (CLK_HZ + (BAUD / 2)) / BAUD;

    localparam [1:0] ST_IDLE  = 2'd0;
    localparam [1:0] ST_START = 2'd1;
    localparam [1:0] ST_DATA  = 2'd2;
    localparam [1:0] ST_STOP  = 2'd3;

    reg [1:0]  state;
    reg [31:0] clk_count;
    reg [2:0]  bit_index;
    reg [7:0]  shift;

    always @(posedge clk) begin
        if (rst) begin
            tx        <= 1'b1;
            busy      <= 1'b0;
            state     <= ST_IDLE;
            clk_count <= 32'd0;
            bit_index <= 3'd0;
            shift     <= 8'd0;
        end else begin
            case (state)
                ST_IDLE: begin
                    tx <= 1'b1;
                    if (send) begin
                        shift     <= data;
                        busy      <= 1'b1;
                        clk_count <= 32'd0;
                        bit_index <= 3'd0;
                        state     <= ST_START;
                    end else begin
                        busy <= 1'b0;
                    end
                end

                ST_START: begin
                    tx <= 1'b0;
                    if (clk_count == (CLKS_PER_BIT - 1)) begin
                        clk_count <= 32'd0;
                        bit_index <= 3'd0;
                        state     <= ST_DATA;
                    end else begin
                        clk_count <= clk_count + 32'd1;
                    end
                end

                ST_DATA: begin
                    tx <= shift[0];
                    if (clk_count == (CLKS_PER_BIT - 1)) begin
                        clk_count <= 32'd0;
                        if (bit_index == 3'd7) begin
                            tx    <= 1'b1;
                            state <= ST_STOP;
                        end else begin
                            bit_index <= bit_index + 3'd1;
                            shift     <= {1'b0, shift[7:1]};
                        end
                    end else begin
                        clk_count <= clk_count + 32'd1;
                    end
                end

                ST_STOP: begin
                    tx <= 1'b1;
                    if (clk_count == (CLKS_PER_BIT - 1)) begin
                        clk_count <= 32'd0;
                        busy      <= 1'b0;
                        state     <= ST_IDLE;
                    end else begin
                        clk_count <= clk_count + 32'd1;
                    end
                end

                default: begin
                    tx    <= 1'b1;
                    busy  <= 1'b0;
                    state <= ST_IDLE;
                end
            endcase
        end
    end

endmodule
