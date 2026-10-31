// velocity_estimator — computes 2D velocity from successive valid GNSS fixes,
// applies jitter suppression (uncertainty margin), and checks approach towards road.

module velocity_estimator #(
    parameter [63:0] MIN_SPEED2_THRESH = 64'd900,     // 30 cm/s -> 900 (cm/s)^2
    parameter [63:0] MAX_SPEED2_THRESH = 64'd2_250_000 // 1500 cm/s
) (
    input  wire               clk,
    input  wire               rst,
    input  wire signed [31:0] px,
    input  wire signed [31:0] py,
    input  wire               fix_valid,
    input  wire               fix_ready,
    input  wire signed [31:0] closest_qx,
    input  wire signed [31:0] closest_qy,

    output reg  signed [31:0] vx,
    output reg  signed [31:0] vy,
    output reg         [63:0] speed2,
    output reg                approaching,
    output reg                valid_vel,
    output reg                vel_ready
);

    reg signed [31:0] px_prev;
    reg signed [31:0] py_prev;
    reg               has_prev;

    // Immediate velocity from current fix and registered previous fix
    wire signed [31:0] new_vx = px - px_prev;
    wire signed [31:0] new_vy = py - py_prev;

    // Vector to road: R = Q - P (using current position P)
    wire signed [31:0] rx = closest_qx - px;
    wire signed [31:0] ry = closest_qy - py;

    // Dot product: V dot R = new_vx*rx + new_vy*ry
    wire signed [63:0] dot_x = $signed(new_vx) * $signed(rx);
    wire signed [63:0] dot_y = $signed(new_vy) * $signed(ry);
    wire signed [63:0] dot_prod = dot_x + dot_y;

    wire [63:0] calc_speed2 = $signed(new_vx) * $signed(new_vx) + $signed(new_vy) * $signed(new_vy);

    always @(posedge clk) begin
        if (rst) begin
            px_prev     <= 32'sd0;
            py_prev     <= 32'sd0;
            has_prev    <= 1'b0;
            vx          <= 32'sd0;
            vy          <= 32'sd0;
            speed2      <= 64'd0;
            approaching <= 1'b0;
            valid_vel   <= 1'b0;
            vel_ready   <= 1'b0;
        end else begin
            vel_ready <= 1'b0;

            if (fix_ready) begin
                if (fix_valid) begin
                    if (has_prev) begin
                        vx <= new_vx;
                        vy <= new_vy;

                        // Jitter & plausibility check
                        if (calc_speed2 >= MIN_SPEED2_THRESH && calc_speed2 <= MAX_SPEED2_THRESH) begin
                            speed2      <= calc_speed2;
                            approaching <= (dot_prod > 64'sd0);
                            valid_vel   <= 1'b1;
                        end else if (calc_speed2 < MIN_SPEED2_THRESH) begin
                            // Jitter / stationary
                            speed2      <= 64'd0;
                            approaching <= 1'b0;
                            valid_vel   <= 1'b1;
                        end else begin
                            // Implausible jump (> 15 m/s)
                            speed2      <= 64'd0;
                            approaching <= 1'b0;
                            valid_vel   <= 1'b0; // discard jump
                        end

                        vel_ready <= 1'b1;
                    end else begin
                        has_prev <= 1'b1;
                    end
                    px_prev <= px;
                    py_prev <= py;
                end else begin
                    // Invalid fix resets velocity state
                    has_prev    <= 1'b0;
                    valid_vel   <= 1'b0;
                    approaching <= 1'b0;
                    vx          <= 32'sd0;
                    vy          <= 32'sd0;
                    speed2      <= 64'd0;
                end
            end
        end
    end

endmodule
