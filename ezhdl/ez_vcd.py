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

from   vcd.writer import VCDWriter
import subprocess as sp

try:
	from ezhdl.ez_types  import *
	from ezhdl.ez_signal import *
except:
	from ez_types  import *
	from ez_signal import *

class VCD:
	def __init__(self, path, timescale, live=False):
		self.vcd_file = None

		if path != None:
			self.vcd_live   = live
			self.vcd_file   = open(path, "w")
			self.vcd_writer = VCDWriter(self.vcd_file, timescale="1 "+timescale)

			for i in Signal.instances:
				s : Signal = i()
				self.register_signal(s)


	def flush(self):
		self.vcd_file.flush()


	def register_record(self, s, rec, scope, name):
		if s.vcd == None:
			s.vcd = []
		attr = vars(rec).items()
		for n, v in attr:
			if isinstance(v, Record):
				self.register_record(s, v, scope, '.'.join([name, n]))
			else:
				s_type, s_size = get_vcd_specs(v)
				if s_type != None:
					s.vcd.append(self.vcd_writer.register_var(scope=scope,
						name='.'.join([name, n]), var_type=s_type, size=s_size))


	def register_signal(self, s):
		if isinstance(s.now, Record):
			self.register_record(s, s.now, s.path, s.name)
		else:
			s_type, s_size = get_vcd_specs(s)
			if s_type != None:
				s.vcd = self.vcd_writer.register_var(scope=s.path,
						name=s.name, var_type=s_type, size=s_size)


	def dump(self, timestamp, force=False):
		if self.vcd_file != None:
			for i in Signal.instances:
				s = i()
				if (s._transition or force) and s.vcd != None:
					if isinstance(s.now, Record):
						self.dump_record(s, s.now, timestamp)
					else:
						self.vcd_writer.change(s.vcd, timestamp=timestamp, value=s.now.dump)

			if self.vcd_live and self.vcd_file.tell():
				self.vcd_live = False
				sp.Popen(["gtkwave", self.vcd_path])


	def dump_record(self, s, rec, timestamp, idx = 0):
		attr = vars(rec).items()
		for n, v in attr:
			if isinstance(v, Record):
				self.dump_record(s, v, timestamp, idx)
			else:
				self.vcd_writer.change(s.vcd[idx], timestamp=timestamp, value=v.dump)
			idx += 1


def get_vcd_specs(s : Signal|HwType):
	if isinstance(s, Signal):
		s = s.now
	s_size = None
	s_type = None
	elements = 0

	if isinstance(s, Array):
		elements = len(s)
		# empty arrays do not need to be dumped
		if elements == 0:
			return None, None
		s = s[0]

	if isinstance(s, Wire):
		s_size = 1
		s_type = "wire"
	elif isinstance(s, Enum):
		s_type = "string"
		s_size = len(s)
	elif isinstance(s, Unsigned):
		s_size = len(s)
		s_type = "integer"
	elif isinstance(s, Signed):
		s_size = len(s)
		s_type = "integer"
	elif isinstance(s, Integer):
		s_type = "integer"
	elif isinstance(s, int):
		s_type = "integer"
	elif isinstance(s, float):
		s_type = "real"

	if s_size != 0:
		if elements != 0:
			# creating a tuple of sizes (in this case all the same)
			s_size = [s_size]*elements
		return s_type, s_size
	return None, None
