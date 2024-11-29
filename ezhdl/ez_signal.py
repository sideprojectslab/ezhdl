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

import time
import weakref
import inspect

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
		else:
			self._obj = deepcopy(obj)
		self._next    = deepcopy(self._obj)
		self._pend    = False

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
				ppl = 1
			self.content = []
			for _ in range(ppl):
				self.content.append(SignalContent(obj))

		self.driver = None
		self.drives : List["Signal"] = []

		self._changed    = False
		self._posedge    = False
		self._negedge    = False
		self._transition = False

		self.path = ''
		self.name = ''
		self.vcd  = None

		Signal.instances.append(weakref.ref(self))


	def __str__(self):
		return str(self.content[0]._obj)


	def __del__(self):
		for i in range(len(Signal.instances)):
			if Signal.instances[i]() is self:
				Signal.instances.pop(i)


	@property
	def now(self):
		return self.content[-1]._obj


	@property
	def nxt(self):
		# this is necessary because calling my_object.nxt[:] actually calls
		# the getter and not the setter. So even just reading the _next might
		# mean we are changing its value
		for i in range(0, len(self.content)):
			self.content[i]._pend = True
		return self.content[0]._next


	@nxt.setter
	def nxt(self, val):
		fail = False

		# we accept both objects and other signals (by grabbing the
		# underlying object)
		if isinstance(val, Signal):
			next_val = val.now
		else:
			next_val = val

		# the receiving object needs to be a subclass of the source object
		if not isinstance(self.content[0]._obj, type(next_val)):
			fail |= True

		# if the receiving object implements additional type checks, we run them
		if hasattr(self.content[0]._obj, "check_type"):
			fail |= not self.content[0]._obj.check_type(next_val)

		# fail if type checks did not succeed
		if fail:
			raise Exception(f"Source type ({type(next_val)}) not compatible with destination type ({type(self.content[0]._obj)})")

		# types with assignment do not need to be copied
		if hasattr(self.content[0]._obj, "assign"):
			self.content[0]._next.assign(next_val)
			self.content[0]._pend = True
			for i in range(1, len(self.content)):
				self.content[i]._next.assign(self.content[i-1]._obj)
				self.content[i]._pend = True
		else:
			self.content[0]._next = deepcopy(next_val)
			self.content[0]._pend = True
			for i in range(1, len(self.content)):
				self.content[i]._next = deepcopy(self.content[i-1]._obj)
				self.content[i]._pend = True


	@classmethod
	def update(cls):
		updated = 0

		# it is important that FIRST we detect all changes to all signals before
		# updating the contents seen that connected signals share contents
		for i in Signal.instances:
			s : Signal = i()
			# evaluating edges for sensitivity lists
			if s.content[-1]._pend:
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
			for c in s.content:
				if c._pend:
					# update count needs to be done per content and not per signal
					# due to pipelined signals which might be hiding changes within
					# their pipeline
					if c._obj != c._next:
						updated += 1

					if hasattr(c._obj, "assign"):
						c._obj.assign(c._next)
					else:
						c._obj = deepcopy(c._next)
					c._pend = False
		return updated


	@classmethod
	def clear_changes(cls):
		for i in Signal.instances:
			s : Signal = i()
			s._changed = False
			s._posedge = False
			s._negedge = False
			s._transition = False


	def check_type(self, b:Signal|any):
		'''
		check_type() for Signal is used when connecting signals, checks if the
		source object is also a signal and runs all underlying type checks
		'''
		# the source object must be a signal
		if isinstance(b, Signal):
			# at a minimum, the receiving object needs to be a subclass of
			# the source object
			if isinstance(self.content[0]._obj, type(b.content[0]._obj)):
				# if the receiving object has additional type checks we run them
				if hasattr(self.content[0]._obj, "check_type"):
					return self.content[0]._obj.check_type(b.content[0]._obj)
				else:
					return True
		return False


	def connect(self, b:Signal|any):
		if (not (self.driver is None)) and (not (self.driver is b)):
			raise Exception(f"Signal cannot have multiple drivers")

		# connecting signals means letting them "point" to the same underlying SignalContent
		if self.check_type(b):
			self.content = b.content
			self.driver = b
			present = False
			for i in b.drives:
				if i is self:
					present = True
			if not present:
				b.drives.append(self)
			for i in self.drives:
				i.connect(self)
		else:
			raise Exception(f"Source type ({type(b.content[0]._obj)}) not compatible with destination type ({type(self.content[0]._obj)})")

	# overloading <<= as copy-assignment operator
	def __lshift__(self, other:Signal|any):
		self.connect(other)
		return self

	# overloading <<= as copy-assignment operator
	def __rshift__(self, other:Signal|any):
		other.connect(self)
		return self

	# Disabling equality operator
	def __eq__(self, other):
		raise NotImplementedError("Operator not supported for this class.")

	# Disabling inequality operator
	def __ne__(self, other):
		raise NotImplementedError("Operator not supported for this class.")

	# Disabling string representation
	def __repr__(self):
		raise NotImplementedError("Representation is not supported for this class.")

	# Disabling hash functionality
	def __hash__(self):
		raise NotImplementedError("Hashing is not supported for this class.")

	# Disabling bool conversion
	def __bool__(self):
		raise NotImplementedError("Bool conversion is not supported for this class.")

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

################################################################################
#                                     INPUT                                    #
################################################################################

class Input(Signal):
	def connect(self, b:Signal|any):
		stack = inspect.stack()
		for i in range(1, len(stack)):
			caller_frame = stack[i]
			caller_self = caller_frame.frame.f_locals.get("self")
			if caller_self is not None:
				for val in vars(caller_self).values():
					if self is val:
						raise Exception(f"Input Signal cannot have a driver")
		super().connect(b)

################################################################################
#                                    OUTPUT                                    #
################################################################################

class Output(Signal):
	def connect(self, b:Signal|any):
		stack = inspect.stack()
		for i in range(1, len(stack)):
			caller_frame = stack[i]
			caller_self = caller_frame.frame.f_locals.get("self")
			if caller_self is not None:
				for val in vars(caller_self).values():
					if self is val:
						super().connect(b)
						return
		raise Exception(f"Output Signal cannot have a driver")


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
