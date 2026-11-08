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
// Latency: seven cycles after the final checksum character to fix_ready. The
// coordinate conversion is split across cycles for 100 MHz timing.
// Resource: no BRAM. Coordinate conversion uses staged constant arithmetic.

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
    localparam S_CONV_LAT1  = 4'd12;
    localparam S_CONV_MID   = 4'd13;
    localparam S_CONV_LON   = 4'd14;
    localparam S_CONV_OUT   = 4'd15;
    localparam [4:0] S_CONV_SIGN = 5'd16;
    localparam [4:0] S_CONV_X50 = 5'd17;

    reg [4:0] state, state_next;
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
        reg [32:0] rounded_input;
        reg [64:0] product;
        begin
            // round(x/3) as floor((x+1)/3), using ceil(2^33/3).
            rounded_input = {1'b0, x} + 33'd1;
            product = rounded_input * 32'hAAAAAAAB;
            div3 = product[64:33];
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
    reg [15:0] lat_deg_raw, lon_deg_raw;
    reg [31:0] lat_min_int_raw, lon_min_int_raw;
    reg [31:0] lat_min_frac_raw, lon_min_frac_raw;
    reg [3:0] lat_min_frac_d_raw, lon_min_frac_d_raw;
    reg lat_negative, lon_negative;
    reg [31:0] lat_base_q, lon_base_q;
    reg [31:0] lat_min_base_q, lon_min_base_q;
    reg [31:0] lat_min_pad_q, lon_min_pad_q;
    reg [31:0] lat_min_comb_q, lon_min_comb_q;
    reg [31:0] lat_min_x50_q, lon_min_x50_q;
    reg [31:0] lat_min_deg7_q, lon_min_deg7_q;
    reg [31:0] lat_result_q, lon_result_q;
    reg [31:0] spd_int;
    reg [31:0] spd_frac;
    reg [3:0]  spd_frac_d;
    reg [15:0] p_speed;
    reg [7:0]  p_cksum_hi;  // high nibble of expected checksum

    // ---------------------------------------------------------------
    // Coordinate fields are converted in registered stages after checksum.
    // ---------------------------------------------------------------
    function [31:0] frac_to_4;
        input [31:0] value;
        input [3:0] digits;
        begin
            case (digits)
                4'd0: frac_to_4 = 32'd0;
                4'd1: frac_to_4 = value * 32'd1000;
                4'd2: frac_to_4 = value * 32'd100;
                4'd3: frac_to_4 = value * 32'd10;
                default: frac_to_4 = value;
            endcase
        end
    endfunction

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
            lat_deg_raw <= 16'd0;
            lon_deg_raw <= 16'd0;
            lat_min_int_raw <= 32'd0;
            lon_min_int_raw <= 32'd0;
            lat_min_frac_raw <= 32'd0;
            lon_min_frac_raw <= 32'd0;
            lat_min_frac_d_raw <= 4'd0;
            lon_min_frac_d_raw <= 4'd0;
            lat_negative <= 1'b0;
            lon_negative <= 1'b0;
            lat_base_q <= 32'd0;
            lon_base_q <= 32'd0;
            lat_min_base_q <= 32'd0;
            lon_min_base_q <= 32'd0;
            lat_min_pad_q <= 32'd0;
            lon_min_pad_q <= 32'd0;
            lat_min_comb_q <= 32'd0;
            lon_min_comb_q <= 32'd0;
            lat_min_x50_q <= 32'd0;
            lon_min_x50_q <= 32'd0;
            lat_min_deg7_q <= 32'd0;
            lon_min_deg7_q <= 32'd0;
            lat_result_q <= 32'd0;
            lon_result_q <= 32'd0;
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

            if (rx_valid || (state >= S_CONV_LAT1)) begin
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
                        lat_deg_raw <= p_deg;
                        lat_min_int_raw <= p_min_int;
                        lat_min_frac_raw <= p_min_frac;
                        lat_min_frac_d_raw <= p_min_frac_d;
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
                            lat_negative <= 1'b1;
                        else if (rx_data == "N" || rx_data == "n")
                            lat_negative <= 1'b0;
                    end
                end

                S_LON: begin
                    if (rx_data == ",") begin
                        lon_deg_raw <= p_deg;
                        lon_min_int_raw <= p_min_int;
                        lon_min_frac_raw <= p_min_frac;
                        lon_min_frac_d_raw <= p_min_frac_d;
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
                            lon_negative <= 1'b1;
                        else if (rx_data == "E" || rx_data == "e")
                            lon_negative <= 1'b0;
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
                        state <= S_CONV_LAT1;
                    end else begin
                        // Bad checksum: drop silently.
                        state <= S_IDLE;
                    end
                end

                S_CONV_LAT1: begin
                    lat_base_q <= lat_deg_raw * 32'd10_000_000;
                    lon_base_q <= lon_deg_raw * 32'd10_000_000;
                    lat_min_base_q <= lat_min_int_raw * 32'd10000;
                    lon_min_base_q <= lon_min_int_raw * 32'd10000;
                    lat_min_pad_q <= frac_to_4(lat_min_frac_raw, lat_min_frac_d_raw);
                    lon_min_pad_q <= frac_to_4(lon_min_frac_raw, lon_min_frac_d_raw);
                    state         <= S_CONV_MID;
                end

                S_CONV_MID: begin
                    lat_min_comb_q <= lat_min_base_q + lat_min_pad_q;
                    lon_min_comb_q <= lon_min_base_q + lon_min_pad_q;
                    state          <= S_CONV_X50;
                end

                S_CONV_X50: begin
                    lat_min_x50_q <= lat_min_comb_q * 32'd50;
                    lon_min_x50_q <= lon_min_comb_q * 32'd50;
                    state          <= S_CONV_LON;
                end

                S_CONV_LON: begin
                    lat_min_deg7_q <= div3(lat_min_x50_q);
                    lon_min_deg7_q <= div3(lon_min_x50_q);
                    state <= S_CONV_OUT;
                end

                S_CONV_OUT: begin
                    lat_result_q <= lat_base_q + lat_min_deg7_q;
                    lon_result_q <= lon_base_q + lon_min_deg7_q;
                    state <= S_CONV_SIGN;
                end

                S_CONV_SIGN: begin
                    lat_deg7  <= lat_negative ?
                        -$signed(lat_result_q) : $signed(lat_result_q);
                    lon_deg7  <= lon_negative ?
                        -$signed(lon_result_q) : $signed(lon_result_q);
                    speed_kn  <= p_speed;
                    utc_time  <= p_utc;
                    fix_valid <= p_status;
                    fix_ready <= 1'b1;
                    state     <= S_IDLE;
                    xor_active <= 1'b0;
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
