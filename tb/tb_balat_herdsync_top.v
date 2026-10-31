`timescale 1ns/1ps

module tb_balat_herdsync_top;

    localparam [2:0] ST_INVALID = 3'd0;

    reg         clk;
    reg         btnC;
    reg  [3:0]  sw;
    reg         RsRx;
    wire [15:0] led;
    wire        cue_out;
    wire        RsTx;

    reg cue_seen;
    reg safe_seen;

    balat_herdsync_basys3_top #(
        .CLK_PER_TICK   (20),
        .LAST_INDEX     (200),
        .CLK_PER_MS     (1),
        .STALE_MS       (50),
        .MAX_ON_TICKS   (3),
        .COOLDOWN_TICKS (5),
        .HEARTBEAT_DIV  (10),
        .UART_CLK_HZ    (100),
        .UART_BAUD      (10)
    ) dut (
        .clk    (clk),
        .btnC   (btnC),
        .sw     (sw),
        .RsRx   (RsRx),
        .led    (led),
        .cue_out(cue_out),
        .RsTx   (RsTx)
    );

    always #5 clk = ~clk;

    always @(posedge clk) begin
        if (cue_out)
            cue_seen <= 1'b1;
        if (dut.risk_state == 3'd1)
            safe_seen <= 1'b1;
    end

    task wait_for_frames(input integer max_cycles);
        integer n;
        begin
            n = 0;
            while ((dut.u_bridge.frames_sent == 16'd0) && (n < max_cycles)) begin
                @(posedge clk);
                n = n + 1;
            end
            if (dut.u_bridge.frames_sent == 16'd0) begin
                $display("FAIL: timeout waiting for a UART frame at time %0t", $time);
                $fatal;
            end
        end
    endtask

    task wait_for_cue(input integer max_cycles);
        integer n;
        begin
            n = 0;
            while (!cue_seen && (n < max_cycles)) begin
                @(posedge clk);
                n = n + 1;
            end
            if (!cue_seen) begin
                $display("FAIL: timeout waiting for cue at time %0t", $time);
                $fatal;
            end
        end
    endtask

    initial begin
        $dumpfile("build/sim/tb_balat_herdsync_top.vcd");
        $dumpvars(0, tb_balat_herdsync_top);

        clk = 0;
        btnC = 1;
        sw = 4'b0000;
        RsRx = 1'b1;
        cue_seen = 1'b0;
        safe_seen = 1'b0;

        repeat (5) @(negedge clk);
        btnC = 0;
        sw = 4'b0101;

        wait_for_frames(20000);
        wait_for_cue(20000);

        if (!safe_seen) begin
            $display("FAIL: risk pipeline never reached SAFE");
            $fatal;
        end
        if (dut.u_bridge.crc_errors !== 16'd0) begin
            $display("FAIL: unexpected UART CRC error");
            $fatal;
        end
        if (RsTx !== 1'b1 && dut.u_bridge.tx_busy === 1'b0) begin
            $display("FAIL: UART TX line invalid while idle");
            $fatal;
        end

        sw[1] = 1'b1;
        repeat (3) @(negedge clk);
        if ((dut.risk_state !== ST_INVALID) || (cue_out !== 1'b0) || (led[7] !== 1'b1)) begin
            $display("FAIL: stale input must force INVALID, fault, and drop cue");
            $fatal;
        end

        sw[1] = 1'b0;
        btnC = 1'b1;
        repeat (5) @(negedge clk);
        if ((dut.risk_state !== ST_INVALID) || (cue_out !== 1'b0)) begin
            $display("FAIL: reset must force INVALID and cue_out low");
            $fatal;
        end

        $display("PASS: balat_herdsync_basys3_top");
        $finish;
    end

endmodule
