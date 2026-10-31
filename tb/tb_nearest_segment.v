`timescale 1ns/1ps

// tb_nearest_segment — testbench for multi-segment nearest selection.
// Uses road_seg_rom (7 segments) and tests finding the nearest segment.

module tb_nearest_segment;

    reg        clk;
    reg        rst;
    reg        start;
    reg signed [31:0] px;
    reg signed [31:0] py;

    wire [15:0] rom_addr;
    wire [31:0] rom_data;

    wire [63:0] min_dist2;
    wire [7:0]  nearest_seg_id;
    wire        inside_span;
    wire        done;
    wire        busy;

    road_seg_rom #(
        .SEG_COUNT (7)
    ) u_rom (
        .addr (rom_addr),
        .data (rom_data)
    );

    nearest_segment #(
        .SEG_COUNT (7)
    ) dut (
        .clk            (clk),
        .rst            (rst),
        .start          (start),
        .px             (px),
        .py             (py),
        .rom_addr       (rom_addr),
        .rom_data       (rom_data),
        .min_dist2      (min_dist2),
        .nearest_seg_id (nearest_seg_id),
        .inside_span    (inside_span),
        .done           (done),
        .busy           (busy)
    );

    always #5 clk = ~clk;

    integer errors;

    task scan_and_wait;
        input signed [31:0] test_px;
        input signed [31:0] test_py;
        begin
            @(posedge clk);
            px    <= test_px;
            py    <= test_py;
            start <= 1'b1;
            @(posedge clk);
            start <= 1'b0;

            // Wait for done
            while (!done) @(posedge clk);
        end
    endtask

    initial begin
        clk = 0;
        rst = 1;
        start = 0;
        px = 0;
        py = 0;
        errors = 0;

        repeat (5) @(posedge clk);
        rst <= 0;
        repeat (5) @(posedge clk);

        // Test 1: Position on both roads at origin (0, 0)
        scan_and_wait(32'sd0, 32'sd0);
        if (min_dist2 !== 64'd0) begin
            $display("FAIL Test 1: min_dist2 = %0d, expected 0", min_dist2);
            errors = errors + 1;
        end else begin
            $display("PASS Test 1: min_dist2 = 0, nearest_seg = %0d", nearest_seg_id);
        end

        // Test 2: Position (500, 10000) — 500 cm east of y-axis road (seg 1)
        // Seg 1 runs from (0, -18553) to (0, +18553).
        // At y=10000, perpendicular distance to x=0 is 500 cm.
        // Squared distance = 500^2 = 250000.
        scan_and_wait(32'sd500, 32'sd10000);
        if (min_dist2 !== 64'd250000) begin
            $display("FAIL Test 2: min_dist2 = %0d, expected 250000", min_dist2);
            errors = errors + 1;
        end else begin
            $display("PASS Test 2: min_dist2 = 250000, nearest_seg = %0d", nearest_seg_id);
        end

        // Test 3: Far point beyond segment 2 (0, 60000)
        // Seg 2 ends at (0, 55660). Distance = 60000 - 55660 = 4340 cm.
        // dist2 = 4340^2 = 18835600.
        scan_and_wait(32'sd0, 32'sd60000);
        if (min_dist2 !== 64'd18835600) begin
            $display("FAIL Test 3: min_dist2 = %0d, expected 18835600", min_dist2);
            errors = errors + 1;
        end else begin
            $display("PASS Test 3: min_dist2 = 18835600, nearest_seg = %0d", nearest_seg_id);
        end

        if (errors == 0)
            $display("PASS: nearest_segment all tests passed");
        else
            $display("FAIL: nearest_segment %0d errors", errors);

        $finish;
    end

endmodule
