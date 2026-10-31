// uart_rx — 8N1 UART receiver with a two-flop input synchronizer.
//
// rx is asynchronous to clk. The synchronizer and mid-bit sampling recover
// data; valid is a one-cycle pulse. error pulses when the stop bit is low.
// This module does not implement a FIFO or baud-rate detection.
module uart_rx #(
    parameter integer CLK_HZ = 100_000_000,
    parameter integer BAUD   = 115200
) (
    input  wire       clk,
    input  wire       rst,
    input  wire       rx,
    output reg  [7:0] data,
    output reg        valid,
    output reg        error
);

    localparam integer CLKS_PER_BIT = (CLK_HZ + (BAUD / 2)) / BAUD;
    localparam integer HALF_BIT     = (CLKS_PER_BIT > 1) ? (CLKS_PER_BIT / 2) : 1;

    localparam [2:0] ST_IDLE  = 3'd0;
    localparam [2:0] ST_START = 3'd1;
    localparam [2:0] ST_DATA  = 3'd2;
    localparam [2:0] ST_STOP  = 3'd3;

    (* ASYNC_REG = "TRUE" *) reg [1:0] rx_sync;
    reg        rx_prev;
    reg [2:0]  state;
    reg [31:0] clk_count;
    reg [2:0]  bit_index;
    reg [7:0]  shift;

    always @(posedge clk) begin
        if (rst) begin
            rx_sync   <= 2'b11;
            rx_prev   <= 1'b1;
            state     <= ST_IDLE;
            clk_count <= 32'd0;
            bit_index <= 3'd0;
            shift     <= 8'd0;
            data      <= 8'd0;
            valid     <= 1'b0;
            error     <= 1'b0;
        end else begin
            rx_sync <= {rx_sync[0], rx};
            rx_prev <= rx_sync[1];
            valid   <= 1'b0;
            error   <= 1'b0;

            case (state)
                ST_IDLE: begin
                    if (!rx_sync[1] && rx_prev) begin
                        clk_count <= 32'd0;
                        state     <= ST_START;
                    end
                end

                ST_START: begin
                    if (clk_count == (HALF_BIT - 1)) begin
                        clk_count <= 32'd0;
                        if (!rx_sync[1]) begin
                            bit_index <= 3'd0;
                            state     <= ST_DATA;
                        end else begin
                            state <= ST_IDLE;
                        end
                    end else begin
                        clk_count <= clk_count + 32'd1;
                    end
                end

                ST_DATA: begin
                    if (clk_count == (CLKS_PER_BIT - 1)) begin
                        clk_count <= 32'd0;
                        shift     <= {rx_sync[1], shift[7:1]};
                        if (bit_index == 3'd7) begin
                            state <= ST_STOP;
                        end else begin
                            bit_index <= bit_index + 3'd1;
                        end
                    end else begin
                        clk_count <= clk_count + 32'd1;
                    end
                end

                ST_STOP: begin
                    if (clk_count == (CLKS_PER_BIT - 1)) begin
                        clk_count <= 32'd0;
                        if (rx_sync[1]) begin
                            data  <= shift;
                            valid <= 1'b1;
                        end else begin
                            error <= 1'b1;
                        end
                        state <= ST_IDLE;
                    end else begin
                        clk_count <= clk_count + 32'd1;
                    end
                end

                default: begin
                    state <= ST_IDLE;
                end
            endcase
        end
    end

endmodule
