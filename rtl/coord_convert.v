// coord_convert — converts GNSS lat/lon (1e-7 deg) to local Cartesian (px, py) in signed cm.
//
// Uses fixed-point scaling relative to a configured local origin.
// Scale factor: 1 deg ~ 111.19492 km -> 1.1119492 cm per 1e-7 deg.
// Approximated as: N * 72872 >>> 16 (error < 0.005%, ~10 cm over 10 km).
// Longitudinal scale is modulated by cos(origin_lat) via Q14 scale.

module coord_convert #(
    parameter signed [31:0] ORIGIN_LAT_DEG7  = -32'sd338250000, // -33.825 deg
    parameter signed [31:0] ORIGIN_LON_DEG7  =  32'sd186500000, //  18.650 deg
    // cos(-33.825 deg) ~ 0.83076 * 16384 = 13611
    parameter signed [15:0] COS_LAT_Q14      =  16'sd13611
) (
    input  wire               clk,
    input  wire               rst,
    input  wire signed [31:0] lat_deg7,
    input  wire signed [31:0] lon_deg7,
    input  wire               fix_valid,
    input  wire               fix_ready,

    output reg  signed [31:0] px,
    output reg  signed [31:0] py,
    output reg                pos_valid,
    output reg                pos_ready
);

    wire signed [31:0] dlat = lat_deg7 - ORIGIN_LAT_DEG7;
    wire signed [31:0] dlon = lon_deg7 - ORIGIN_LON_DEG7;

    // Intermediate 64-bit products
    wire signed [63:0] y_scaled = $signed(dlat) * 64'sd72872;
    wire signed [31:0] y_cm = y_scaled[47:16];

    wire signed [63:0] x_raw = $signed(dlon) * 64'sd72872;
    wire signed [31:0] x_mid = x_raw[47:16];
    wire signed [47:0] x_scaled = $signed(x_mid) * $signed(COS_LAT_Q14);
    wire signed [31:0] x_cm = x_scaled[45:14];

    always @(posedge clk) begin
        if (rst) begin
            px        <= 32'sd0;
            py        <= 32'sd0;
            pos_valid <= 1'b0;
            pos_ready <= 1'b0;
        end else begin
            pos_ready <= 1'b0;
            if (fix_ready) begin
                px        <= x_cm;
                py        <= y_cm;
                pos_valid <= fix_valid;
                pos_ready <= 1'b1;
            end
        end
    end

endmodule
