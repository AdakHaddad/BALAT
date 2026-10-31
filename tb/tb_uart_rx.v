`timescale 1ns/1ps

module tb_uart_rx;

    localparam integer CLKS_PER_BIT = 10;

    reg       clk;
    reg       rst;
    reg       rx;
    wire [7:0] data;
    wire       valid;
    wire       error;

    reg [7:0] captured;
    reg       captured_valid;
    reg       captured_error;

    uart_rx #(
        .CLK_HZ (100),
        .BAUD   (10)
    ) dut (
        .clk   (clk),
        .rst   (rst),
        .rx    (rx),
        .data  (data),
        .valid (valid),
        .error (error)
    );

    always #5 clk = ~clk;

    always @(posedge clk) begin
        if (valid) begin
            captured       <= data;
            captured_valid <= 1'b1;
        end
        if (error)
            captured_error <= 1'b1;
    end

    task drive_byte(input [7:0] value, input stop_bit);
        integer i;
        begin
            @(negedge clk);
            rx = 1'b0;
            repeat (CLKS_PER_BIT) @(negedge clk);
            for (i = 0; i < 8; i = i + 1) begin
                rx = value[i];
                repeat (CLKS_PER_BIT) @(negedge clk);
            end
            rx = stop_bit;
            repeat (CLKS_PER_BIT) @(negedge clk);
        end
    endtask

    initial begin
        $dumpfile("build/sim/tb_uart_rx.vcd");
        $dumpvars(0, tb_uart_rx);

        clk = 0;
        rst = 1;
        rx = 1;
        captured = 0;
        captured_valid = 0;
        captured_error = 0;

        repeat (3) @(negedge clk);
        rst = 0;
        repeat (5) @(negedge clk);

        drive_byte(8'h5A, 1'b1);
        repeat (3) @(negedge clk);
        if (!captured_valid || (captured !== 8'h5A)) begin
            $display("FAIL: expected 0x5A, got valid=%0d data=%02x", captured_valid, captured);
            $fatal;
        end

        captured_valid = 0;
        drive_byte(8'hC3, 1'b1);
        repeat (3) @(negedge clk);
        if (!captured_valid || (captured !== 8'hC3)) begin
            $display("FAIL: expected 0xC3, got valid=%0d data=%02x", captured_valid, captured);
            $fatal;
        end

        captured_valid = 0;
        captured_error = 0;
        drive_byte(8'h77, 1'b0);
        repeat (3) @(negedge clk);
        if (!captured_error) begin
            $display("FAIL: low stop bit must set error");
            $fatal;
        end
        if (captured_valid) begin
            $display("FAIL: framing error must not assert valid");
            $fatal;
        end

        $display("PASS: uart_rx");
        $finish;
    end

endmodule
