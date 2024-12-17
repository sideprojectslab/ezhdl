module BitToggler #(
	parameter integer TOGGLE_PERIOD = 10
) (
	output reg toggle,
	input wire clk,
	input wire rst
);
	reg [31:0] counter;
	always @(posedge clk) begin
		if (counter == TOGGLE_PERIOD - 1) begin
			counter <= 0;
			toggle <= ~toggle;
		end else begin
			counter <= counter + 1;
		end
		if (rst) begin
			counter <= 0;
			toggle <= 0;
		end

	end

endmodule
