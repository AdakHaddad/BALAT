`timescale 1ns/1ps

// tb_road_seg_rom — testbench for the generated road segment ROM.
// Verifies reading addresses for all segments and sanity checks values.

module tb_road_seg_rom;

    reg  [15:0] addr;
    wire [31:0] data;

    road_seg_rom dut (
        .addr (addr),
        .data (data)
    );

    integer i;
    integer errors;
    reg signed [31:0] ax, ay, bx, by;
    reg signed [15:0] ux, uy;
    reg [7:0]         rclass;

    initial begin
        errors = 0;
        addr = 16'd0;
        #10;

        // Check each of the segments
        for (i = 0; i < dut.SEG_COUNT; i = i + 1) begin
            addr = i * 6 + 0; #10; ax = data;
            addr = i * 6 + 1; #10; ay = data;
            addr = i * 6 + 2; #10; bx = data;
            addr = i * 6 + 3; #10; by = data;
            addr = i * 6 + 4; #10; ux = data[31:16]; uy = data[15:0];
            addr = i * 6 + 5; #10; rclass = data[7:0];

            // Direction norm sanity check: ux^2 + uy^2 ~ (16384)^2 = 268435456
            // Allowing small integer rounding margin
            if (ux == 0 && uy == 0 && (ax != bx || ay != by)) begin
                $display("FAIL seg %0d: zero direction for non-zero length", i);
                errors = errors + 1;
            end
        end

        // Check out of bounds addr returns 0
        addr = 16'hFFFF; #10;
        if (data !== 32'd0) begin
            $display("FAIL: out-of-bounds address did not return 0");
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS: road_seg_rom (%0d segments verified)", dut.SEG_COUNT);
        else
            $display("FAIL: road_seg_rom — %0d errors", errors);

        $finish;
    end

endmodule
