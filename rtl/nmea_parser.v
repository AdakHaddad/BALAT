// nmea_parser — streaming NMEA $xxRMC parser for BALAT v0.1.
//
// Accepts one UART byte at a time via (rx_data, rx_valid). Parses $GPRMC and
// $GNRMC sentences only; all others are silently ignored.
//
// Outputs are latched on the rising edge of `fix_ready` and remain stable until
// the next `fix_ready` pulse.
//
// Coordinate output:
//   lat_deg7  — latitude  in units of 1e-7 degrees, signed (north positive)
//   lon_deg7  — longitude in units of 1e-7 degrees, signed (east  positive)
//   speed_kn  — speed over ground in 1/100 knot (unsigned)
//   utc_time  — UTC hhmmss in packed BCD, 24-bit (hh[23:16] mm[15:8] ss[7:0])
//   fix_valid — 1 if status field is 'A' (active), 0 if 'V' (void)
//
// The module validates the NMEA XOR checksum (*XX). If the checksum fails the
// sentence is silently dropped and no `fix_ready` pulse is issued.
//
// Stale-fix detection is left to downstream logic (risk_fsm watchdog).
// This module does not convert to local metric coordinates; that is done by a
// separate coord_convert module.
//
// Width/unit contract:
//   lat_deg7  : signed 32-bit, range +/- 900_000_000  (±90.0000000°)
//   lon_deg7  : signed 32-bit, range +/- 1_800_000_000 (±180.0000000°)
//   speed_kn  : unsigned 16-bit, 0..65535 (0..655.35 knots)
//   utc_time  : unsigned 24-bit packed BCD
//
// Latency: one cycle after the final checksum character to fix_ready.
// Resource: no multipliers, no BRAM. Uses a combinational divide-by-3 function.

