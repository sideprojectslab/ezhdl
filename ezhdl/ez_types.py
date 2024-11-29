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
from   typing     import List
from   copy       import deepcopy
import math

################################################################################
#                              HWTYPE BASE CLASS                               #
################################################################################

class HwType:
	# all ezhdl types support the assign() method. This allows to define
	# record-like classes by subclassing HwType. It is recommended to use
	# ezhdl types within such a class as they can be "assigned" the new value.
	# Class members of other types will be replaced with a "deepcopy" of the
	# corresponding member of the source object

	def assign(self, other:HwType|any):
		# we go through all attributes and if we find any other subclasses
		# of hwbase we
		for attr_name, attr_value in vars(self).items():
			if isinstance(attr_value, HwType):
				attr_value.assign(vars(other)[attr_name])
			else:
				attr_value = deepcopy(vars(other)[attr_name])
		return self

	# overloading <<= as copy-assignment operator
	def __ilshift__(self, other:HwType|any):
		return self.assign(other)

# here we rename HwType to Record for convenience
class Record(HwType):
	pass

################################################################################
#                                   UTILITIES                                  #
################################################################################

def join(*args):
	ret = 0
	for i in args:
		ret <<= i.nbits
		ret +=  i.val
	return Integer(ret)

def mask(hi, lo):
	return ((1 << (hi - lo)) - 1) << lo

################################################################################
#                                    INTEGER                                   #
################################################################################

