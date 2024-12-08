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
from   typing import List
from   copy import deepcopy

import math
import weakref
import inspect

try:
	from ezhdl.ez_types  import *
except:
	from ez_types  import *

################################################################################
#                                SIGNAL CONTENT                                #
################################################################################

class SignalContent(object):
	'''
	SignalContent holds the actual objects, as well as their "next" counterpart
	'''
	def __init__(self, obj):
		if isinstance(obj, SignalContent):
			self._obj = deepcopy(obj._obj)
		elif isinstance(obj, HwType):
			self._obj = deepcopy(obj)
		else:
			raise Exception("Only HwTypes are allowed for signals")

		self._next           = deepcopy(self._obj)
		self._pend           = False

################################################################################
#                                    SIGNAL                                    #
################################################################################

class Signal(object):
	'''
	Signal Holds an array of SignalContent, and implements the "next" and "now"
	methods to access the underlying objects
	'''
	instances : List["Signal"] = []

	def __init__(self, obj:Signal|any, ppl:int=None):
		if isinstance(obj, Signal):
			if ppl is None:
				ppl = len(obj.content)
			self.content : List["SignalContent"] = []
			for _ in range(ppl):
				self.content.append(SignalContent(obj.content[0]))
		else:
			if ppl is None:
				ppl = 0
			self.content = []
			for _ in range(ppl+1):
				self.content.append(SignalContent(obj))

		self._driver = None
		self._drives : List["Signal"] = []

		self._changed    = False
		self._posedge    = False
		self._negedge    = False
		self._transition = False

		self.path = ''
		self.name = ''
		self.vcd  = None

		Signal.instances.append(weakref.ref(self))


	@property
	def now(self):
		return self.content[-1]._obj


	@property
	def nxt(self):
		# this is necessary because calling my_object.nxt[:] actually calls
		# the getter and not the setter. So even just reading the _next might
		# mean we are changing its value
		self.content[0]._pend = True
		return self.content[0]._next

	@nxt.setter
	def nxt(self, val):
		pass

	@classmethod
	def update(cls):
		updated = 0

		# it is important that FIRST we detect all changes to all signals before
		# updating the contents seen that connected signals share contents
		for i in Signal.instances:
			s : Signal = i()
			# evaluating edges for sensitivity lists
			if s.content[0]._pend:
				s._changed = s.changed_eval()
				s._posedge = s.posedge_eval()
				s._negedge = s.negedge_eval()
				# the transition flag is sticky (used for logging and cleared by the simulator)
				s._transition = s._changed
			else:
				s._changed = False
				s._posedge = False
				s._negedge = False

		# now we can do the actual content update
		for i in Signal.instances:
			s : Signal = i()
			if s.content[0]._pend:
				s.content[0]._pend = False

				for i in range(1, len(s.content)):
					s.content[i]._next._assign(s.content[i-1]._obj)

				for c in s.content:
					# update count needs to be done per content and not per signal
					# due to pipelined signals which might be hiding changes within
					# their pipeline
					if c._obj != c._next:
						updated += 1

					if hasattr(c._obj, "_assign"):
						c._obj._assign(c._next)
					else:
						c._obj = deepcopy(c._next)
		return updated


	@classmethod
	def clear_changes(cls):
		for i in Signal.instances:
			s : Signal = i()
			s._changed = False
			s._posedge = False
			s._negedge = False
			s._transition = False


	def driver(self, b:Signal):
		if (not (self._driver is None)) and (not (self._driver is b)):
			raise Exception(f"Signal cannot have multiple _drivers")

		if not isinstance(b, Signal):
			raise Exception("Only signals can be assigned to other signals")

		# connecting signals means letting them "point" to the same underlying SignalContent
		if self.now._check_type(b.now):
			self.content = b.content
			self._driver = b
			present = False
			for i in b._drives:
				if i is self:
					present = True
			if not present:
				b._drives.append(self)
			for i in self._drives:
				i.driver(self)
		else:
			raise Exception(f"Source type ({type(b.content[0]._obj)}) not compatible with destination type ({type(self.content[0]._obj)})")


	def posedge_eval(self):
		return (self.content[-1]._next != 0) and (self.content[-1]._obj == 0)

	def negedge_eval(self):
		return (self.content[-1]._next == 0) and (self.content[-1]._obj != 0)

	def changed_eval(self):
		return self.content[-1]._next != self.content[-1]._obj

	def posedge(self):
		return self._posedge

	def negedge(self):
		return self._negedge

	def anyedge(self):
		return self._posedge or self._negedge

	def changed(self):
		return self._changed

	# BINDING ALL FUNCTIONS OF THE UNDERLYING OBJECT

	# overloading <<= as concurrent assignment operator
	def __ilshift__(self, other:Signal|any):
		self.driver(other)
		return self

	def __del__(self):
		for i in range(len(Signal.instances)):
			if Signal.instances[i]() is self:
				Signal.instances.pop(i)

	def __bool__(self):
		raise Exception("Cannot use a signal as-is as boolean, use <signal>.now instead")

	def __eq__(self, other):
		raise Exception('Equality operator is disabled for signals, use "is" instead')

################################################################################
#                                     INPUT                                    #
################################################################################

class Input(Signal):

	def driver(self, b:Signal):
		stack = inspect.stack()
		for i in range(1, len(stack)):
			caller_frame = stack[i]
			caller_self = caller_frame.frame.f_locals.get("self")
			if caller_self is not None:
				for val in vars(caller_self).values():
					if self is val:
						raise Exception(f"Input Signal cannot have a _driver")
		super().driver(b)

################################################################################
#                                    OUTPUT                                    #
################################################################################

class Output(Signal):

	def driver(self, b:Signal):
		stack = inspect.stack()
		for i in range(1, len(stack)):
			caller_frame = stack[i]
			caller_self = caller_frame.frame.f_locals.get("self")
			if caller_self is not None:
				for val in vars(caller_self).values():
					if self is val:
						super().driver(b)
						return
		raise Exception(f"Output Signal cannot have a _driver")


################################################################################
#                                   UTILITIES                                  #
################################################################################

def local(obj):
	if isinstance(obj, Signal):
		return deepcopy(obj.now)
	else:
		return deepcopy(obj)


################################################################################
#                                SIGNAL CONTAINER                              #
################################################################################

# entities and bundles inherit from this class

class SignalContainer:
	def register_signals(self, parent_name='top'):
		attr = vars(self)
		for n, v in attr.items():
			if isinstance(v, SignalContainer):
				v.register_signals(('.'.join([parent_name, n])) if parent_name else n)
			if isinstance(v, Signal):
				v.path = parent_name
				v.name = n

# here we rename SignalContainer to Bundle for convenience
class Bundle(SignalContainer):
	pass


if __name__ == "__main__":
	a = Signal(Array([Integer()]*4))
	a.nxt[0] <<= 2
	Signal.update()
	pass
