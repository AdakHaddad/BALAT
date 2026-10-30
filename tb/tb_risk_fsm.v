`timescale 1ns/1ps

module tb_risk_fsm;

    localparam [2:0] ST_INVALID  = 3'd0;
    localparam [2:0] ST_SAFE     = 3'd1;
    localparam [2:0] ST_CAUTION  = 3'd2;
    localparam [2:0] ST_DANGER   = 3'd3;
    localparam [2:0] ST_COOLDOWN = 3'd4;

    reg         clk;
    reg         rst;
    reg         sample_valid;
    reg         stale;
    reg         map_valid;
    reg         cooldown;
    reg         approaching;
    reg  [63:0] dist2;
    wire [2:0]  state;
    wire        cue_req;
    wire        fault;

    risk_fsm dut (
        .clk (clk),
        .rst (rst),
        .sample_valid (sample_valid),
        .stale (stale),
        .map_valid (map_valid),
        .cooldown (cooldown),
        .approaching (approaching),
        .dist2 (dist2),
        .state (state),
        .cue_req (cue_req),
        .fault (fault)
    );

    always #5 clk = ~clk;

    task do_sample(input [63:0] d2, input appr, input st, input mv, input cd);
        begin
            @(negedge clk);
            dist2 = d2;
            approaching = appr;
            stale = st;
            map_valid = mv;
            cooldown = cd;
            sample_valid = 1'b1;
            @(negedge clk);
            sample_valid = 1'b0;
        end
    endtask

    task expect_state(input [2:0] expected);
        begin
            if (state !== expected) begin
                $display("FAIL: expected state %0d, got %0d at time %0t", expected, state, $time);
                $fatal;
            end
        end
    endtask

    initial begin
        clk = 0;
        rst = 1;
        sample_valid = 0;
        stale = 0;
        map_valid = 1;
        cooldown = 0;
        approaching = 0;
        dist2 = 0;

        repeat (3) @(negedge clk);
        rst = 0;
        @(negedge clk);
        expect_state(ST_INVALID);

        do_sample(64'd1000000, 1'b1, 1'b0, 1'b1, 1'b0);
        expect_state(ST_SAFE);

        do_sample(64'd250000, 1'b1, 1'b0, 1'b1, 1'b0);
        expect_state(ST_SAFE);
        do_sample(64'd240100, 1'b1, 1'b0, 1'b1, 1'b0);
        expect_state(ST_CAUTION);

        do_sample(64'd40000, 1'b1, 1'b0, 1'b1, 1'b0);
        expect_state(ST_CAUTION);
        do_sample(64'd36100, 1'b1, 1'b0, 1'b1, 1'b0);
        expect_state(ST_DANGER);
        if (cue_req !== 1'b1) begin
            $display("FAIL: DANGER must request a cue");
            $fatal;
        end

        do_sample(64'd36100, 1'b1, 1'b0, 1'b1, 1'b1);
        expect_state(ST_COOLDOWN);
        if (cue_req !== 1'b0) begin
            $display("FAIL: COOLDOWN must inhibit cue request");
            $fatal;
        end

        do_sample(64'd90000, 1'b0, 1'b0, 1'b1, 1'b0);
        expect_state(ST_SAFE);

        stale = 1'b1;
        @(negedge clk);
        expect_state(ST_INVALID);
        if (fault !== 1'b1) begin
            $display("FAIL: stale must assert fault");
            $fatal;
        end
        stale = 1'b0;
        @(negedge clk);

        do_sample(64'd1000000, 1'b1, 1'b0, 1'b1, 1'b0);
        expect_state(ST_SAFE);

        map_valid = 1'b0;
        @(negedge clk);
        expect_state(ST_INVALID);
        if (fault !== 1'b1) begin
            $display("FAIL: map invalid must assert fault");
            $fatal;
        end

        $display("PASS: risk_fsm");
        $finish;
    end

endmodule
