`timescale 1ns/1ps

// tb_nmea_parser — directed test for the NMEA $xxRMC parser.
//
// Feeds complete sentences byte-by-byte and checks parsed outputs against
// the Python golden model (scripts/golden_nmea.py).

module tb_nmea_parser;

    reg        clk;
    reg        rst;
    reg [7:0]  rx_data;
    reg        rx_valid;

    wire signed [31:0] lat_deg7;
    wire signed [31:0] lon_deg7;
    wire        [15:0] speed_kn;
    wire        [23:0] utc_time;
    wire               fix_valid;
    wire               fix_ready;

    nmea_parser dut (
        .clk       (clk),
        .rst       (rst),
        .rx_data   (rx_data),
        .rx_valid  (rx_valid),
        .lat_deg7  (lat_deg7),
        .lon_deg7  (lon_deg7),
        .speed_kn  (speed_kn),
        .utc_time  (utc_time),
        .fix_valid (fix_valid),
        .fix_ready (fix_ready)
    );

    always #5 clk = ~clk;

    integer fix_count;
    integer error_count;

    // Track fix_ready pulses
    always @(posedge clk) begin
        if (fix_ready)
            fix_count <= fix_count + 1;
    end

    // ---------------------------------------------------------------
    // Task: send one byte (with rx_valid for exactly one cycle)
    // ---------------------------------------------------------------
    task send_byte(input [7:0] b);
        begin
            @(posedge clk);
            #1;
            rx_data  = b;
            rx_valid = 1'b1;
            @(posedge clk);
            #1;
            rx_valid = 1'b0;
            // Wait a couple cycles (simulates UART inter-byte gap)
            @(posedge clk);
            @(posedge clk);
        end
    endtask

    // ---------------------------------------------------------------
    // Sentence buffer
    // ---------------------------------------------------------------
    reg [7:0] sentence [0:127];
    integer   sentence_len;

    task send_sentence;
        integer i;
        begin
            for (i = 0; i < sentence_len; i = i + 1)
                send_byte(sentence[i]);
        end
    endtask

    task fill_sentence;
        input [8*128-1:0] s;
        input integer      len;
        integer i;
        begin
            sentence_len = len;
            for (i = 0; i < len; i = i + 1)
                sentence[i] = s[(len-1-i)*8 +: 8];
        end
    endtask

    // ---------------------------------------------------------------
    // Task: wait for fix_ready pulse (timeout after N cycles)
    // Returns 1 if pulse seen, 0 if timeout.
    // ---------------------------------------------------------------
    integer saw_fix;
    task wait_fix_ready;
        input integer timeout_cycles;
        integer cnt;
        begin
            saw_fix = 0;
            for (cnt = 0; cnt < timeout_cycles && !saw_fix; cnt = cnt + 1) begin
                @(posedge clk);
                if (fix_ready) saw_fix = 1;
            end
        end
    endtask

    // ---------------------------------------------------------------
    // Task: send sentence and check outputs
    // ---------------------------------------------------------------
    task test_sentence;
        input [8*64-1:0]   desc;
        input [8*128-1:0]  sent;
        input integer       slen;
        input signed [31:0] exp_lat;
        input signed [31:0] exp_lon;
        input [15:0]        exp_speed;
        input [23:0]        exp_utc;
        input               exp_valid;
        input               expect_fix;
        begin
            fill_sentence(sent, slen);
            send_sentence;
            // Give a few cycles for fix_ready to propagate
            repeat (5) @(posedge clk);

            if (expect_fix) begin
                // Check latched outputs
                if (lat_deg7 !== exp_lat) begin
                    $display("FAIL %0s: lat_deg7 = %0d, expected %0d", desc, lat_deg7, exp_lat);
                    error_count = error_count + 1;
                end
                if (lon_deg7 !== exp_lon) begin
                    $display("FAIL %0s: lon_deg7 = %0d, expected %0d", desc, lon_deg7, exp_lon);
                    error_count = error_count + 1;
                end
                if (speed_kn !== exp_speed) begin
                    $display("FAIL %0s: speed_kn = %0d, expected %0d", desc, speed_kn, exp_speed);
                    error_count = error_count + 1;
                end
                if (utc_time !== exp_utc) begin
                    $display("FAIL %0s: utc_time = 0x%06X, expected 0x%06X", desc, utc_time, exp_utc);
                    error_count = error_count + 1;
                end
                if (fix_valid !== exp_valid) begin
                    $display("FAIL %0s: fix_valid = %0b, expected %0b", desc, fix_valid, exp_valid);
                    error_count = error_count + 1;
                end
            end
        end
    endtask

    // ---------------------------------------------------------------
    // Task: send sentence and verify NO fix_ready fires
    // ---------------------------------------------------------------
    integer pre_fix_count;
    task test_no_fix;
        input [8*64-1:0]  desc;
        input [8*128-1:0] sent;
        input integer      slen;
        begin
            pre_fix_count = fix_count;
            fill_sentence(sent, slen);
            send_sentence;
            repeat (10) @(posedge clk);
            if (fix_count !== pre_fix_count) begin
                $display("FAIL %0s: fix_ready fired but should not have", desc);
                error_count = error_count + 1;
            end
        end
    endtask

    // ---------------------------------------------------------------
    // Main test sequence
    // ---------------------------------------------------------------
    initial begin
        clk         = 0;
        rst         = 1;
        rx_data     = 8'd0;
        rx_valid    = 1'b0;
        fix_count   = 0;
        error_count = 0;

        repeat (10) @(posedge clk);
        rst = 1'b0;
        repeat (5) @(posedge clk);

        // Test 1: Basic GPRMC, north-east
        // $GPRMC,123519.00,A,4807.0380,N,01131.0000,E,0.5,0.0,231003,,A*7B
        test_sentence("test1_GPRMC_NE",
            "$GPRMC,123519.00,A,4807.0380,N,01131.0000,E,0.5,0.0,231003,,A*7B", 64,
            32'sd481173000,   // lat
            32'sd115166667,   // lon
            16'd50,           // speed 0.50 kn
            24'h123519,       // utc
            1'b1,             // fix_valid
            1'b1              // expect_fix
        );

        // Test 2: GNRMC, south-west
        // $GNRMC,091500.00,A,3349.8000,S,07051.0000,W,12.3,0.0,231003,,A*5B
        test_sentence("test2_GNRMC_SW",
            "$GNRMC,091500.00,A,3349.8000,S,07051.0000,W,12.3,0.0,231003,,A*5B", 65,
            -32'sd338300000,  // lat
            -32'sd708500000,  // lon
            16'd1230,         // speed 12.30 kn
            24'h091500,       // utc
            1'b1,
            1'b1
        );

        // Test 3: Void fix (status V)
        // $GPRMC,000000.00,V,0000.0000,N,00000.0000,E,0.0,0.0,231003,,A*66
        test_sentence("test3_void",
            "$GPRMC,000000.00,V,0000.0000,N,00000.0000,E,0.0,0.0,231003,,A*66", 64,
            32'sd0,
            32'sd0,
            16'd0,
            24'h000000,
            1'b0,             // fix_valid = 0 (void)
            1'b1
        );

        // Test 4: High latitude/longitude
        // $GNRMC,235959.00,A,8959.9999,N,17959.9999,E,99.9,0.0,231003,,A*59
        test_sentence("test4_high",
            "$GNRMC,235959.00,A,8959.9999,N,17959.9999,E,99.9,0.0,231003,,A*59", 65,
            32'sd899999983,
            32'sd1799999983,
            16'd9990,
            24'h235959,
            1'b1,
            1'b1
        );

        // Test 5: Zero coordinates
        // $GPRMC,120000.00,A,0000.0000,N,00000.0000,E,0.0,0.0,231003,,A*72
        test_sentence("test5_zero",
            "$GPRMC,120000.00,A,0000.0000,N,00000.0000,E,0.0,0.0,231003,,A*72", 64,
            32'sd0,
            32'sd0,
            16'd0,
            24'h120000,
            1'b1,
            1'b1
        );

        // Test 6: Bad checksum — should NOT produce fix_ready
        test_no_fix("test6_bad_cksum",
            "$GPRMC,120000.00,A,4807.0380,N,01131.0000,E,0.0,0.0,231003,,A*00", 64);

        // Test 7: Non-RMC sentence — should be ignored
        test_no_fix("test7_non_rmc",
            "$GPGGA,120000.00,4807.0380,N,01131.0000,E,1,08,0.9,545.4,M*47", 63);

        // Test 8: Back-to-back sentences — second should update
        test_sentence("test8_second",
            "$GPRMC,180000.00,A,5100.0000,N,00300.0000,W,5.5,0.0,231003,,A*6D", 64,
            32'sd510000000,
            -32'sd30000000,
            16'd550,
            24'h180000,
            1'b1,
            1'b1
        );

        // ---- Summary ----
        if (error_count == 0)
            $display("PASS: nmea_parser (%0d fixes parsed)", fix_count);
        else
            $display("FAIL: nmea_parser — %0d errors", error_count);

        $finish;
    end

endmodule