class Integer(HwType):
	def constrain(self):
		return self

	def __init__(self, val=0, *args, **kwargs):
		self.val = val
		self.constrain()

	@property
	def val(self):
		return self._val

	@val.setter
	def val(self, v):
		if isinstance(v, Integer):
			self._val = v.val
		else:
			self._val = v
		return self

	def chop(self, *args):
		val = self.val
		for i in reversed(args):
			i.val = val
			i.constrain()
			val >>= i.nbits

	def assign(self, other:Integer|any):
		self.val = other
		return self.constrain()

	def __index__(self):
		# Define how the object is converted to an integer
		return self._val

	def __bool__(self):
		# Define how the object is converted to an integer
		return bool(self._val)

	# mathematical
	def __add__(self, other):
		return Integer(self.val + int(other))

	def __radd__(self, other):
		return self.val + int(other)

	def __sub__(self, other):
		return Integer(self.val - int(other))

	def __rsub__(self, other):
		return int(other) - self.val

	def __mul__(self, other):
		return Integer(self.val * int(other))

	def __rmul__(self, other):
		return self.val * int(other)

	def __floordiv__(self, other):
		return Integer(self.val // int(other))

	def __rfloordiv__(self, other):
		return int(other) // self.val

	def __neg__(self):
		return Integer(-self.val)

	def __abs__(self):
		return Integer(abs(self.val))

	def __lshift__(self, other):
		return Integer(self.val << int(other))

	def __rshift__(self, other):
		return Integer(self.val >> int(other))

	def __rlshift__(self, other):
		return int(other) << self.val

	def __rrshift__(self, other):
		return int(other) >> self.val

	# bitwise boolean
	def __and__(self, other):
		return Integer(self.val & int(other))

	def __rand__(self, other):
		return self.val & int(other)

	def __or__(self, other):
		return Integer(self.val | int(other))

	def __ror__(self, other):
		return self.val | int(other)

	def __xor__(self, other):
		return Integer(self.val ^ int(other))

	def __rxor__(self, other):
		return self.val ^ int(other)

	def __invert__(self):
		return Integer(~self.val)

	# Comparisons
	def __lt__(self, other):
		return self.val < int(other)

	def __rlt__(self, other):
		return self.val > int(other)

	def __le__(self, other):
		return self.val <= int(other)

	def __rle__(self, other):
		return self.val >= int(other)

	def __gt__(self, other):
		return self.val > int(other)

	def __rgt__(self, other):
		return self.val < int(other)

	def __ge__(self, other):
		return self.val >= int(other)

	def __rge__(self, other):
		return self.val <= int(other)

	def __eq__(self, other):
		return self.val == int(other)

	def __req__(self, other):
		return self.val == int(other)

	def __ne__(self, other):
		return self.val != int(other)

	def __rne__(self, other):
		return self.val != int(other)

	def __pow__(self, other, modulo=None):
		raise NotImplementedError(f"Power operation not supported for {type(self)}.")

	def __mod__(self, other):
		raise NotImplementedError(f"Modulo operator not supported for {type(self)}.")

	def __truediv__(self, other):
		raise NotImplementedError(f"In-place operations not supported for {type(self)}.")

	def __iadd__(self, other):
		raise NotImplementedError(f"In-place operations not supported for {type(self)}.")

	def __isub__(self, other):
		raise NotImplementedError(f"In-place operations not supported for {type(self)}.")

	def __imul__(self, other):
		raise NotImplementedError(f"In-place operations not supported for {type(self)}.")

	def __imod__(self, other):
		raise NotImplementedError(f"In-place operations not supported for {type(self)}.")

	def __ipow__(self, other):
		raise NotImplementedError(f"In-place operations not supported for {type(self)}.")

	def __repr__(self):
		if hasattr(self, "nbits"):
			b = "0b" + bin(self._val)[2:].zfill(self.nbits)
			hex_digits = ((self.nbits - 1) // 4) + 1
			h = "0x" + hex(self._val)[2:].zfill(hex_digits)
			d = str(int(self._val))
		else:
			b = bin(self._val)
			h = hex(self._val)
			d = str(int(self._val))
		return f"dec:{d}, hex:{h}, bin:{b}"

	# slicing
	def __getitem__(self, key):
		if isinstance(key, slice):
			hi = key.start if key.start is not None else self.nbits
			lo = key.stop if key.stop is not None else 0
			if hi < 0:
				hi += len(self)
			if lo < 0:
				lo += len(self)
		else:
			if key < 0:
				key += len(self)
			hi = key + 1
			lo = key

		if lo > hi:
			raise Exception("Integer slices must have downward direction")

		val = (self._val & mask(hi, lo)) >> lo
		ret = type(self)(val, nbits=hi - lo)
		return ret

	def __setitem__(self, key, value):
		if isinstance(key, slice):
			hi = key.start
			lo = key.stop
		else:
			hi = key
			lo = key

		hi = hi if hi is not None else self.nbits
		lo = lo if lo is not None else 0

		if hi < 0:
			hi += len(self)
		if lo < 0:
			lo += len(self)

		if lo > hi:
			raise Exception("Integer slices must have downward direction")

		m = mask(hi, lo)
		self._val &= ~m
		self._val += (value << lo) & m
		return self.constrain()

################################################################################
#                                     WIRE                                     #
################################################################################

class Wire(Integer):
	def constrain(self):
		self._val &= 1
		return self

	def __len__(self):
		return 1

################################################################################
#                                   UNSIGNED                                   #
################################################################################

class Unsigned(Integer):
	def mask(self):
		return (1 << self.nbits) - 1

	def constrain(self):
		self._val &= self.mask()
		return self

	def __init__(self, val=0, nbits=32, *args, **kwargs):
		self.nbits = max(nbits, 0)
		self.val   = val
		self.constrain()

	def __len__(self):
		return self.nbits

	def bits(self, nbits):
		self.nbits = nbits
		return self.constrain()

	def span(self, spn):
		if spn == 0:
			self.nbits = 0
		elif spn == 1:
			self.nbits = 1
		else:
			self.nbits = int(math.ceil(math.log2(spn)))
		return self.constrain()

	def upto(self, val):
		if val >= 0:
			rng = val + 1
		else:
			raise Exception(f"Value {val} cannot be represented with Unsigned type")
		return self.span(rng)

################################################################################
#                                    SIGNED                                    #
################################################################################

class Signed(Integer):
	def mask(self):
		return (1 << self.nbits) - 1

	def constrain(self):
		self._val &= self.mask()
		if self._val >> (self.nbits - 1):
			self._val -= (1 << self.nbits)
		return self

	def __init__(self, val=0, nbits=32, *args, **kwargs):
		self.nbits = max(nbits, 0)
		self.val   = val
		self.constrain()

	def __len__(self):
		return self.nbits

	def bits(self, nbits):
		self.nbits = nbits
		return self.constrain()

	def span(self, spn):
		if spn == 0:
			self.nbits = 0
		elif spn == 1:
			self.nbits = 1
		else:
			self.nbits = int(math.ceil(math.log2(spn)))
		return self.constrain()

	def upto(self, val):
		if val >= 0:
			rng = val + 1
		else:
			rng = -2 * val
		return self.span(rng)


################################################################################
#                                     ENUM                                     #
################################################################################

class Enum(HwType):
	def __init__(self, *args):
		for i in range(len(args)):
			if not isinstance(args[i], str):
				raise Exception("Enumeration keys must be strings")
			self.__setattr__(args[i], i)
		self._len = len(args)

	def __len__(self):
		return self._len

################################################################################
#                                     ARRAY                                    #
################################################################################

class Array(List, HwType):

	def __init__(self, val):
		super().__init__([])
		for i in val:
			self.append(deepcopy(i))

	def check_type(self, b:Array|any):
		if len(self) != len(b):
			return False

		# at the very least, the source needs to be a parent class of the
		# destination
		if not isinstance(self, type(b)):
			return False

		# all members need to be compatible
		for i in range(len(self)):
			if isinstance(self[i], type(b[i])):
				if hasattr(self[i], "check_type"):
					if self[i].check_type(b[i]):
						continue
					else:
						return False
				else:
					continue
			else:
				return False
		return True

	def assign(self, other:Array):
		if self.check_type(other):
			for i in range(len(self)):
				if hasattr(self[i], "assign"):
					self[i].assign(other[i])
				else:
					self[i] = deepcopy(other[i])
		else:
			raise Exception(f"Incompatible assignment from {type(other)} to {type(self)}")
		return self

	def __getitem__(self, key):
		ret = super().__getitem__(key)
		if isinstance(ret, list):
			return Array(ret)
		return ret

	@property
	def val(self):
		ret = []
		for i in self:
			if hasattr(i, "val"):
				ret.append(i.val)
			else:
				ret.append(i)
		return ret

################################################################################
#                                    RECORD                                    #
################################################################################



################################################################################
#                                 SIMPLE TEST                                  #
################################################################################

if __name__ == "__main__":
	a = Array([1]*40)
	b = Array([0]*40)

	b <<= a
	pass