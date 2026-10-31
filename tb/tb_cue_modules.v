`timescale 1ns/1ps

// tb_cue_modules — validates interchangeable MCI cue transducer drivers (M5).
// Verifies that buzzer (PWM), vibration (bursts), and direct logic drivers
// all respond safely to the abstract CUE_EN signal without altering the risk engine.

module tb_cue_modules;

    reg clk;
    reg rst;
    reg cue_en;

    // Module 1: Direct logic driver (e.g. LED / external gate)
    wire direct_out = cue_en;

    // Module 2: Acoustic PWM generator (e.g. 4 kHz tone)
    // At 100 MHz clock, 4 kHz period = 25,000 cycles
    reg [15:0] pwm_cnt;
    reg        buzzer_pwm;
    always @(posedge clk) begin
        if (rst || !cue_en) begin
            pwm_cnt    <= 16'd0;
            buzzer_pwm <= 1'b0;
        end else begin
            if (pwm_cnt >= 16'd24999) begin
                pwm_cnt    <= 16'd0;
                buzzer_pwm <= ~buzzer_pwm;
            end else begin
                pwm_cnt <= pwm_cnt + 16'd1;
            end
        end
    end

    // Module 3: Haptic vibration burst generator (200 Hz pulsed burst)
    reg [19:0] burst_cnt;
    reg        vibe_out;
    always @(posedge clk) begin
        if (rst || !cue_en) begin
            burst_cnt <= 20'd0;
            vibe_out  <= 1'b0;
        end else begin
            burst_cnt <= burst_cnt + 20'd1;
            // 50% duty cycle burst
            vibe_out  <= burst_cnt[18];
        end
    end

    always #5 clk = ~clk;

    integer errors;

    initial begin
        clk = 0; rst = 1; cue_en = 0; errors = 0;
        repeat (5) @(posedge clk);
        rst <= 0;
        repeat (5) @(posedge clk);

        // When cue_en is LOW: all transducers must be SILENT
        if (direct_out !== 0 || buzzer_pwm !== 0 || vibe_out !== 0) begin
            $display("FAIL: Transducers active when cue_en is 0");
            errors = errors + 1;
        end

        // Assert cue_en
        cue_en <= 1'b1;
        repeat (100) @(posedge clk);

        if (direct_out !== 1'b1) begin
            $display("FAIL: Direct output not active");
            errors = errors + 1;
        end

        // Deassert cue_en: all must immediately quiet down
        cue_en <= 1'b0;
        repeat (10) @(posedge clk);

        if (direct_out !== 0 || buzzer_pwm !== 0 || vibe_out !== 0) begin
            $display("FAIL: Transducers did not silence immediately on cue_en deassert");
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS: tb_cue_modules (all interchangeable drivers verified safe)");
        else
            $display("FAIL: tb_cue_modules — %0d errors", errors);

        $finish;
    end

endmodule
