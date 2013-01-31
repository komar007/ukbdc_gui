from ctypes import c_uint8
from .mnemonics import mnemonics, scancodes

def as_signed(x):
	if x < 128:
		return x
	else:
		return x - 256

def as_unsigned(x):
	if x < 0:
		return x + 256
	else:
		return x

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
	def __init__(self, layout = None, layer = None, no = None, scancode = 0, press = None, release = None, inherited = False):
		self._lay = layout
		self._layer = layer
		self._no = no
		self._inherited = inherited
		if type(scancode) is int:
			self._scancode = scancode
		else:
			self._scancode = scancodes[scancode]
		if press is not None:
			self._press = press
		else:
			self._press = Action(0x00)
		if release is not None:
			self._release = release
		else:
			self._release = Action(0x00)

	def get_root(self):
		if self.inherited:
			return self._lay.get_parent(self).get_root()
		else:
			return self

	@property
	def no(self):
		return self._no

	@property
	def layer(self):
		return self._layer

	@property
	def scancode(self):
		return self.get_root()._scancode

	@property
	def press(self):
		return self.get_root()._press

	@property
	def release(self):
		return self.get_root()._release

	@property
	def inherited(self):
		return self._inherited

	def binary(self, fordevice):
		if self.inherited and not fordevice:
			return b'\xff\xff\xff\xff'
		else:
			actions = (self.press.kind << 4) + self.release.kind
			fields = [self.scancode, actions, self.press.arg, self.release.arg]
			return b''.join(map(lambda x: bytes(c_uint8(x)), fields))

	@property
	def nicename(self):
		try:
			return mnemonics[self.scancode]
		except KeyError:
			if self.scancode == 0:
				return ""
			else:
				return hex(self.scancode)

class Layout(object):
	def __init__(self, no_keys = None, no_layers = None):
		if no_keys is None or no_layers is None:
			return
		self.no_keys = no_keys
		self.no_layers = no_layers
		self.layers = []
		for i in range(0, no_layers):
			deflay = []
			for j in range(0, no_keys):
				deflay.append(KeyDef(layout = self, layer = i, no = j))
			self.layers.append(deflay)
		self.parents = [-1] + [0] * (self.no_layers - 1)

	def __getitem__(self, pos):
		lay, key = pos
		return self.layers[lay][key]

	def __setitem__(self, pos, val):
		lay, key = pos
		kd = self.layers[lay][key]
		# Do not change reference, because inherited keys are using itk
		# Copy properties one by one instead
		kd._inherited = val._inherited
		kd._scancode = val._scancode
		kd._press = val._press
		kd._release = val._release

	def get_parent(self, key):
		if self.parents[key.layer] == -1:
			return key
		else:
			return self[self.parents[key.layer], key.no]

	def binary(self, fordevice = False):
		hdr = bytes(c_uint8(self.no_keys)) + bytes(c_uint8(self.no_layers))
		l = b''.join(map(lambda x: b''.join(map(lambda x: x.binary(fordevice), x)), self.layers))
		if fordevice:
			return hdr + l
		else:
			return hdr + l + bytes(map(as_unsigned, self.parents))

	@staticmethod
	def from_binary(data):
		l = Layout()
		l.no_keys, l.no_layers, *rest = data
		lay_size = 4 * l.no_keys
		layers = [rest[i*lay_size:(i+1)*lay_size] for i in range(0, l.no_layers)]
		l.parents = rest[l.no_layers*lay_size:l.no_layers*lay_size + l.no_layers]
		l.parents = list(map(as_signed, l.parents))
		l.layers = []
		for li, lay in enumerate(layers):
			layer = []
			binlay = [lay[i*4:(i+1)*4] for i in range(0, l.no_keys)]
			for i, binkd in enumerate(binlay):
				if all(map(lambda x: x == 0xff, binkd)):
					kd = KeyDef(layout = l, layer = li, no = i, inherited = True)
				else:
					pr = Action(binkd[1] >> 4, as_signed(binkd[2]))
					re = Action(binkd[1] & 0x0f, as_signed(binkd[3]))
					kd = KeyDef(layout = l, layer = li, no = i,
							scancode = binkd[0], press = pr, release = re)
				layer.append(kd)
			l.layers.append(layer)
		return l
