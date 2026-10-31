`timescale 1ns/1ps

module tb_uart_tx;

    localparam integer CLKS_PER_BIT = 10;

    reg       clk;
    reg       rst;
    reg       send;
    reg [7:0] data;
    wire      tx;
    wire      busy;

    uart_tx #(
        .CLK_HZ (100),
        .BAUD   (10)
    ) dut (
        .clk  (clk),
        .rst  (rst),
        .send (send),
        .data (data),
        .tx   (tx),
        .busy (busy)
    );

    always #5 clk = ~clk;

    task send_byte(input [7:0] value);
        begin
            @(negedge clk);
            data = value;
            send = 1'b1;
            @(negedge clk);
            send = 1'b0;
        end
    endtask

    task expect_byte(input [7:0] value);
        integer i;
        begin
            @(negedge tx);
            repeat (CLKS_PER_BIT / 2) @(posedge clk);
            if (tx !== 1'b0) begin
                $display("FAIL: start bit not low at time %0t", $time);
                $fatal;
            end
            for (i = 0; i < 8; i = i + 1) begin
                repeat (CLKS_PER_BIT) @(posedge clk);
                if (tx !== value[i]) begin
                    $display("FAIL: bit %0d expected %0d got %0d at time %0t",
                             i, value[i], tx, $time);
                    $fatal;
                end
            end
            repeat (CLKS_PER_BIT) @(posedge clk);
            if (tx !== 1'b1) begin
                $display("FAIL: stop bit not high at time %0t", $time);
                $fatal;
            end
        end
    endtask

    initial begin
        $dumpfile("build/sim/tb_uart_tx.vcd");
        $dumpvars(0, tb_uart_tx);

        clk = 0;
        rst = 1;
        send = 0;
        data = 0;

        repeat (3) @(negedge clk);
        rst = 0;
        repeat (2) @(negedge clk);
        if (tx !== 1'b1) begin
            $display("FAIL: tx must idle high");
            $fatal;
        end

        send_byte(8'hA5);
        expect_byte(8'hA5);
        while (busy) @(posedge clk);

        send_byte(8'h00);
        expect_byte(8'h00);
        while (busy) @(posedge clk);

        send_byte(8'hFF);
        expect_byte(8'hFF);
        while (busy) @(posedge clk);

        if (tx !== 1'b1) begin
            $display("FAIL: tx must return high");
            $fatal;
        end

        rst = 1;
        @(negedge clk);
        if ((tx !== 1'b1) || (busy !== 1'b0)) begin
            $display("FAIL: reset must force tx high and busy low");
            $fatal;
        end

        $display("PASS: uart_tx");
        $finish;
    end

endmodule
