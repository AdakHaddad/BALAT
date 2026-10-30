// risk_fsm — conservative road-approach state machine for the demo.
//
// States: INVALID, SAFE, CAUTION, DANGER, COOLDOWN.
// Entering CAUTION or DANGER requires two consecutive qualifying samples.
// Hysteresis is applied on exit. Stale data or an invalid map forces INVALID
// and gates the cue request off immediately.
//
// dist2 is squared distance in cm^2. Threshold parameters are also squared.
// The FSM is a demonstration policy, not a calibrated safety limit.
module risk_fsm #(
    parameter [63:0] CAUTION_ENTER2 = 64'd250000, // 500 cm
    parameter [63:0] CAUTION_EXIT2  = 64'd360000, // 600 cm
    parameter [63:0] DANGER_ENTER2  = 64'd40000,  // 200 cm
    parameter [63:0] DANGER_EXIT2   = 64'd90000   // 300 cm
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        sample_valid,
    input  wire        stale,
    input  wire        map_valid,
    input  wire        cooldown,
    input  wire        approaching,
    input  wire [63:0] dist2,
    output reg  [2:0]  state,
    output wire        cue_req,
    output wire        fault
);

    localparam [2:0] ST_INVALID  = 3'd0;
    localparam [2:0] ST_SAFE     = 3'd1;
    localparam [2:0] ST_CAUTION  = 3'd2;
    localparam [2:0] ST_DANGER   = 3'd3;
    localparam [2:0] ST_COOLDOWN = 3'd4;

    reg [1:0] confirm_cnt;

    assign fault   = stale | ~map_valid;
    assign cue_req = (state == ST_DANGER) & ~stale & map_valid & ~cooldown;

    always @(posedge clk) begin
        if (rst) begin
            state       <= ST_INVALID;
            confirm_cnt <= 2'd0;
        end else if (stale | ~map_valid) begin
            state       <= ST_INVALID;
            confirm_cnt <= 2'd0;
        end else if (sample_valid) begin
            if (cooldown) begin
                state       <= ST_COOLDOWN;
                confirm_cnt <= 2'd0;
            end else begin
                case (state)
                    ST_INVALID: begin
                        state       <= ST_SAFE;
                        confirm_cnt <= 2'd0;
                    end

                    ST_SAFE: begin
                        if ((dist2 <= DANGER_ENTER2) && approaching) begin
                            if (confirm_cnt == 2'd1) begin
                                state       <= ST_DANGER;
                                confirm_cnt <= 2'd0;
                            end else begin
                                confirm_cnt <= confirm_cnt + 2'd1;
                            end
                        end else if ((dist2 <= CAUTION_ENTER2) && approaching) begin
                            if (confirm_cnt == 2'd1) begin
                                state       <= ST_CAUTION;
                                confirm_cnt <= 2'd0;
                            end else begin
                                confirm_cnt <= confirm_cnt + 2'd1;
                            end
                        end else begin
                            confirm_cnt <= 2'd0;
                        end
                    end

                    ST_CAUTION: begin
                        if ((dist2 <= DANGER_ENTER2) && approaching) begin
                            if (confirm_cnt == 2'd1) begin
                                state       <= ST_DANGER;
                                confirm_cnt <= 2'd0;
                            end else begin
                                confirm_cnt <= confirm_cnt + 2'd1;
                            end
                        end else if ((dist2 >= CAUTION_EXIT2) || ~approaching) begin
                            state       <= ST_SAFE;
                            confirm_cnt <= 2'd0;
                        end else begin
                            confirm_cnt <= 2'd0;
                        end
                    end

                    ST_DANGER: begin
                        if (dist2 >= CAUTION_EXIT2) begin
                            state       <= ST_SAFE;
                            confirm_cnt <= 2'd0;
                        end else if (dist2 >= DANGER_EXIT2) begin
                            state       <= ST_CAUTION;
                            confirm_cnt <= 2'd0;
                        end else begin
                            confirm_cnt <= 2'd0;
                        end
                    end

                    ST_COOLDOWN: begin
                        if (!cooldown) begin
                            state       <= ST_SAFE;
                            confirm_cnt <= 2'd0;
                        end
                    end

                    default: begin
                        state       <= ST_INVALID;
                        confirm_cnt <= 2'd0;
                    end
                endcase
            end
        end
    end

endmodule
