from ezhdl import *

class BitToggler(Entity):
	def __init__(self, TOGGLE_PERIOD):
		self.TOGGLE_PERIOD = TOGGLE_PERIOD

		self.clk    = Input(Wire())
		self.rst    = Input(Wire())
		self.toggle = Output(Wire())

		self.counter = Signal(Unsigned().upto(TOGGLE_PERIOD - 1))

	def _run(self):
		s = self

		if posedge(s.clk):
			if (s.counter.now == s.TOGGLE_PERIOD - 1):
				s.counter.nxt <<= 0
				s.toggle.nxt  <<= ~s.toggle.now
			else:
				s.counter.nxt <<= s.counter.nxt + 1

			if s.rst.now:
				s.counter.nxt <<= 0
				s.toggle.nxt  <<= 0
