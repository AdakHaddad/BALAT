`timescale 1ns/1ps

module tb_cue_scheduler;

    reg clk;
    reg rst;
    reg tick;
    reg enable;
    reg request;
    wire cue_en;
    wire cooldown;

    cue_scheduler #(
        .MAX_ON_TICKS (3),
        .COOLDOWN_TICKS (5)
    ) dut (
        .clk (clk),
        .rst (rst),
        .tick (tick),
        .enable (enable),
        .request (request),
        .cue_en (cue_en),
        .cooldown (cooldown)
    );

    always #5 clk = ~clk;

    task tick_once;
        begin
            @(negedge clk);
            tick = 1'b1;
            @(negedge clk);
            tick = 1'b0;
        end
    endtask

    task expect_cue(input expected);
        begin
            if (cue_en !== expected) begin
                $display("FAIL: expected cue_en=%0d, got %0d at time %0t", expected, cue_en, $time);
                $fatal;
            end
        end
    endtask

    task expect_cooldown(input expected);
        begin
            if (cooldown !== expected) begin
                $display("FAIL: expected cooldown=%0d, got %0d at time %0t", expected, cooldown, $time);
                $fatal;
            end
        end
    endtask

    initial begin
        clk = 0;
        rst = 1;
        tick = 0;
        enable = 1;
        request = 0;

        repeat (3) @(negedge clk);
        rst = 0;
        @(negedge clk);
        expect_cue(1'b0);
        expect_cooldown(1'b0);

        tick_once();
        expect_cue(1'b0);

        request = 1'b1;
        tick_once();
        expect_cue(1'b1);

        tick_once();
        expect_cue(1'b1);
        tick_once();
        expect_cue(1'b1);
        tick_once();
        expect_cue(1'b0);
        expect_cooldown(1'b1);

        repeat (4) tick_once();
        expect_cue(1'b0);
        expect_cooldown(1'b1);

        tick_once();
        expect_cooldown(1'b0);

        tick_once();
        expect_cue(1'b1);

        enable = 1'b0;
        tick_once();
        expect_cue(1'b0);
        expect_cooldown(1'b0);

        enable = 1'b1;
        request = 1'b1;
        tick_once();
        expect_cue(1'b1);

        rst = 1'b1;
        @(negedge clk);
        expect_cue(1'b0);
        expect_cooldown(1'b0);

        $display("PASS: cue_scheduler");
        $finish;
    end

endmodule
