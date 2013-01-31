import usb
from .crc16 import crc16
import time
from ctypes import c_uint16, c_uint8

class Packet(object):
	def __init__(self, hdr, payload = b''):
		self.hdr = bytes([hdr])
		self.payload = bytes(payload)

	def __len__(self):
		return 1 + len(self.payload)

	def __iter__(self):
		yield int(self.hdr[0])
		for b in self.payload:
			yield int(b)

class Ping(Packet):
	def __init__(self):
		super(Ping, self).__init__(0x00)

class Reset(Packet):
	def __init__(self):
		super(Reset, self).__init__(0x04)

class Start(Packet):
	def __init__(self, payload):
		super(Start, self).__init__(0x02, payload)

class Cont(Packet):
	def __init__(self, payload):
		super(Cont, self).__init__(0x03, payload)

class Message(object):
	def __init__(self, hdr, payload = b''):
		self.hdr = bytes([hdr])
		self.payload = bytes(payload)
		self.psize = None

	def set_packet_size(self, psize):
		self.psize = psize

	def __len__(self):
		return 1 + len(self.payload)
		if self.psize is None:
			raise RuntimeError("psize not set!")

	def __iter__(self):
		if self.psize is None:
			raise RuntimeError("psize not set!")
		msg = self.hdr + self.payload
		fst = msg[0:self.psize - 4]
		rest = [msg[i:i+self.psize-1] for i in range(self.psize - 4, len(msg), self.psize - 1)]
		payload = bytes(c_uint8(len(self))) + bytes(c_uint16(crc16(msg))) + fst
		yield Start(payload)
		for c in rest:
			yield Cont(c)

class Dfu(Message):
	def __init__(self):
		super(Dfu, self).__init__(0x00)

class WritePage(Message):
	def __init__(self, page_addr, page):
		if len(page) < 128:
			page += bytes([0] * (128-len(page)))
		elif len(page) > 128:
			raise ValueError("page too long")
		payload = bytes(c_uint8(page_addr)) + page
		super(WritePage, self).__init__(0x01, payload)

class ActivateLayout(Message):
	def __init__(self):
		super(ActivateLayout, self).__init__(0x02)

class DeactivateLayout(Message):
	def __init__(self):
		super(DeactivateLayout, self).__init__(0x03)

class Status(object):
	IDLE			= 0
	UNEXPECTED_CONT_ERROR	= 1
	CRC_ERROR		= 2
	RECEIVING_MESSAGE	= 3
	EXECUTING		= 4
	MESSAGE_ERROR		= 6
	BUSY_ERROR		= 7
	WRONG_MESSAGE_ERROR	= 8

	@classmethod
	def name(self, st):
		if st == self.IDLE:
			return "idle"
		elif st == self.UNEXPECTED_CONT_ERROR:
			return "unexpected cont packet"
		elif st == self.CRC_ERROR:
			return "crc error"
		elif st == self.RECEIVING_MESSAGE:
			return "receiving message"
		elif st == self.EXECUTING:
			return "executing"
		elif st == self.MESSAGE_ERROR:
			return "message error (malformed)"
		elif st == self.BUSY_ERROR:
			return "requested operation while device busy"
		elif st == self.WRONG_MESSAGE_ERROR:
			return "unknown message received"

class UKBDC(object):
	vendorId = 0x16c0
	productId = 0x047c
	interface = 1
	ep_out = 0x03
	ep_in = 0x82
	tm_out = 1000
	def __init__(self):
		self.dev = None
		pass

	def attach(self):
		self.dev = usb.core.find(
				idVendor = self.vendorId,
				idProduct = self.productId
		)
		if self.dev is None:
			raise RuntimeError("no device found")
		try:
			usb.util.claim_interface(self.dev, self.interface)
		except usb.core.USBError:
			self.dev.detach_kernel_driver(self.interface)
		config = self.dev[0]
		iface = config[self.interface, 0]
		self.epin = usb.util.find_descriptor(iface, custom_match = \
				lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == \
					usb.util.ENDPOINT_IN)
		self.epout = usb.util.find_descriptor(iface, custom_match = \
				lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == \
					usb.util.ENDPOINT_OUT)
		self.reset()

	def detach(self):
		usb.util.release_interface(self.dev, self.interface)
		self.epin = None
		self.epout = None

	def write_packet(self, p):
		if len(p) > self.epout.wMaxPacketSize:
			raise OverflowError("packet length > bMaxPacketSize")
		elif self.dev is not None:
			self.epout.write(bytes(p), timeout = self.tm_out)
		else:
			raise RuntimeError("device not attached")

	def read_packet(self):
		if self.dev is not None:
			return self.epin.read(self.epin.wMaxPacketSize, timeout = self.tm_out)
		else:
			raise RuntimeError("device not attached")

	def status(self):
		self.write_packet(Ping())
		return self.read_packet()[1]

	def reset(self):
		self.write_packet(Reset())

	def send(self, msg):
		msg.set_packet_size(self.epout.wMaxPacketSize)
		for packet in msg:
			self.write_packet(packet)

	def dfu(self):
		self.send(Dfu())

	def program_layout(self, data):
		self.send(DeactivateLayout())
		pages = [data[i:i+128] for i in range(0, len(data), 128)]
		for no, page in enumerate(pages):
			m = WritePage(no, page)
			self.send(m)
			while self.status() == Status.EXECUTING:
				pass
			s = self.status()
			if s != Status.IDLE:
				raise RuntimeError("device returned status: %s" % Status.name(s))
		self.send(ActivateLayout())
