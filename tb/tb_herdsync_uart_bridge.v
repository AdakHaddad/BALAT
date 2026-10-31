`timescale 1ns/1ps

module tb_herdsync_uart_bridge;

    localparam integer CLKS_PER_BIT = 10;
    localparam integer FRAME_LEN    = 43;

    reg         clk;
    reg         rst;
    reg         sample_tick;
    reg         sample_valid;
    reg         stale;
    reg  [2:0]  risk;
    reg  signed [31:0] x_cm;
    reg  signed [31:0] y_cm;
    reg         host_rx;
    wire        uart_tx;
    wire        tx_busy;
    wire [15:0] frames_sent;
    wire [15:0] frames_received;
    wire [15:0] crc_errors;
    wire [15:0] tx_drops;
    wire [15:0] rx_errors;
    wire [31:0] last_peer_id;
    wire [31:0] last_peer_seq;
    wire [31:0] last_peer_fix_s;
    wire [2:0]  last_peer_risk;
    wire        peer_seen;

    reg [7:0] frame [0:FRAME_LEN-1];
    reg [7:0] host_frame [0:19];

    herdsync_uart_bridge #(
        .CLK_HZ    (100),
        .BAUD      (10),
        .ORIGIN_ID (32'd1),
        .EPOCH     (16'd1)
    ) dut (
        .clk             (clk),
        .rst             (rst),
        .sample_tick     (sample_tick),
        .sample_valid    (sample_valid),
        .stale           (stale),
        .risk            (risk),
        .x_cm            (x_cm),
        .y_cm            (y_cm),
        .uart_rx         (host_rx),
        .uart_tx         (uart_tx),
        .tx_busy         (tx_busy),
        .frames_sent     (frames_sent),
        .frames_received (frames_received),
        .crc_errors      (crc_errors),
        .tx_drops        (tx_drops),
        .rx_errors       (rx_errors),
        .last_peer_id    (last_peer_id),
        .last_peer_seq   (last_peer_seq),
        .last_peer_fix_s (last_peer_fix_s),
        .last_peer_risk  (last_peer_risk),
        .peer_seen       (peer_seen)
    );

    always #5 clk = ~clk;

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

    function [31:0] frame_u32;
        input integer offset;
        begin
            frame_u32 = {
                frame[offset],
                frame[offset + 1],
                frame[offset + 2],
                frame[offset + 3]
            };
        end
    endfunction

    task recv_byte(output [7:0] value);
        integer i;
        begin
            value = 8'd0;
            @(negedge uart_tx);
            repeat (CLKS_PER_BIT / 2) @(posedge clk);
            if (uart_tx !== 1'b0) begin
                $display("FAIL: UART start bit not low at time %0t", $time);
                $fatal;
            end
            for (i = 0; i < 8; i = i + 1) begin
                repeat (CLKS_PER_BIT) @(posedge clk);
                value[i] = uart_tx;
            end
            repeat (CLKS_PER_BIT) @(posedge clk);
            if (uart_tx !== 1'b1) begin
                $display("FAIL: UART stop bit not high at time %0t", $time);
                $fatal;
            end
        end
    endtask

    task send_byte(input [7:0] value);
        integer i;
        begin
            @(negedge clk);
            host_rx = 1'b0;
            repeat (CLKS_PER_BIT) @(negedge clk);
            for (i = 0; i < 8; i = i + 1) begin
                host_rx = value[i];
                repeat (CLKS_PER_BIT) @(negedge clk);
            end
            host_rx = 1'b1;
            repeat (CLKS_PER_BIT) @(negedge clk);
        end
    endtask

    task send_host_frame(input integer length);
        integer i;
        begin
            for (i = 0; i < length; i = i + 1)
                send_byte(host_frame[i]);
        end
    endtask

    initial begin
        $dumpfile("build/sim/tb_herdsync_uart_bridge.vcd");
        $dumpvars(0, tb_herdsync_uart_bridge);

        clk = 0;
        rst = 1;
        sample_tick = 0;
        sample_valid = 1;
        stale = 0;
        risk = 3'd4;
        x_cm = 32'sd1234;
        y_cm = -32'sd567;
        host_rx = 1'b1;

        repeat (3) @(negedge clk);
        rst = 0;
        repeat (3) @(negedge clk);

        @(negedge clk);
        sample_tick = 1'b1;
        @(negedge clk);
        sample_tick = 1'b0;

        repeat (2) @(negedge clk);
        if (dut.tx_state == 3'd0) begin
            $display("FAIL: bridge did not start building a frame");
            $fatal;
        end

        @(negedge clk);
        sample_tick = 1'b1;
        @(negedge clk);
        sample_tick = 1'b0;
        @(negedge clk);
        if (tx_drops !== 16'd1) begin
            $display("FAIL: expected one TX drop, got %0d", tx_drops);
            $fatal;
        end

        begin : receive_record
            integer i;
            for (i = 0; i < FRAME_LEN; i = i + 1)
                recv_byte(frame[i]);
        end

        if ((frame[0] !== 8'hAA) || (frame[1] !== 8'h55)) begin
            $display("FAIL: bad sync");
            $fatal;
        end
        if ((frame[2] !== 8'h01) || (frame[3] !== 8'h01) || (frame[4] !== 8'd36)) begin
            $display("FAIL: bad header version/type/length");
            $fatal;
        end
        if (frame[5] !== 8'h01) begin
            $display("FAIL: bad record schema");
            $fatal;
        end
        if (frame[6] !== 8'h00) begin
            $display("FAIL: routine record must have priority 0");
            $fatal;
        end
        if (frame_u32(9) !== 32'd1) begin
            $display("FAIL: bad origin id");
            $fatal;
        end
        if (frame_u32(13) !== 32'd1) begin
            $display("FAIL: bad sequence number");
            $fatal;
        end
        if (frame_u32(21) !== 32'd1234) begin
            $display("FAIL: bad x coordinate");
            $fatal;
        end
        if (frame_u32(25) !== 32'hFFFFFDC9) begin
            $display("FAIL: bad y coordinate");
            $fatal;
        end
        if (frame[29] !== 8'd100) begin
            $display("FAIL: bad quality");
            $fatal;
        end
        if ({frame[30], frame[31]} !== 16'd3700) begin
            $display("FAIL: bad battery");
            $fatal;
        end
        if (frame[32] !== 8'd4) begin
            $display("FAIL: bad risk (cooldown must not truncate)");
            $fatal;
        end
        if ({frame[33], frame[34], frame[35], frame[36],
             frame[37], frame[38], frame[39], frame[40]} !== 64'd0) begin
            $display("FAIL: bench record tag must be zero");
            $fatal;
        end

        begin : check_crc
            integer i;
            reg [15:0] crc;
            crc = 16'hFFFF;
            for (i = 2; i <= 40; i = i + 1)
                crc = crc16_byte(crc, frame[i]);
            if ({frame[41], frame[42]} !== crc) begin
                $display("FAIL: bad record CRC");
                $fatal;
            end
        end

        while (tx_busy) @(posedge clk);
        repeat (3) @(negedge clk);
        if (frames_sent !== 16'd1) begin
            $display("FAIL: expected one frame sent, got %0d", frames_sent);
            $fatal;
        end

        host_frame[0] = 8'hAA;
        host_frame[1] = 8'h55;
        host_frame[2] = 8'h01;
        host_frame[3] = 8'h02;
        host_frame[4] = 8'd13;
        host_frame[5] = 8'd0;
        host_frame[6] = 8'd0;
        host_frame[7] = 8'd0;
        host_frame[8] = 8'd7;
        host_frame[9] = 8'd0;
        host_frame[10] = 8'd0;
        host_frame[11] = 8'd0;
        host_frame[12] = 8'd42;
        host_frame[13] = 8'd0;
        host_frame[14] = 8'd0;
        host_frame[15] = 8'd0;
        host_frame[16] = 8'd123;
        host_frame[17] = 8'd1;
        begin : make_peer_crc
            integer i;
            reg [15:0] crc;
            crc = 16'hFFFF;
            for (i = 2; i <= 17; i = i + 1)
                crc = crc16_byte(crc, host_frame[i]);
            host_frame[18] = crc[15:8];
            host_frame[19] = crc[7:0];
        end

        send_host_frame(20);
        repeat (5) @(negedge clk);
        if (!peer_seen || (last_peer_id !== 32'd7) || (last_peer_seq !== 32'd42) ||
            (last_peer_fix_s !== 32'd123) || (last_peer_risk !== 2'd1)) begin
            $display("FAIL: peer summary not decoded");
            $fatal;
        end
        if (frames_received !== 16'd1) begin
            $display("FAIL: expected one host frame received, got %0d", frames_received);
            $fatal;
        end

        host_frame[19] = host_frame[19] ^ 8'hFF;
        send_host_frame(20);
        repeat (5) @(negedge clk);
        if (crc_errors !== 16'd1) begin
            $display("FAIL: bad host CRC must increment crc_errors, got %0d", crc_errors);
            $fatal;
        end
        if (frames_received !== 16'd1) begin
            $display("FAIL: bad CRC frame must not increment frames_received");
            $fatal;
        end

        rst = 1;
        @(negedge clk);
        if (frames_sent !== 16'd0 || peer_seen !== 1'b0) begin
            $display("FAIL: reset must clear bridge counters");
            $fatal;
        end

        $display("PASS: herdsync_uart_bridge");
        $finish;
    end

endmodule
