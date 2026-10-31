`timescale 1ns/1ps

// tb_velocity_estimator — testbench for 2D velocity estimation and approach detection.

module tb_velocity_estimator;

    reg        clk;
    reg        rst;
    reg signed [31:0] px, py;
    reg        fix_valid;
    reg        fix_ready;
    reg signed [31:0] closest_qx, closest_qy;

    wire signed [31:0] vx, vy;
    wire        [63:0] speed2;
    wire               approaching;
    wire               valid_vel;
    wire               vel_ready;

    velocity_estimator #(
        .MIN_SPEED2_THRESH (32'd900),     // 30 cm/s
        .MAX_SPEED2_THRESH (32'd2_250_000) // 1500 cm/s
    ) dut (
        .clk        (clk),
        .rst        (rst),
        .px         (px),
        .py         (py),
        .fix_valid  (fix_valid),
        .fix_ready  (fix_ready),
        .closest_qx (closest_qx),
        .closest_qy (closest_qy),
        .vx         (vx),
        .vy         (vy),
        .speed2     (speed2),
        .approaching(approaching),
        .valid_vel  (valid_vel),
        .vel_ready  (vel_ready)
    );

    always #5 clk = ~clk;

    integer errors;

    task send_fix(input signed [31:0] in_x, input signed [31:0] in_y, input in_valid);
        begin
            @(posedge clk);
            px        <= in_x;
            py        <= in_y;
            fix_valid <= in_valid;
            fix_ready <= 1'b1;
            @(posedge clk);
            fix_ready <= 1'b0;
            @(posedge clk);
        end
    endtask

    initial begin
        clk = 0;
        rst = 1;
        px = 0; py = 0;
        fix_valid = 0; fix_ready = 0;
        closest_qx = 32'sd1000; // road at x=1000, y=0
        closest_qy = 32'sd0;
        errors = 0;

        repeat (5) @(posedge clk);
        rst <= 0;
        repeat (5) @(posedge clk);

        // Test 1: First fix -> no velocity yet
        send_fix(32'sd0, 32'sd0, 1'b1);
        if (valid_vel !== 1'b0) begin
            $display("FAIL Test 1: valid_vel on first fix");
            errors = errors + 1;
        end

        // Test 2: Second fix -> moving east +100 cm/s towards road (100, 0)
        send_fix(32'sd100, 32'sd0, 1'b1);
        if (valid_vel !== 1'b1 || vx !== 32'sd100 || approaching !== 1'b1) begin
            $display("FAIL Test 2: vx=%0d, approaching=%b (expected vx=100, app=1)", vx, approaching);
            errors = errors + 1;
        end else begin
            $display("PASS Test 2: approach toward road detected (vx=%0d, vy=%0d)", vx, vy);
        end

        // Test 3: Third fix -> moving west -100 cm/s away from road (0, 0)
        send_fix(32'sd0, 32'sd0, 1'b1);
        if (vx !== -32'sd100 || approaching !== 1'b0) begin
            $display("FAIL Test 3: vx=%0d, approaching=%b (expected vx=-100, app=0)", vx, approaching);
            errors = errors + 1;
        end else begin
            $display("PASS Test 3: retreat from road detected (vx=%0d, app=0)", vx);
        end

        // Test 4: Small GPS jitter (10 cm movement < 30 cm/s threshold)
        send_fix(32'sd10, 32'sd0, 1'b1);
        if (approaching !== 1'b0 || speed2 !== 64'd0) begin
            $display("FAIL Test 4: jitter not filtered (speed2=%0d)", speed2);
            errors = errors + 1;
        end else begin
            $display("PASS Test 4: jitter filtered to speed=0");
        end

        // Test 5: Implausible jump (5000 cm = 50 m in 1 s > 15 m/s)
        send_fix(32'sd5010, 32'sd0, 1'b1);
        if (valid_vel !== 1'b0) begin
            $display("FAIL Test 5: implausible jump not rejected");
            errors = errors + 1;
        end else begin
            $display("PASS Test 5: implausible jump rejected");
        end

        // Test 6: Invalid fix (status V)
        send_fix(32'sd0, 32'sd0, 1'b0);
        if (valid_vel !== 1'b0 || dut.has_prev !== 1'b0) begin
            $display("FAIL Test 6: invalid fix did not reset state");
            errors = errors + 1;
        end else begin
            $display("PASS Test 6: invalid fix resets state");
        end

        if (errors == 0)
            $display("PASS: velocity_estimator all tests passed");
        else
            $display("FAIL: velocity_estimator %0d errors", errors);

        $finish;
    end

endmodule
