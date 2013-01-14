from ctypes import c_uint8
from copy import copy

class Action(object):
	Abs = 0x02
	Rel = 0x01
	def __init__(self, kind, arg = 0x00):
		self.kind = kind
		self.arg = arg

class Rel(Action):
	def __init__(self, offset):
		super(Rel, self).__init__(Action.Rel, offset)

class Abs(Action):
	def __init__(self, layer):
		super(Abs, self).__init__(Action.Abs, layer)

class KeyDef(object):
	def __init__(self, scancode, press = None, release = None):
		self.scancode = scancode
		if press is not None:
			self.press = press
		else:
			self.press = Action(0x00)
		if release is not None:
			self.release = release
		else:
			self.release = Action(0x00)

	def binary(self):
		actions = (self.press.kind << 4) + self.release.kind
		fields = [self.scancode, actions, self.press.arg, self.release.arg]
		return b''.join(map(lambda x: bytes(c_uint8(x)), fields))

class Layout(object):
	def __init__(self, no_keys, no_layers):
		self.no_keys = no_keys
		self.no_layers = no_layers
		self.layers = []
		deflay = [KeyDef(0)]*no_keys
		for i in range(0, no_layers):
			self.layers.append(copy(deflay))

	def __getitem__(self, pos):
		lay, key = pos
		return self.layers[lay][key]

	def __setitem__(self, pos, val):
		lay, key = pos
		self.layers[lay][key] = val

	def binary(self):
		hdr = bytes(c_uint8(self.no_keys)) + bytes(c_uint8(self.no_layers))
		l = b''.join(map(lambda x: b''.join(map(lambda x: x.binary(), x)), self.layers))
		return hdr + l
