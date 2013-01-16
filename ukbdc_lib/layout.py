from ctypes import c_uint8
from copy import copy
from .mnemonics import mnemonics, scancodes

def as_signed(x):
	if x < 128:
		return x
	else:
		return x - 256

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
		if type(scancode) is int:
			self.scancode = scancode
		else:
			self.scancode = scancodes[scancode]
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

	@property
	def nicename(self):
		try:
			return mnemonics[self.scancode]
		except KeyError:
			return hex(self.scancode)

class Layout(object):
	def __init__(self, no_keys = None, no_layers = None):
		if no_keys is None or no_layers is None:
			return
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

	@staticmethod
	def from_binary(data):
		l = Layout()
		l.no_keys, l.no_layers, *rest = data
		lay_size = 4 * l.no_keys
		layers = [rest[i*lay_size:(i+1)*lay_size] for i in range(0, l.no_layers)]
		l.layers = []
		for lay in layers:
			layer = []
			binlay = [lay[i*4:(i+1)*4] for i in range(0, l.no_keys)]
			for binkd in binlay:
				pr = Action(binkd[1] >> 4, as_signed(binkd[2]))
				re = Action(binkd[1] & 0x0f, as_signed(binkd[3]))
				kd = KeyDef(binkd[0], pr, re)
				layer.append(kd)
			l.layers.append(layer)
		return l
