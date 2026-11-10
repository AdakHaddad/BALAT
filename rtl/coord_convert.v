// coord_convert — converts GNSS lat/lon (1e-7 deg) to local Cartesian cm.
//
// RTL-equivalent fixed point:
//   dy = sar64((lat - origin_lat) * 72872, 16)
//   x_mid = sar64((lon - origin_lon) * 72872, 16)
//   dx = sar64(x_mid * cos_origin_q14, 14)
//
// Inputs are captured on fix_ready, then processed over three registered
// stages to keep the multiplier path within the 100 MHz Basys 3 clock.
// pos_ready pulses with px/py three clocks after the accepted fix_ready edge.
//
// Origin: Sumbawa Besar town centre, West Nusa Tenggara, Indonesia
//   lat = -8.490 deg  → ORIGIN_LAT_DEG7 = -84_900_000
//   lon = 117.420 deg → ORIGIN_LON_DEG7 = 1_174_200_000
//   cos(-8.490 deg) × 16384 = 16204
// Map data: Sumbawa Besar road network — see data/road_manifest.json
module coord_convert #(
    parameter signed [31:0] ORIGIN_LAT_DEG7 = -32'sd84900000,
    parameter signed [31:0] ORIGIN_LON_DEG7 =  32'sd1174200000,
    parameter signed [15:0] COS_LAT_Q14     = 16'sd16204
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
    localparam [1:0] ST_WAIT = 2'd0;
    localparam [1:0] ST_SCALE = 2'd1;
    localparam [1:0] ST_COS = 2'd2;
    localparam [1:0] ST_PUBLISH = 2'd3;
    reg [1:0] state;

    reg signed [31:0] dlat_q, dlon_q;
    reg signed [63:0] y_scaled_q, x_raw_q;
    reg signed [47:0] x_scaled_q;
    reg signed [31:0] y_cm_q;
    reg valid_q;

    always @(posedge clk) begin
        if (rst) begin
            state <= ST_WAIT;
            dlat_q <= 0;
            dlon_q <= 0;
            y_scaled_q <= 0;
            x_raw_q <= 0;
            x_scaled_q <= 0;
            y_cm_q <= 0;
            valid_q <= 0;
            px <= 0;
            py <= 0;
            pos_valid <= 0;
            pos_ready <= 0;
        end else begin
            pos_ready <= 0;
            case (state)
                ST_WAIT: if (fix_ready) begin
                    dlat_q <= lat_deg7 - ORIGIN_LAT_DEG7;
                    dlon_q <= lon_deg7 - ORIGIN_LON_DEG7;
                    valid_q <= fix_valid;
                    state <= ST_SCALE;
                end
                ST_SCALE: begin
                    y_scaled_q <= $signed(dlat_q) * 64'sd72872;
                    x_raw_q <= $signed(dlon_q) * 64'sd72872;
                    state <= ST_COS;
                end
                ST_COS: begin
                    y_cm_q <= y_scaled_q[47:16];
                    x_scaled_q <= $signed(x_raw_q[47:16]) * $signed(COS_LAT_Q14);
                    state <= ST_PUBLISH;
                end
                ST_PUBLISH: begin
                    px <= x_scaled_q[45:14];
                    py <= y_cm_q;
                    pos_valid <= valid_q;
                    pos_ready <= 1;
                    state <= ST_WAIT;
                end
                default: state <= ST_WAIT;
            endcase
        end
    end
endmodule
