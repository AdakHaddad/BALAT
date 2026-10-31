// herdsync_uart_bridge — Basys 3 bench bridge to a host over USB-UART.
//
// On each sample_tick the bridge latches a 36-byte unsigned record and emits a
// framed UART record. It also accepts framed host records or peer summaries and
// exposes counters for LEDs. This is a bench transport, not an authenticated
// production link and not part of the v0.1 cue path.
//
// Frame: AA 55 | version | type | length | payload | CRC16
// CRC: CRC-16/CCITT-FALSE over version, type, length, and payload.
// Record type 0x01 payload: 28-byte POC record plus eight zero tag bytes.
// Peer type 0x02 payload: peer_id u32, seq u32, fix_time_s u32, risk u8.
module herdsync_uart_bridge #(
    parameter integer CLK_HZ    = 100_000_000,
    parameter integer BAUD      = 115200,
    parameter [31:0]  ORIGIN_ID = 32'd1,
    parameter [15:0]  EPOCH     = 16'd1
) (
    input  wire               clk,
    input  wire               rst,
    input  wire               sample_tick,
    input  wire               sample_valid,
    input  wire               stale,
    input  wire [2:0]         risk,
    input  wire signed [31:0] x_cm,
    input  wire signed [31:0] y_cm,
    input  wire               uart_rx,
    output wire               uart_tx,
    output wire               tx_busy,
    output reg  [15:0]        frames_sent,
    output reg  [15:0]        frames_received,
    output reg  [15:0]        crc_errors,
    output reg  [15:0]        tx_drops,
    output reg  [15:0]        rx_errors,
    output reg  [31:0]        last_peer_id,
    output reg  [31:0]        last_peer_seq,
    output reg  [31:0]        last_peer_fix_s,
    output reg  [2:0]         last_peer_risk,
    output reg                peer_seen
);

    localparam [7:0] VERSION_BYTE = 8'h01;
    localparam [7:0] TYPE_RECORD  = 8'h01;
    localparam [7:0] TYPE_PEER    = 8'h02;
    localparam [7:0] RECORD_LEN   = 8'd36;
    localparam [6:0] FRAME_LEN    = 7'd43;

    localparam [2:0] S_IDLE  = 3'd0;
    localparam [2:0] S_BUILD = 3'd1;
    localparam [2:0] S_LOAD  = 3'd2;
    localparam [2:0] S_SEND  = 3'd3;
    localparam [2:0] S_WAIT  = 3'd4;

    localparam [2:0] R_SYNC0  = 3'd0;
    localparam [2:0] R_SYNC1  = 3'd1;
    localparam [2:0] R_VER    = 3'd2;
    localparam [2:0] R_TYPE   = 3'd3;
    localparam [2:0] R_LEN    = 3'd4;
    localparam [2:0] R_PAYLOAD= 3'd5;
    localparam [2:0] R_CRC_HI = 3'd6;
    localparam [2:0] R_CRC_LO = 3'd7;

    reg [2:0]  tx_state;
    reg [6:0]  build_index;
    reg [6:0]  tx_index;
    reg [15:0] crc;
    reg [7:0]  frame_buf [0:42];
    reg        uart_send;
    reg [7:0]  uart_data;

    reg [31:0] rec_seq;
    reg [31:0] rec_fix_s;
    reg [31:0] rec_x;
    reg [31:0] rec_y;
    reg [7:0]  rec_quality;
    reg [7:0]  rec_priority;
    reg [2:0]  rec_risk;
    reg [3:0]  sample_div;
    reg [31:0] seconds;

    reg [2:0]  rx_state;
    reg [7:0]  rx_type;
    reg [7:0]  rx_len;
    reg [6:0]  rx_index;
    reg [15:0] rx_crc;
    reg [15:0] rx_crc_hi;
    reg [7:0]  rx_buf [0:63];

    wire [7:0] uart_rx_data;
    wire       uart_rx_valid;
    wire       uart_rx_error;

    uart_tx #(
        .CLK_HZ (CLK_HZ),
        .BAUD   (BAUD)
    ) u_uart_tx (
        .clk  (clk),
        .rst  (rst),
        .send (uart_send),
        .data (uart_data),
        .tx   (uart_tx),
        .busy (tx_busy)
    );

    uart_rx #(
        .CLK_HZ (CLK_HZ),
        .BAUD   (BAUD)
    ) u_uart_rx (
        .clk   (clk),
        .rst   (rst),
        .rx    (uart_rx),
        .data  (uart_rx_data),
        .valid (uart_rx_valid),
        .error (uart_rx_error)
    );

    function [15:0] crc16_byte;
        input [15:0] crc_in;
        input [7:0]  data_in;
        integer i;
        reg [15:0] c;
        begin
            c = crc_in ^ {data_in, 8'h00};
            for (i = 0; i < 8; i = i + 1) begin
                if (c[15])
                    c = (c << 1) ^ 16'h1021;
                else
                    c = c << 1;
            end
            crc16_byte = c;
        end
    endfunction

    function [7:0] header_byte;
        input [2:0] index;
        begin
            case (index)
                3'd0: header_byte = 8'hAA;
                3'd1: header_byte = 8'h55;
                3'd2: header_byte = VERSION_BYTE;
                3'd3: header_byte = TYPE_RECORD;
                3'd4: header_byte = RECORD_LEN;
                default: header_byte = 8'h00;
            endcase
        end
    endfunction

    function [7:0] record_byte;
        input [5:0] index;
        begin
            case (index)
                6'd0:  record_byte = VERSION_BYTE;
                6'd1:  record_byte = rec_priority;
                6'd2:  record_byte = EPOCH[15:8];
                6'd3:  record_byte = EPOCH[7:0];
                6'd4:  record_byte = ORIGIN_ID[31:24];
                6'd5:  record_byte = ORIGIN_ID[23:16];
                6'd6:  record_byte = ORIGIN_ID[15:8];
                6'd7:  record_byte = ORIGIN_ID[7:0];
                6'd8:  record_byte = rec_seq[31:24];
                6'd9:  record_byte = rec_seq[23:16];
                6'd10: record_byte = rec_seq[15:8];
                6'd11: record_byte = rec_seq[7:0];
                6'd12: record_byte = rec_fix_s[31:24];
                6'd13: record_byte = rec_fix_s[23:16];
                6'd14: record_byte = rec_fix_s[15:8];
                6'd15: record_byte = rec_fix_s[7:0];
                6'd16: record_byte = rec_x[31:24];
                6'd17: record_byte = rec_x[23:16];
                6'd18: record_byte = rec_x[15:8];
                6'd19: record_byte = rec_x[7:0];
                6'd20: record_byte = rec_y[31:24];
                6'd21: record_byte = rec_y[23:16];
                6'd22: record_byte = rec_y[15:8];
                6'd23: record_byte = rec_y[7:0];
                6'd24: record_byte = rec_quality;
                6'd25: record_byte = 16'd3700 >> 8;
                6'd26: record_byte = 16'd3700 & 8'hFF;
                6'd27: record_byte = {5'd0, rec_risk};
                6'd28: record_byte = 8'h00;
                6'd29: record_byte = 8'h00;
                6'd30: record_byte = 8'h00;
                6'd31: record_byte = 8'h00;
                6'd32: record_byte = 8'h00;
                6'd33: record_byte = 8'h00;
                6'd34: record_byte = 8'h00;
                6'd35: record_byte = 8'h00;
                default: record_byte = 8'h00;
            endcase
        end
    endfunction

    always @(posedge clk) begin
        if (rst) begin
            tx_state      <= S_IDLE;
            build_index   <= 7'd0;
            tx_index      <= 7'd0;
            crc           <= 16'hFFFF;
            uart_send     <= 1'b0;
            uart_data     <= 8'd0;
            rec_seq       <= 32'd0;
            rec_fix_s     <= 32'd0;
            rec_x         <= 32'd0;
            rec_y         <= 32'd0;
            rec_quality   <= 8'd0;
            rec_priority  <= 8'd0;
            rec_risk      <= 2'd0;
            sample_div    <= 4'd0;
            seconds       <= 32'd0;
            frames_sent   <= 16'd0;
            frames_received <= 16'd0;
            crc_errors    <= 16'd0;
            tx_drops      <= 16'd0;
            rx_errors     <= 16'd0;
            last_peer_id  <= 32'd0;
            last_peer_seq <= 32'd0;
            last_peer_fix_s <= 32'd0;
            last_peer_risk <= 3'd0;
            peer_seen     <= 1'b0;
            rx_state      <= R_SYNC0;
            rx_type       <= 8'd0;
            rx_len        <= 8'd0;
            rx_index      <= 7'd0;
            rx_crc        <= 16'hFFFF;
            rx_crc_hi     <= 16'd0;
        end else begin
            uart_send <= 1'b0;

            if (sample_tick) begin
                if (tx_state == S_IDLE) begin
                    rec_seq      <= rec_seq + 32'd1;
                    rec_x        <= x_cm;
                    rec_y        <= y_cm;
                    rec_quality  <= (sample_valid && !stale) ? 8'd100 : 8'd0;
                    rec_priority <= (risk == 3'd3) ? 8'd1 : 8'd0;
                    rec_risk     <= risk;
                    rec_fix_s    <= (sample_div == 4'd9) ? (seconds + 32'd1) : seconds;
                    tx_state     <= S_BUILD;
                    build_index  <= 7'd0;
                    crc          <= 16'hFFFF;
                end else begin
                    tx_drops <= tx_drops + 16'd1;
                end

                if (sample_div == 4'd9) begin
                    sample_div <= 4'd0;
                    seconds    <= seconds + 32'd1;
                end else begin
                    sample_div <= sample_div + 4'd1;
                end
            end

            case (tx_state)
                S_IDLE: begin
                    uart_send <= 1'b0;
                end

                S_BUILD: begin
                    if (build_index < 7'd5) begin
                        frame_buf[build_index] <= header_byte(build_index[2:0]);
                        if (build_index >= 7'd2) begin
                            crc <= crc16_byte(crc, header_byte(build_index[2:0]));
                        end
                        build_index <= build_index + 7'd1;
                    end else if (build_index < 7'd41) begin
                        frame_buf[build_index] <= record_byte(build_index[5:0] - 6'd5);
                        crc <= crc16_byte(crc, record_byte(build_index[5:0] - 6'd5));
                        build_index <= build_index + 7'd1;
                    end else if (build_index == 7'd41) begin
                        frame_buf[41] <= crc[15:8];
                        build_index <= 7'd42;
                    end else begin
                        frame_buf[42] <= crc[7:0];
                        build_index  <= 7'd0;
                        tx_index     <= 7'd0;
                        tx_state     <= S_LOAD;
                    end
                end

                S_LOAD: begin
                    if (!tx_busy) begin
                        if (tx_index < FRAME_LEN) begin
                            uart_data <= frame_buf[tx_index];
                            uart_send <= 1'b1;
                            tx_state  <= S_SEND;
                        end else begin
                            frames_sent <= frames_sent + 16'd1;
                            tx_state    <= S_IDLE;
                        end
                    end
                end

                S_SEND: begin
                    uart_send <= 1'b0;
                    if (tx_busy) begin
                        tx_state <= S_WAIT;
                    end
                end

                S_WAIT: begin
                    if (!tx_busy) begin
                        tx_index <= tx_index + 7'd1;
                        tx_state <= S_LOAD;
                    end
                end

                default: begin
                    tx_state <= S_IDLE;
                end
            endcase

            if (uart_rx_valid) begin
                case (rx_state)
                    R_SYNC0: begin
                        if (uart_rx_data == 8'hAA) begin
                            rx_state <= R_SYNC1;
                        end
                    end

                    R_SYNC1: begin
                        if (uart_rx_data == 8'h55) begin
                            rx_state <= R_VER;
                        end else if (uart_rx_data != 8'hAA) begin
                            rx_state <= R_SYNC0;
                        end
                    end

                    R_VER: begin
                        if (uart_rx_data == VERSION_BYTE) begin
                            rx_crc   <= crc16_byte(16'hFFFF, uart_rx_data);
                            rx_state <= R_TYPE;
                        end else begin
                            rx_state <= R_SYNC0;
                        end
                    end

                    R_TYPE: begin
                        rx_type  <= uart_rx_data;
                        rx_crc   <= crc16_byte(rx_crc, uart_rx_data);
                        rx_state <= R_LEN;
                    end

                    R_LEN: begin
                        if (uart_rx_data <= 8'd64) begin
                            rx_len   <= uart_rx_data;
                            rx_index <= 7'd0;
                            rx_crc   <= crc16_byte(rx_crc, uart_rx_data);
                            if (uart_rx_data == 8'd0)
                                rx_state <= R_CRC_HI;
                            else
                                rx_state <= R_PAYLOAD;
                        end else begin
                            rx_state <= R_SYNC0;
                        end
                    end

                    R_PAYLOAD: begin
                        rx_buf[rx_index] <= uart_rx_data;
                        rx_crc <= crc16_byte(rx_crc, uart_rx_data);
                        if (rx_index == (rx_len - 8'd1)) begin
                            rx_state <= R_CRC_HI;
                        end else begin
                            rx_index <= rx_index + 7'd1;
                        end
                    end

                    R_CRC_HI: begin
                        rx_crc_hi <= uart_rx_data;
                        rx_state  <= R_CRC_LO;
                    end

                    R_CRC_LO: begin
                        if ({rx_crc_hi, uart_rx_data} == rx_crc) begin
                            frames_received <= frames_received + 16'd1;
                            if (rx_type == TYPE_PEER && rx_len >= 8'd13) begin
                                last_peer_id <= {
                                    rx_buf[0], rx_buf[1], rx_buf[2], rx_buf[3]
                                };
                                last_peer_seq <= {
                                    rx_buf[4], rx_buf[5], rx_buf[6], rx_buf[7]
                                };
                                last_peer_fix_s <= {
                                    rx_buf[8], rx_buf[9], rx_buf[10], rx_buf[11]
                                };
                                last_peer_risk <= rx_buf[12][2:0];
                                peer_seen <= 1'b1;
                            end else if (rx_type == TYPE_RECORD && rx_len >= 8'd36) begin
                                last_peer_id <= {
                                    rx_buf[4], rx_buf[5], rx_buf[6], rx_buf[7]
                                };
                                last_peer_seq <= {
                                    rx_buf[8], rx_buf[9], rx_buf[10], rx_buf[11]
                                };
                                last_peer_fix_s <= {
                                    rx_buf[12], rx_buf[13], rx_buf[14], rx_buf[15]
                                };
                                last_peer_risk <= rx_buf[27][2:0];
                                peer_seen <= 1'b1;
                            end
                        end else begin
                            crc_errors <= crc_errors + 16'd1;
                        end
                        rx_state <= R_SYNC0;
                    end

                    default: begin
                        rx_state <= R_SYNC0;
                    end
                endcase
            end

            if (uart_rx_error) begin
                rx_errors <= rx_errors + 16'd1;
            end
        end
    end

endmodule
