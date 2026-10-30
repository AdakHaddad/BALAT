// road_geom — pipelined point-to-segment squared distance for the BALAT demo.
//
// Coordinates are signed centimetres. The demo is bounded to |x|,|y| <= 1,000,000 cm
// so that the 64-bit squared-distance result cannot overflow.
//
// The road record supplies endpoints A/B and a precomputed Q14 unit direction:
//   16384 == 1.0.  The direction must be derived offline from B-A.
// This avoids a runtime divider; the map preparation tool is responsible for
// producing a consistent direction and endpoints.
//
// inside_span is high when the projection falls strictly between A and B.
// For an outside projection, dist2 is the squared distance to the nearer endpoint.
// For an inside projection, dist2 is the squared perpendicular distance.
// A zero-length segment (A == B, direction 0,0) resolves to the A endpoint.
//
// Latency: 7 clk cycles from input to dist2/inside_span. Inputs are expected
// to be stable for at least that long; the demo updates them at 10 Hz.
module road_geom (
    input  wire               clk,
    input  wire               rst,
    input  wire signed [31:0] px,
    input  wire signed [31:0] py,
    input  wire signed [31:0] ax,
    input  wire signed [31:0] ay,
    input  wire signed [31:0] bx,
    input  wire signed [31:0] by,
    input  wire signed [15:0] ux_q14,
    input  wire signed [15:0] uy_q14,
    output reg  [63:0]        dist2,
    output reg                inside_span
);

    reg signed [31:0] px_s1, py_s1, ax_s1, ay_s1, bx_s1, by_s1;
    reg signed [15:0] ux_s1, uy_s1;

    always @(posedge clk) begin
        if (rst) begin
            px_s1 <= 32'sd0; py_s1 <= 32'sd0;
            ax_s1 <= 32'sd0; ay_s1 <= 32'sd0;
            bx_s1 <= 32'sd0; by_s1 <= 32'sd0;
            ux_s1 <= 16'sd0; uy_s1 <= 16'sd0;
        end else begin
            px_s1 <= px; py_s1 <= py;
            ax_s1 <= ax; ay_s1 <= ay;
            bx_s1 <= bx; by_s1 <= by;
            ux_s1 <= ux_q14; uy_s1 <= uy_q14;
        end
    end

    reg signed [32:0] relx_s2, rely_s2, bax_s2, bay_s2;
    reg signed [15:0] ux_s2, uy_s2;

    always @(posedge clk) begin
        if (rst) begin
            relx_s2 <= 33'sd0; rely_s2 <= 33'sd0;
            bax_s2  <= 33'sd0; bay_s2  <= 33'sd0;
            ux_s2   <= 16'sd0; uy_s2   <= 16'sd0;
        end else begin
            relx_s2 <= $signed(px_s1) - $signed(ax_s1);
            rely_s2 <= $signed(py_s1) - $signed(ay_s1);
            bax_s2  <= $signed(bx_s1) - $signed(ax_s1);
            bay_s2  <= $signed(by_s1) - $signed(ay_s1);
            ux_s2   <= ux_s1; uy_s2 <= uy_s1;
        end
    end

    reg signed [48:0] p1_s3, p2_s3, p3_s3, p4_s3, p5_s3, p6_s3;
    reg signed [32:0] relx_s3, rely_s3;
    reg signed [31:0] px_s3, py_s3, bx_s3, by_s3;

    always @(posedge clk) begin
        if (rst) begin
            p1_s3 <= 49'sd0; p2_s3 <= 49'sd0;
            p3_s3 <= 49'sd0; p4_s3 <= 49'sd0;
            p5_s3 <= 49'sd0; p6_s3 <= 49'sd0;
            relx_s3 <= 33'sd0; rely_s3 <= 33'sd0;
            px_s3 <= 32'sd0; py_s3 <= 32'sd0;
            bx_s3 <= 32'sd0; by_s3 <= 32'sd0;
        end else begin
            p1_s3 <= relx_s2 * $signed(ux_s2);
            p2_s3 <= rely_s2 * $signed(uy_s2);
            p3_s3 <= bax_s2  * $signed(ux_s2);
            p4_s3 <= bay_s2  * $signed(uy_s2);
            p5_s3 <= relx_s2 * $signed(uy_s2);
            p6_s3 <= rely_s2 * $signed(ux_s2);
            relx_s3 <= relx_s2; rely_s3 <= rely_s2;
            px_s3 <= px_s1; py_s3 <= py_s1;
            bx_s3 <= bx_s1; by_s3 <= by_s1;
        end
    end

    reg signed [49:0] along_s4, b_along_s4, perp_s4;

    always @(posedge clk) begin
        if (rst) begin
            along_s4   <= 50'sd0;
            b_along_s4 <= 50'sd0;
            perp_s4    <= 50'sd0;
        end else begin
            along_s4   <= p1_s3 + p2_s3;
            b_along_s4 <= p3_s3 + p4_s3;
            perp_s4    <= p5_s3 - p6_s3;
        end
    end

    reg signed [32:0] dx_s4, dy_s4;
    reg               inside_s4;

    always @(posedge clk) begin
        if (rst) begin
            dx_s4 <= 33'sd0;
            dy_s4 <= 33'sd0;
            inside_s4 <= 1'b0;
        end else if (along_s4 <= 0) begin
            dx_s4 <= relx_s3;
            dy_s4 <= rely_s3;
            inside_s4 <= 1'b0;
        end else if (along_s4 >= b_along_s4) begin
            dx_s4 <= $signed(px_s3) - $signed(bx_s3);
            dy_s4 <= $signed(py_s3) - $signed(by_s3);
            inside_s4 <= 1'b0;
        end else begin
            // For the documented coordinate range this fits in 33 bits.
            dx_s4 <= $signed(perp_s4[46:14]);
            dy_s4 <= 33'sd0;
            inside_s4 <= 1'b1;
        end
    end

    reg signed [63:0] dx2_s5, dy2_s5;
    reg               inside_s5;

    always @(posedge clk) begin
        if (rst) begin
            dx2_s5 <= 64'sd0;
            dy2_s5 <= 64'sd0;
            inside_s5 <= 1'b0;
        end else begin
            dx2_s5 <= dx_s4 * dx_s4;
            dy2_s5 <= dy_s4 * dy_s4;
            inside_s5 <= inside_s4;
        end
    end

    always @(posedge clk) begin
        if (rst) begin
            dist2 <= 64'd0;
            inside_span <= 1'b0;
        end else begin
            dist2 <= dx2_s5 + dy2_s5;
            inside_span <= inside_s5;
        end
    end

endmodule
