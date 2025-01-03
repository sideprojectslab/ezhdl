# ---------------------------------------------------------------------------- #
#          .XXXXXXXXXXXXXXXX.  .XXXXXXXXXXXXXXXX.  .XX.                        #
#          XXXXXXXXXXXXXXXXX'  XXXXXXXXXXXXXXXXXX  XXXX                        #
#          XXXX                XXXX          XXXX  XXXX                        #
#          XXXXXXXXXXXXXXXXX.  XXXXXXXXXXXXXXXXXX  XXXX                        #
#          'XXXXXXXXXXXXXXXXX  XXXXXXXXXXXXXXXXX'  XXXX                        #
#                        XXXX  XXXX                XXXX                        #
#          .XXXXXXXXXXXXXXXXX  XXXX                XXXXXXXXXXXXXXXXX.          #
#          'XXXXXXXXXXXXXXXX'  'XX'                'XXXXXXXXXXXXXXXX'          #
# ---------------------------------------------------------------------------- #
#              Copyright 2023 Vittorio Pascucci (SideProjectsLab)              #
#                                                                              #
#  Licensed under the GNU GENERAL PUBLIC LICENSE Version 3 (the "License");    #
#  you may not use this file except in compliance with the License.            #
#  You may obtain a copy of the License at                                     #
#                                                                              #
#      https://www.gnu.org/licenses/                                           #
#                                                                              #
#  Unless required by applicable law or agreed to in writing, software         #
#  distributed under the License is distributed on an "AS IS" BASIS,           #
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.    #
#  See the License for the specific language governing permissions and         #
#  limitations under the License.                                              #
# ---------------------------------------------------------------------------- #

from   __future__ import annotations
from   typing   import List
import keyboard as kb

try:
	from ezhdl.ez_types  import *
	from ezhdl.ez_signal import *
	from ezhdl.ez_entity import *
	from ezhdl.ez_vcd    import *
except:
	from ez_types  import *
	from ez_signal import *
	from ez_entity import *
	from ez_vcd    import *


class SimpleSim:
	stop_simulation = True
	time_ps         = 0
	event_times     = []
	force_run       = False
	force_dump      = False
	cycle_limit     = 1000

	vcd_path        = None
	vcd_timescale   = "ps"
	vcd_live        = False

	@classmethod
	def run(cls, dut:Entity):
		print('Simulation Started, press "F10" to enter the Pause Menu')
		dut.reset()

		cls.stop_simulation = False
		dut.register_signals()

		# preparing VCD output
		vcd_time_mult = 1 / time_unit_to_mult(cls.vcd_timescale)
		vcd = VCD(cls.vcd_path, cls.vcd_timescale)

		vcd.dump(int(cls.time_ps*vcd_time_mult), cls.force_dump)

		# running simulation
		while not cls.stop_simulation:
			count = 0
			while True:
				dut.run()
				updated = Signal.update()

				if (updated == 0) and not cls.force_run:
					break
				else:
					if count >= cls.cycle_limit:
						raise Exception("Potential cyclical assignment detected")
					count += 1
				cls.force_run = False

			# dumping changes in VCD
			vcd.dump(int(cls.time_ps*vcd_time_mult))
			Signal.clear_changes()

			if len(cls.event_times) == 0:
				break
			else:
				cls.time_ps = cls.event_times[0]
				cls.event_times.pop(0)

			# accepting user input to pause and/or terminate the simulation
			cls.userinput()

		vcd.flush()
		print("Simulation Ended")


	@classmethod
	def userinput(cls):
		if kb.is_pressed('F10'):
			print('Simulation paused, press "F10" to resume "F12" to terminate')
			# waiting for space key to be de-pressed
			while kb.is_pressed('F10'):
				pass
			# waiting for new input
			while True:
				if kb.is_pressed('F12'):
					cls.stop_simulation = True
					break
				if kb.is_pressed('F10'):
					# making sure the spacebar is de-pressed before we continue
					while kb.is_pressed('F10'):
						pass
					print('Simulation resumed')
					break

	@classmethod
	def stop(cls):
		print("Stopping Simulation")
		cls.stop_simulation = True

	@classmethod
	def schedule_event(cls, time_ps):
		for i in range(len(cls.event_times)):
			if time_ps == cls.event_times[i]:
				return
			elif time_ps < cls.event_times[i]:
				cls.event_times.insert(time_ps, i)
				break
		else:
			cls.event_times.append(time_ps)

################################################################################
#                              PROCEDURE FUNCTIONS                             #
################################################################################

def time_unit_to_mult(unit):
	units = ["ps", "ns", "us", "ms", "s"]
	mult = 1
	for i in range(len(units)):
		if unit == units[i]:
			break
		mult *= 1000
	else:
		raise Exception(f"Unit of time: {unit} not supported")
	return mult


def wait(time, unit="s"):
	mult = time_unit_to_mult(unit)
	target_time = SimpleSim.time_ps + time*mult
	SimpleSim.schedule_event(target_time)

	SimpleSim.force_run = True
	yield
	while SimpleSim.time_ps != target_time:
		yield


def posedge(s:Signal):
	SimpleSim.force_run = True
	yield
	while not s.posedge():
		yield


def negedge(s:Signal):
	SimpleSim.force_run = True
	yield
	while not s.negedge():
		yield

def anyedge(s:Signal):
	SimpleSim.force_run = True
	yield
	while not s.anyedge():
		yield

################################################################################
#                                   UTILITIES                                  #
################################################################################

class ClockGen(Entity):
	def __init__(self, freq):
		self.period = 1 / freq
		self.clk = Signal(Wire())

	@procedure
	def _run(self):
		while True:
			self.clk.nxt <<= 1
			yield from wait(self.period / 2)
			self.clk.nxt <<= 0
			yield from wait(self.period / 2)

	def _reset(self):
		self.clk.nxt <<= 0
