module BitToggler_tb;

	reg clk;            // Clock signal
	reg rst;            // Reset signal
	wire toggle;   // Output from the DUT

	// Instantiate the BitToggler with a toggle period of 5
	BitToggler #(
		.TOGGLE_PERIOD(5)
	) dut (
		.toggle(toggle),
		.clk(clk),
		.rst(rst)
	);

	// Generate clock signal with a period of 10 time units
	initial clk = 0;
	always #5 clk = ~clk;

	// Test stimulus
	initial begin
		$monitor("Time=%0t, toggle=%b", $time, toggle);

		rst = 1; #10;   // Assert reset for 10 time units
		rst = 0;        // Deassert reset

		#100;           // Run simulation for 100 time units
		$finish;        // End simulation
	end

endmodule
