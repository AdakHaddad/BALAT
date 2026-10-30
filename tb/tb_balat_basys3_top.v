`timescale 1ns/1ps

module tb_balat_basys3_top;

    localparam [2:0] ST_INVALID = 3'd0;
    localparam [2:0] ST_SAFE    = 3'd1;
    localparam [2:0] ST_CAUTION = 3'd2;
    localparam [2:0] ST_DANGER  = 3'd3;

    reg         clk;
    reg         btnC;
    reg  [3:0]  sw;
    wire [15:0] led;
    wire        cue_out;

    balat_basys3_top #(
        .CLK_PER_TICK   (20),
        .LAST_INDEX     (200),
        .CLK_PER_MS     (1),
        .STALE_MS       (50),
        .MAX_ON_TICKS   (3),
        .COOLDOWN_TICKS (5),
        .HEARTBEAT_DIV  (10)
    ) dut (
        .clk (clk),
        .btnC (btnC),
        .sw (sw),
        .led (led),
        .cue_out (cue_out)
    );

    always #5 clk = ~clk;

    task wait_for_state(input [2:0] target, input integer max_cycles);
        integer n;
        begin
            n = 0;
            while ((dut.risk_state !== target) && (n < max_cycles)) begin
                @(posedge clk);
                n = n + 1;
            end
            if (dut.risk_state !== target) begin
                $display("FAIL: timeout waiting for state %0d, got %0d at time %0t",
                         target, dut.risk_state, $time);
                $fatal;
            end
        end
    endtask

    task wait_for_cue(input integer max_cycles);
        integer n;
        begin
            n = 0;
            while (!dut.cue_active && (n < max_cycles)) begin
                @(posedge clk);
                n = n + 1;
            end
            if (!dut.cue_active) begin
                $display("FAIL: timeout waiting for cue at time %0t", $time);
                $fatal;
            end
        end
    endtask

    task wait_for_cooldown(input integer max_cycles);
        integer n;
        begin
            n = 0;
            while (!dut.cooldown && (n < max_cycles)) begin
                @(posedge clk);
                n = n + 1;
            end
            if (!dut.cooldown) begin
                $display("FAIL: timeout waiting for cooldown at time %0t", $time);
                $fatal;
            end
        end
    endtask

    initial begin
        $dumpfile("build/sim/tb_balat_basys3_top.vcd");
        $dumpvars(0, tb_balat_basys3_top);

        clk = 0;
        btnC = 1;
        sw = 4'b0000;

        repeat (5) @(negedge clk);
        btnC = 0;
        sw = 4'b0101; // run + cue enable

        wait_for_state(ST_SAFE, 500);
        if (led[3] !== 1'b1) begin
            $display("FAIL: SAFE with fresh input must show valid");
            $fatal;
        end

        wait_for_state(ST_CAUTION, 3000);
        wait_for_state(ST_DANGER, 3000);
        wait_for_cue(500);

        if ((led[5] !== 1'b1) || (cue_out !== 1'b1)) begin
            $display("FAIL: cue LED and cue_out must assert together");
            $fatal;
        end

        wait_for_cooldown(500);
        wait_for_state(ST_SAFE, 1000);

        sw[1] = 1'b1;
        wait_for_state(ST_INVALID, 5);
        if ((cue_out !== 1'b0) || (led[7] !== 1'b1)) begin
            $display("FAIL: stale input must force INVALID and drop the cue");
            $fatal;
        end

        sw[1] = 1'b0;
        wait_for_state(ST_SAFE, 200);

        sw[2] = 1'b0;
        #20;
        if (cue_out !== 1'b0) begin
            $display("FAIL: cue enable off must force cue_out low");
            $fatal;
        end

        btnC = 1'b1;
        repeat (5) @(negedge clk);
        if ((dut.risk_state !== ST_INVALID) || (cue_out !== 1'b0)) begin
            $display("FAIL: reset must force INVALID and cue_out low");
            $fatal;
        end

        $display("PASS: balat_basys3_top integration");
        $finish;
    end

endmodule
