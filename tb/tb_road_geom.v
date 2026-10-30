`timescale 1ns/1ps

module tb_road_geom;

    reg  signed [31:0] px, py, ax, ay, bx, by;
    reg  signed [15:0] ux_q14, uy_q14;
    reg         clk;
    reg         rst;
    wire [63:0] dist2;
    wire        inside_span;

    integer fd;
    integer rc;
    integer px_i, py_i, ax_i, ay_i, bx_i, by_i, ux_i, uy_i;
    reg [63:0] exp_dist2;
    integer exp_inside;
    integer errors;

    always #5 clk = ~clk;

    road_geom dut (
        .clk (clk),
        .rst (rst),
        .px (px),
        .py (py),
        .ax (ax),
        .ay (ay),
        .bx (bx),
        .by (by),
        .ux_q14 (ux_q14),
        .uy_q14 (uy_q14),
        .dist2 (dist2),
        .inside_span (inside_span)
    );

    initial begin
        clk = 0;
        rst = 1;
        px = 0; py = 0; ax = 0; ay = 0; bx = 0; by = 0;
        ux_q14 = 0; uy_q14 = 0;
        errors = 0;

        repeat (3) @(posedge clk);
        rst = 0;

        fd = $fopen("tb/road_geom_vectors.txt", "r");
        if (fd == 0) begin
            $display("FAIL: cannot open tb/road_geom_vectors.txt");
            $fatal;
        end

        rc = $fscanf(fd, "%d %d %d %d %d %d %d %d %h %d\n",
                     px_i, py_i, ax_i, ay_i, bx_i, by_i, ux_i, uy_i,
                     exp_dist2, exp_inside);
        while (rc == 10) begin
            px = px_i; py = py_i;
            ax = ax_i; ay = ay_i;
            bx = bx_i; by = by_i;
            ux_q14 = ux_i[15:0];
            uy_q14 = uy_i[15:0];
            repeat (8) @(posedge clk);

            if ((dist2 !== exp_dist2) || (inside_span !== exp_inside[0])) begin
                $display("FAIL: P=(%0d,%0d) A=(%0d,%0d) B=(%0d,%0d) u=(%0d,%0d) expected dist2=%0d inside=%0d got dist2=%0d inside=%0d",
                         px_i, py_i, ax_i, ay_i, bx_i, by_i, ux_i, uy_i,
                         exp_dist2, exp_inside, dist2, inside_span);
                errors = errors + 1;
            end

            rc = $fscanf(fd, "%d %d %d %d %d %d %d %d %h %d\n",
                         px_i, py_i, ax_i, ay_i, bx_i, by_i, ux_i, uy_i,
                         exp_dist2, exp_inside);
        end
        $fclose(fd);

        if (errors != 0) begin
            $display("FAIL: %0d geometry vector(s) failed", errors);
            $fatal;
        end
        $display("PASS: road_geom vectors");
        $finish;
    end

endmodule