module nmea_parser (
    input  wire        clk,
    input  wire        rst,
    input  wire [7:0]  rx_data,
    input  wire        rx_valid,

    output reg  signed [31:0] lat_deg7,
    output reg  signed [31:0] lon_deg7,
    output reg         [15:0] speed_kn,
    output reg         [23:0] utc_time,
    output reg                fix_valid,
    output reg                fix_ready   // single-cycle pulse
);

    // ---------------------------------------------------------------
    // States
    // ---------------------------------------------------------------
    localparam S_IDLE       = 4'd0;
    localparam S_TALKER     = 4'd1;
    localparam S_UTC        = 4'd2;
    localparam S_STATUS     = 4'd3;
    localparam S_LAT        = 4'd4;
    localparam S_NS         = 4'd5;
    localparam S_LON        = 4'd6;
    localparam S_EW         = 4'd7;
    localparam S_SPEED      = 4'd8;
    localparam S_SKIP       = 4'd9;
    localparam S_CKSUM_HI   = 4'd10;
    localparam S_CKSUM_LO   = 4'd11;

    reg [3:0] state, state_next;
    reg [3:0] char_idx;
    reg [7:0] xor_ck;            // running XOR between '$' and '*'
    reg       xor_active;

    // ---------------------------------------------------------------
    // Hex nibble
    // ---------------------------------------------------------------
    function [3:0] hex_val;
        input [7:0] ch;
        begin
            if (ch >= "0" && ch <= "9")
                hex_val = ch - "0";
            else if (ch >= "A" && ch <= "F")
                hex_val = ch - "A" + 4'd10;
            else if (ch >= "a" && ch <= "f")
                hex_val = ch - "a" + 4'd10;
            else
                hex_val = 4'd0;
        end
    endfunction

    // ---------------------------------------------------------------
    // Divide unsigned 32-bit by 3, with rounding.
    // ---------------------------------------------------------------
    function [31:0] div3;
        input [31:0] x;
        reg [31:0] q, r;
        integer i;
        begin
            q = 0; r = 0;
            for (i = 31; i >= 0; i = i - 1) begin
                r = {r[30:0], x[i]};
                if (r >= 32'd3) begin
                    q[i] = 1'b1;
                    r = r - 32'd3;
                end
            end
            div3 = (r >= 32'd2) ? q + 32'd1 : q;
        end
    endfunction

    // ---------------------------------------------------------------
    // Per-sentence accumulators
    // ---------------------------------------------------------------
    reg [23:0] p_utc;
    reg        p_status;
    reg [15:0] p_deg;
    reg [31:0] p_min_int;
    reg [31:0] p_min_frac;
    reg [3:0]  p_min_frac_d;
    reg        past_dot;
    reg signed [31:0] p_lat;
    reg signed [31:0] p_lon;
    reg [31:0] spd_int;
    reg [31:0] spd_frac;
    reg [3:0]  spd_frac_d;
    reg [15:0] p_speed;
    reg [7:0]  p_cksum_hi;  // high nibble of expected checksum

    // ---------------------------------------------------------------
    // Combinational: convert deg + min fields to 1e-7 degrees
    // Formula: deg7 = deg * 10_000_000 + div3(min_combined * 50)
    //   where min_combined = min_int * 10^4 + min_frac (padded to 4 digits)
    // ---------------------------------------------------------------
    // Pad min_frac to 4 digits
    wire [31:0] min_frac_padded =
        (p_min_frac_d == 4'd0) ? 32'd0 :
        (p_min_frac_d == 4'd1) ? p_min_frac * 1000 :
        (p_min_frac_d == 4'd2) ? p_min_frac * 100 :
        (p_min_frac_d == 4'd3) ? p_min_frac * 10 :
                                 p_min_frac;

    wire [31:0] min_combined = p_min_int * 32'd10000 + min_frac_padded;
    wire [31:0] min_x50      = min_combined * 32'd50;
    wire [31:0] min_deg7     = div3(min_x50);
    wire [31:0] coord_deg7   = p_deg * 32'd10_000_000 + min_deg7;

    // ---------------------------------------------------------------
    // Main FSM
    // ---------------------------------------------------------------
    always @(posedge clk) begin
        if (rst) begin
            state      <= S_IDLE;
            fix_ready  <= 1'b0;
            fix_valid  <= 1'b0;
            lat_deg7   <= 32'sd0;
            lon_deg7   <= 32'sd0;
            speed_kn   <= 16'd0;
            utc_time   <= 24'd0;
            xor_ck     <= 8'd0;
            xor_active <= 1'b0;
            char_idx   <= 4'd0;
            p_utc      <= 24'd0;
            p_status   <= 1'b0;
            p_lat      <= 32'sd0;
            p_lon      <= 32'sd0;
            p_speed    <= 16'd0;
            p_deg      <= 16'd0;
            p_min_int  <= 32'd0;
            p_min_frac <= 32'd0;
            p_min_frac_d <= 4'd0;
            past_dot   <= 1'b0;
            spd_int    <= 32'd0;
            spd_frac   <= 32'd0;
            spd_frac_d <= 4'd0;
            p_cksum_hi <= 8'd0;
        end else begin
            fix_ready <= 1'b0;

            if (rx_valid) begin
                // XOR checksum accumulation
                if (xor_active && rx_data != "*")
                    xor_ck <= xor_ck ^ rx_data;

                case (state)

                S_IDLE: begin
                    if (rx_data == "$") begin
                        state      <= S_TALKER;
                        char_idx   <= 4'd0;
                        xor_ck     <= 8'd0;
                        xor_active <= 1'b1;
                    end
                end

                S_TALKER: begin
                    if (rx_data == ",") begin
                        // Check we matched all 5 characters of "G[PN]RMC"
                        if (char_idx == 4'd5) begin
                            state    <= S_UTC;
                            char_idx <= 4'd0;
                        end else begin
                            state      <= S_IDLE;
                            xor_active <= 1'b0;
                        end
                    end else begin
                        // Validate each character
                        case (char_idx)
                            4'd0: if (rx_data != "G") begin state <= S_IDLE; xor_active <= 1'b0; end
                            4'd1: if (rx_data != "P" && rx_data != "N") begin state <= S_IDLE; xor_active <= 1'b0; end
                            4'd2: if (rx_data != "R") begin state <= S_IDLE; xor_active <= 1'b0; end
                            4'd3: if (rx_data != "M") begin state <= S_IDLE; xor_active <= 1'b0; end
                            4'd4: if (rx_data != "C") begin state <= S_IDLE; xor_active <= 1'b0; end
                            default: begin state <= S_IDLE; xor_active <= 1'b0; end
                        endcase
                        if (char_idx <= 4'd4)
                            char_idx <= char_idx + 4'd1;
                    end
                end

                S_UTC: begin
                    if (rx_data == ",") begin
                        state    <= S_STATUS;
                        char_idx <= 4'd0;
                    end else if (rx_data == ".") begin
                        // ignore fractional seconds, stop incrementing char_idx
                    end else if (rx_data >= "0" && rx_data <= "9") begin
                        case (char_idx)
                            4'd0: p_utc[23:20] <= rx_data[3:0];
                            4'd1: p_utc[19:16] <= rx_data[3:0];
                            4'd2: p_utc[15:12] <= rx_data[3:0];
                            4'd3: p_utc[11:8]  <= rx_data[3:0];
                            4'd4: p_utc[7:4]   <= rx_data[3:0];
                            4'd5: p_utc[3:0]   <= rx_data[3:0];
                            default: ;
                        endcase
                        if (char_idx < 4'd6)
                            char_idx <= char_idx + 4'd1;
                    end
                end

                S_STATUS: begin
                    if (rx_data == ",") begin
                        state        <= S_LAT;
                        char_idx     <= 4'd0;
                        p_deg        <= 16'd0;
                        p_min_int    <= 32'd0;
                        p_min_frac   <= 32'd0;
                        p_min_frac_d <= 4'd0;
                        past_dot     <= 1'b0;
                    end else begin
                        p_status <= (rx_data == "A");
                    end
                end

                S_LAT: begin
                    if (rx_data == ",") begin
                        p_lat    <= $signed(coord_deg7);
                        state    <= S_NS;
                        char_idx <= 4'd0;
                    end else if (rx_data == ".") begin
                        past_dot <= 1'b1;
                    end else if (rx_data >= "0" && rx_data <= "9") begin
                        if (!past_dot) begin
                            // lat: first 2 chars are degrees, rest are min integer
                            if (char_idx < 4'd2)
                                p_deg <= p_deg * 10 + {12'd0, rx_data[3:0]};
                            else
                                p_min_int <= p_min_int * 10 + {28'd0, rx_data[3:0]};
                        end else begin
                            if (p_min_frac_d < 4'd4) begin
                                p_min_frac   <= p_min_frac * 10 + {28'd0, rx_data[3:0]};
                                p_min_frac_d <= p_min_frac_d + 4'd1;
                            end
                        end
                        char_idx <= char_idx + 4'd1;
                    end
                end

                S_NS: begin
                    if (rx_data == ",") begin
                        state        <= S_LON;
                        char_idx     <= 4'd0;
                        p_deg        <= 16'd0;
                        p_min_int    <= 32'd0;
                        p_min_frac   <= 32'd0;
                        p_min_frac_d <= 4'd0;
                        past_dot     <= 1'b0;
                    end else begin
                        if (rx_data == "S" || rx_data == "s")
                            p_lat <= -p_lat;
                    end
                end

                S_LON: begin
                    if (rx_data == ",") begin
                        p_lon    <= $signed(coord_deg7);
                        state    <= S_EW;
                        char_idx <= 4'd0;
                    end else if (rx_data == ".") begin
                        past_dot <= 1'b1;
                    end else if (rx_data >= "0" && rx_data <= "9") begin
                        if (!past_dot) begin
                            // lon: first 3 chars are degrees
                            if (char_idx < 4'd3)
                                p_deg <= p_deg * 10 + {12'd0, rx_data[3:0]};
                            else
                                p_min_int <= p_min_int * 10 + {28'd0, rx_data[3:0]};
                        end else begin
                            if (p_min_frac_d < 4'd4) begin
                                p_min_frac   <= p_min_frac * 10 + {28'd0, rx_data[3:0]};
                                p_min_frac_d <= p_min_frac_d + 4'd1;
                            end
                        end
                        char_idx <= char_idx + 4'd1;
                    end
                end

                S_EW: begin
                    if (rx_data == ",") begin
                        state      <= S_SPEED;
                        char_idx   <= 4'd0;
                        spd_int    <= 32'd0;
                        spd_frac   <= 32'd0;
                        spd_frac_d <= 4'd0;
                        past_dot   <= 1'b0;
                    end else begin
                        if (rx_data == "W" || rx_data == "w")
                            p_lon <= -p_lon;
                    end
                end

                S_SPEED: begin
                    if (rx_data == ",") begin
                        // Convert to 1/100 knot
                        case (spd_frac_d)
                            4'd0: p_speed <= spd_int[15:0] * 16'd100;
                            4'd1: p_speed <= spd_int[15:0] * 16'd100 + spd_frac[15:0] * 16'd10;
                            default: p_speed <= spd_int[15:0] * 16'd100 + spd_frac[15:0];
                        endcase
                        state <= S_SKIP;
                    end else if (rx_data == ".") begin
                        past_dot <= 1'b1;
                    end else if (rx_data >= "0" && rx_data <= "9") begin
                        if (!past_dot)
                            spd_int <= spd_int * 10 + {28'd0, rx_data[3:0]};
                        else if (spd_frac_d < 4'd2) begin
                            spd_frac   <= spd_frac * 10 + {28'd0, rx_data[3:0]};
                            spd_frac_d <= spd_frac_d + 4'd1;
                        end
                    end
                end

                S_SKIP: begin
                    if (rx_data == "*") begin
                        xor_active <= 1'b0;
                        state      <= S_CKSUM_HI;
                    end else if (rx_data == "$" || rx_data == 8'h0D || rx_data == 8'h0A) begin
                        // Unexpected end or new sentence
                        state      <= S_IDLE;
                        xor_active <= 1'b0;
                    end
                end

                S_CKSUM_HI: begin
                    p_cksum_hi <= {4'd0, hex_val(rx_data)};
                    state      <= S_CKSUM_LO;
                end

                S_CKSUM_LO: begin
                    // Validate checksum
                    if ({p_cksum_hi[3:0], hex_val(rx_data)} == xor_ck) begin
                        lat_deg7  <= p_lat;
                        lon_deg7  <= p_lon;
                        speed_kn  <= p_speed;
                        utc_time  <= p_utc;
                        fix_valid <= p_status;
                        fix_ready <= 1'b1;
                    end
                    // else: bad checksum, drop silently
                    state <= S_IDLE;
                end

                default: begin
                    state      <= S_IDLE;
                    xor_active <= 1'b0;
                end

                endcase
            end // rx_valid
        end // !rst
    end

endmodule
