`timescale 1ns/1ps

module tb_coord_convert;

    reg        clk;
    reg        rst;
    reg signed [31:0] lat_deg7;
    reg signed [31:0] lon_deg7;
    reg        fix_valid;
    reg        fix_ready;

    wire signed [31:0] px;
    wire signed [31:0] py;
    wire        pos_valid;
    wire        pos_ready;

    coord_convert #(
        .ORIGIN_LAT_DEG7 (-32'sd338250000),
        .ORIGIN_LON_DEG7 ( 32'sd186500000),
        .COS_LAT_Q14     ( 16'sd13611)
    ) dut (
        .clk       (clk),
        .rst       (rst),
        .lat_deg7  (lat_deg7),
        .lon_deg7  (lon_deg7),
        .fix_valid (fix_valid),
        .fix_ready (fix_ready),
        .px        (px),
        .py        (py),
        .pos_valid (pos_valid),
        .pos_ready (pos_ready)
    );

    always #5 clk = ~clk;

    integer errors;

    initial begin
        clk = 0; rst = 1; errors = 0;
        lat_deg7 = 0; lon_deg7 = 0; fix_valid = 0; fix_ready = 0;
        repeat (5) @(posedge clk);
        rst <= 0;
        repeat (5) @(posedge clk);

        // Test 1: Origin itself -> should produce (0, 0)
        @(posedge clk);
        lat_deg7 <= -32'sd338250000;
        lon_deg7 <=  32'sd186500000;
        fix_valid <= 1'b1;
        fix_ready <= 1'b1;
        @(posedge clk);
        fix_ready <= 1'b0;
        wait (pos_ready === 1'b1);
        #1;

        if (px !== 32'sd0 || py !== 32'sd0) begin
            $display("FAIL Test 1: origin expected (0,0), got (%0d, %0d)", px, py);
            errors = errors + 1;
        end else begin
            $display("PASS Test 1: origin maps to (0,0)");
        end

        // Test 2: Point 1000 units north (0.0001 deg ~ 11.12 m = 1112 cm)
        @(posedge clk);
        lat_deg7 <= -32'sd338250000 + 32'sd1000;
        lon_deg7 <=  32'sd186500000;
        fix_valid <= 1'b1;
        fix_ready <= 1'b1;
        @(posedge clk);
        fix_ready <= 1'b0;
        wait (pos_ready === 1'b1);
        #1;

        if (py < 32'sd1100 || py > 32'sd1125 || px !== 32'sd0) begin
            $display("FAIL Test 2: expected py~1112, got px=%0d, py=%0d", px, py);
            errors = errors + 1;
        end else begin
            $display("PASS Test 2: 0.0001 deg north maps to %0d cm", py);
        end

        if (errors == 0)
            $display("PASS: coord_convert all tests passed");
        else
            $display("FAIL: coord_convert %0d errors", errors);

        $finish;
    end

endmodule
