`timescale 1ns/1ps

module tb_trace_player;

    reg clk;
    reg rst;
    reg run;
    wire tick;
    wire [15:0] index;

    trace_player #(
        .CLK_PER_TICK (4),
        .LAST_INDEX (3)
    ) dut (
        .clk (clk),
        .rst (rst),
        .run (run),
        .tick (tick),
        .index (index)
    );

    always #5 clk = ~clk;

    task wait_tick;
        integer n;
        begin
            while (tick)
                @(posedge clk);
            n = 0;
            while (!tick && (n < 20)) begin
                @(posedge clk);
                n = n + 1;
            end
            if (!tick) begin
                $display("FAIL: timeout waiting for tick");
                $fatal;
            end
        end
    endtask

    initial begin
        clk = 0;
        rst = 1;
        run = 0;

        repeat (3) @(negedge clk);
        rst = 0;
        repeat (10) @(negedge clk);
        if (tick !== 1'b0 || index !== 16'd0) begin
            $display("FAIL: paused player must not tick");
            $fatal;
        end

        run = 1;
        wait_tick();
        if (index !== 16'd1) begin
            $display("FAIL: after tick 1 expected index 1, got %0d", index);
            $fatal;
        end

        wait_tick();
        if (index !== 16'd2) begin
            $display("FAIL: after tick 2 expected index 2, got %0d", index);
            $fatal;
        end

        wait_tick();
        if (index !== 16'd3) begin
            $display("FAIL: after tick 3 expected index 3, got %0d", index);
            $fatal;
        end

        wait_tick();
        if (index !== 16'd0) begin
            $display("FAIL: after tick 4 expected wrap to 0, got %0d", index);
            $fatal;
        end

        run = 0;
        repeat (20) @(negedge clk);
        if (tick !== 1'b0 || index !== 16'd0) begin
            $display("FAIL: pause must hold index and stop ticks");
            $fatal;
        end

        $display("PASS: trace_player");
        $finish;
    end

endmodule
