class Button(object):
	def __init__(self, width, height, x, y):
		self._width, self._height = width, height
		self._x, self._y = x, y

	@property
	def x(self):
		return self._x

	@property
	def y(self):
		return self._y

	@property
	def width(self):
		return self._width

	@property
	def height(self):
		return self._height

class Buttons(dict):
	def __init__(self, num_keys, width, height):
		self._width, self._height = width, height
		self._num_keys = num_keys

	@property
	def num_keys(self):
		return self._num_keys

	@property
	def width(self):
		return self._width

	@property
	def height(self):
		return self._height

	@property
	def nos(self):
		return list(self.keys())

	def add_button(self, no, width, height, x, y):
		self[no] = Button(width, height, x, y)
