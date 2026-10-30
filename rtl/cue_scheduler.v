// cue_scheduler — bounded cue pulse and mandatory cooldown.
//
// The scheduler is advanced by a sample-rate tick. A request starts one pulse.
// The pulse is limited to MAX_ON_TICKS and is terminated early when request
// drops or enable is removed. Any terminated pulse starts a COOLDOWN_TICKS
// inhibit interval. Reset forces the cue output inactive.
//
// Timing parameters are sample ticks, not milliseconds; the top-level demo
// uses a 10 Hz tick so 5 ticks = 0.5 s and 30 ticks = 3 s.
module cue_scheduler #(
    parameter integer MAX_ON_TICKS   = 5,
    parameter integer COOLDOWN_TICKS = 30
) (
    input  wire clk,
    input  wire rst,
    input  wire tick,
    input  wire enable,
    input  wire request,
    output reg  cue_en,
    output reg  cooldown
);

    localparam [15:0] ON_LAST   = (MAX_ON_TICKS - 1) & 16'hFFFF;
    localparam [15:0] COOL_LAST = (COOLDOWN_TICKS - 1) & 16'hFFFF;

    reg [15:0] on_count;
    reg [15:0] cool_count;

    always @(posedge clk) begin
        if (rst) begin
            cue_en     <= 1'b0;
            cooldown   <= 1'b0;
            on_count   <= 16'd0;
            cool_count <= 16'd0;
        end else if (tick) begin
            if (!enable) begin
                cue_en     <= 1'b0;
                cooldown   <= 1'b0;
                on_count   <= 16'd0;
                cool_count <= 16'd0;
            end else if (cooldown) begin
                cue_en <= 1'b0;
                if (cool_count >= COOL_LAST) begin
                    cooldown   <= 1'b0;
                    cool_count <= 16'd0;
                end else begin
                    cool_count <= cool_count + 16'd1;
                end
            end else if (cue_en) begin
                if (!request || (on_count >= ON_LAST)) begin
                    cue_en     <= 1'b0;
                    cooldown   <= 1'b1;
                    on_count   <= 16'd0;
                    cool_count <= 16'd0;
                end else begin
                    on_count <= on_count + 16'd1;
                end
            end else if (request) begin
                cue_en   <= 1'b1;
                on_count <= 16'd0;
            end
        end
    end

endmodule
