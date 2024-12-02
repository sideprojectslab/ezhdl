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
		self._forward_attributes()


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
		if hasattr(self.content[0]._obj, "_check_type"):
			fail |= not self.content[0]._obj._check_type(next_val)

		# fail if type checks did not succeed
		if fail:
			raise Exception(f"Source type ({type(next_val)}) not compatible with destination type ({type(self.content[0]._obj)})")

		# types with assignment do not need to be copied
		self.content[0]._pend = True
		if hasattr(self.content[0]._obj, "_assign"):
			self.content[0]._next._assign(next_val)
			for i in range(1, len(self.content)):
				self.content[i]._next._assign(self.content[i-1]._obj)
		else:
			self.content[0]._next = deepcopy(next_val)
			for i in range(1, len(self.content)):
				self.content[i]._next = deepcopy(self.content[i-1]._obj)


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


	def _check_type(self, b:Signal|any):
		'''
		_check_type() for Signal is used when connecting signals, checks if the
		source object is also a signal and runs all underlying type checks
		'''
		# the source object must be a signal
		if isinstance(b, Signal):
			# at a minimum, the receiving object needs to be a subclass of
			# the source object
			if isinstance(self.content[0]._obj, type(b.content[0]._obj)):
				# if the receiving object has additional type checks we run them
				if hasattr(self.content[0]._obj, "_check_type"):
					return self.content[0]._obj._check_type(b.content[0]._obj)
				else:
					return True
		return False

	def driver(self, b:Signal):
		if (not (self._driver is None)) and (not (self._driver is b)):
			raise Exception(f"Signal cannot have multiple _drivers")

		# connecting signals means letting them "point" to the same underlying SignalContent
		if self._check_type(b):
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

	# overloading |= as concurrent assignment operator
	def __ior__(self, other:Signal):
		self.driver(other)
		return self

	# overloading <<= as copy-assignment operator
	def __ilshift__(self, other:Signal|any):
		if isinstance(other, Signal):
			other = other.now
		self.nxt <<= other
		return self

	# Dynamically bind methods from the contained object to this signal
	def _forward_attributes(self):
		for name in dir(self.content[0]._obj):
			attr = getattr(self.content[0]._obj, name)
			# skip private and special methods
			if not name.startswith("_"):
				if callable(attr):
					self._bind_method(name, attr)
				else:
					setattr(self, name, attr)


	def _bind_method(self, name, method):
		# Create a wrapper function that calls the contained method
		def wrapper(*args, **kwargs):
			return method(*args, **kwargs)
		# Bind the wrapper function to this Container instance
		setattr(self, name, wrapper)

	# mathematical binary
	def __add__(self, other):
		return self.now + other

	def __radd__(self, other):
		return other + self.now

	def __sub__(self, other):
		return self.now - other

	def __rsub__(self, other):
		return other - self.now

	def __mul__(self, other):
		return self.now * other

	def __rmul__(self, other):
		return other * self.now

	def __floordiv__(self, other):
		return self.now // other

	def __rfloordiv__(self, other):
		return other // self.now

	def __truediv__(self, other):
		return self.now / other

	def __rtruediv__(self, other):
		return other / self.now

	def __lshift__(self, other):
		return self.now << other

	def __rlshift__(self, other):
		return other << self.now

	def __rshift__(self, other):
		return self.now >> other

	def __rrshift__(self, other):
		return other >> self.now

	def __mod__(self, other):
		return self.now % other

	def __rmod__(self, other):
		return other % self.now

	def __pow__(self, other):
		return self.now ** other

	def __rpow__(self, other):
		return other ** self.now

	#mathematical unary
	def __abs__(self):
		return abs(self.now)

	def __neg__(self):
		return -(self.now)

	def __round__(self):
		return round(self.now)

	def __floor__(self):
		return math.floor(self.now)

	def __ceil__(self):
		return math.ceil(self.now)

	def __trunc__(self):
		return math.trunc(self.now)


	# bitwise boolean
	def __and__(self, other):
		return self.now & other

	def __rand__(self, other):
		return other & self.now

	def __or__(self, other):
		return self.now | other

	def __ror__(self, other):
		return other | self.now

	def __xor__(self, other):
		return self.now ^ other

	def __rxor__(self, other):
		return other ^ self.now

	def __invert__(self):
		return ~self.now

	# comparison
	def __eq__(self, other):
		return self.now == other
	def __ne__(self, other):
		return self.now != other
	def __ge__(self, other):
		return self.now >= other
	def __gt__(self, other):
		return self.now > other
	def __le__(self, other):
		return self.now <= other
	def __lt__(self, other):
		return self.now < other

	# casts
	def __bool__(self):
		return self.now.__bool__()

	def __int__(self):
		return self.now.__int__()

	def __index__(self):
		return self.now.__index__()

	def __float__(self):
		return self.now.__float__()

	def __str__(self):
		return self.now.__str__()

	def __repr__(self):
		return self.now.__repr__()

	# slicing and other utilities
	def __len__(self):
		return self.now.__len__()

	def __getitem__(self, key):
		return self.now.__getitem__(key)

	def __setitem__(self, key, value):
		return self.now.__setitem__(key, value)

	def __del__(self):
		for i in range(len(Signal.instances)):
			if Signal.instances[i]() is self:
				Signal.instances.pop(i)

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
