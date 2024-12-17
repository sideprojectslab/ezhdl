from ezpath import *

add_rel_path("input")


# for simplicity I am implementing the basic logic here without any formal
# testing framework. This will be eventually moved to a proper converter module
# and tested thoroughly

input_file_path = get_abs_path("input/input_logic.py")
with open(input_file_path, "r") as input_file:

	scope = 0 # keeps track of the depth of the scope



	pass
