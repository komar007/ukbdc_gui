#!/usr/bin/env python3
from tkinter import *
from tkinter.filedialog import *
from tkinter.messagebox import *
import sys
import xml.etree.ElementTree as ET

from ukbdc_lib.layout import *

class KeyButton(Button):
	hicolor = "lightgreen"
	def __init__(self, master, identifier, command = lambda: False):
		super(KeyButton, self).__init__(master, text = "Key", command = self.on_click)
		self.command = command
		self.highlighted = False
		self.bgcolor = self.cget("bg") # remember bg color for later use
		self.grid(column = 0, row = 0, sticky = N+S+E+W)
		self.bind("<Leave>", self.on_leave)
		self.bind("<Enter>", self.on_enter)
		self.iden = identifier
		self.no = Label(self, text = self.iden, font = (None, 7, "normal"))
		self.pr = Label(self, text = "", fg = "red", font = (None, 7, "normal"))
		self.re = Label(self, text = "", fg = "blue", font = (None, 7, "normal"))
		for label in [self.no, self.pr, self.re]:
			label.bind("<Button-1>", lambda x: self.invoke())
		self.do_layout()
		for x in range(3):
			Grid.columnconfigure(self, x, weight = 1)
			Grid.rowconfigure(self, x, weight = 1)
		Grid.columnconfigure(self, 1, weight = 10)
		Grid.rowconfigure(self, 1, weight = 10)

	def do_layout(self, event = None):
		# windows quirk hack
		self.no.grid_forget()
		self.pr.grid_forget()
		self.re.grid_forget()
		self.no.grid(column = 0, row = 0, sticky = N+W)
		self.pr.grid(column = 0, row = 2, sticky = S+W)
		self.re.grid(column = 2, row = 2, sticky = S+E)

	def set_color(self, color, only_labels = False):
		if not only_labels:
			self.config(bg = color)
		for label in [self.pr, self.re, self.no]:
			label.config(bg = color)

	def on_enter(self, event):
		color = self.cget("activebackground")
		if sys.platform.startswith("win"):
			self.set_color(color)
		else:
			self.set_color(color, only_labels = True)

	def on_leave(self, event):
		if sys.platform.startswith("win"):
			self.do_layout(event)
		color = self.cget("bg")
		if sys.platform.startswith("win"):
			if self.highlighted:
				self.set_color(self.hicolor)
			else:
				self.set_color(color)
		else:
			self.set_color(color, only_labels = True)

	def on_click(self):
		self.command(self)

	# Public API starts here...

	def generate_label(self, prefix, act):
		try:
			arg = str(act.arg)
		except ValueError:
			arg = ""
		if act.kind == Action.Rel:
			if act.arg >= 0:
				s = "+" + arg
			else:
				s = arg
			n = s
		elif act.kind == Action.Abs:
			n = arg
		else:
			n = ""
		if len(n) == 0:
			return ""
		else:
			return prefix + n

	def update_press_label(self, act):
		self.pr.config(text = self.generate_label("↓", act))

	def update_release_label(self, act):
		self.re.config(text = self.generate_label("↑", act))

	def highlight(self):
		self.highlighted = True
		self.set_color(self.hicolor)

	def dehighlight(self):
		self.highlighted = False
		self.set_color(self.bgcolor)

class KeyboardFrame(Frame):
	hicolor = "lightyellow"
	def __init__(self, master, command = lambda: False):
		super(KeyboardFrame, self).__init__(master)
		self.cur_button = None
		self.command = command
		self.bgcolor = self.master.cget("bg")
		master.bind("<Button-1>", self.on_click_nothing)

	def on_button_pressed(self, button):
		if self.cur_button is not None:
			self.cur_button.dehighlight()
		self.cur_button = button
		self.cur_button.highlight()
		self.command(button.iden)

	def on_click_nothing(self, w):
		if self.cur_button is not None:
			self.cur_button.dehighlight()
			self.cur_button = None
			self.command(None)

	def place_btn(self, key, btn, aspect = False):
		posx = int(key.attrib['x'])
		posy = int(key.attrib['y'])
		width = int(key.attrib['width'])
		height = int(key.attrib['height'])
		btn.place(
				relx = float(posx) / self.kwidth,
				rely = float(posy) / self.kheight,
				relwidth = float(width) / self.kwidth,
				relheight = float(height) / self.kheight
		)

	# Public API starts here...

	def update_button(self, no, kd):
		b = self.buttons[no]
		b.config(text = str(kd.scancode))
		b.update_press_label(kd.press)
		b.update_release_label(kd.release)

	def get_current_btn(self):
		if self.cur_button is None:
			return None
		else:
			return self.cur_button.iden

	# deprecated
	def load_xml(self, xml):
		tree = ET.parse(xml)
		keyboard = tree.getroot()
		self.kwidth = int(keyboard.attrib['width'])
		self.kheight = int(keyboard.attrib['height'])
		self.buttons = {}
		for key in keyboard:
			iden = int(key.attrib['id'])
			btn = KeyButton(self, iden, self.on_button_pressed)
			self.buttons[iden] = btn
			self.place_btn(key, btn)

class PropsFrame(Frame):
	kinds = ["None", "Change layer by", "Go to layer"]
	def __init__(self, master, notify = lambda: False):
		self.should_notify = False
		super(PropsFrame, self).__init__(master)
		self.notify = notify
		top = Frame(self)
		top.pack(side = TOP, fill = X)
		l = Label(top, text = "scancode: ")
		l.grid(column = 0, row = 0)
		vcmd = (master.register(self.validate_scancode), '%P')
		self.scancode = StringVar()
		self.scancode.set(0)
		self.scancode.trace("w", self.on_props_changed)
		self.scentry = Entry(top, textvariable = self.scancode, validate = "key",
				validatecommand = vcmd, width = 4)
		self.scentry.grid(column = 1, row = 0)
		acts = Frame(self)
		acts.pack(side = TOP, fill = X)
		l = Label(acts, text = "key press action: ")
		l.grid(column = 0, row = 0)
		self.pressaction = IntVar()
		vcmd = (master.register(lambda x, w = self.pressaction: self.validate_act(w, x)), '%P')
		self.pressarg = StringVar()
		self.pressarg.set(0)
		self.pressarg.trace("w", self.on_props_changed)
		self.pressnum = Entry(acts, textvariable = self.pressarg, validate = "key",
				validatecommand = vcmd, width = 4, state = DISABLED)
		self.pressnum.var = self.pressarg
		self.pressnum.grid(column = 2, row = 1, rowspan = 2, padx = 8)
		for i, t in enumerate(self.kinds):
			r = Radiobutton(acts, text = t, variable = self.pressaction, value = i,
					command = lambda: self.radio_changed(self.pressaction, self.pressnum))
			r.grid(column = 1, row = i, sticky = W)
		l = Label(acts, text = "key release action: ")
		l.grid(column = 3, row = 0)
		self.releaseaction = IntVar()
		vcmd = (master.register(lambda x, w = self.releaseaction: self.validate_act(w, x)), '%P')
		self.releasearg = StringVar()
		self.releasearg.set(0)
		self.releasearg.trace("w", self.on_props_changed)
		self.releasenum = Entry(acts, textvariable = self.releasearg, validate = "key",
				validatecommand = vcmd, width = 4, state = DISABLED)
		self.releasenum.var = self.releasearg
		self.releasenum.grid(column = 5, row = 1, rowspan = 2, padx = 8)
		for i, t in enumerate(self.kinds):
			r = Radiobutton(acts, text = t, variable = self.releaseaction, value = i,
					command = lambda: self.radio_changed(self.releaseaction, self.releasenum))
			r.grid(column = 4, row = i, sticky = W)
		self.should_notify = True

	def on_props_changed(self, *args):
		can_notify = self.scancode.get().isnumeric() and \
			self.releasearg.get() not in ["", "-"] and \
			self.pressarg.get() not in ["", "-"]
		if self.should_notify and can_notify:
			self.notify()

	def radio_changed(self, act, entry):
		if act.get() == 0:
			entry.config(state = DISABLED)
			self.scentry.focus_set()
		else:
			entry.config(state = NORMAL)
			entry.focus_set()
			entry.selection_range(0, END)
		if act.get() == Action.Abs:
			try:
				i = int(entry.var.get())
			except ValueError:
				i = 0
			if i <= 0:
				entry.var.set("0")
		if self.should_notify:
			self.on_props_changed()

	def validate_scancode(self, text):
		return (text.isnumeric() and int(text) < 256) or len(text) == 0

	def validate_act(self, act, text):
		a = act.get()
		if len(text) == 0:
			return True
		elif a == Action.Rel and text == "-":
			return True
		elif a == Action.Abs and text == "-":
			return False
		else:
			try:
				n = int(text)
			except:
				return False
			if a == Action.Rel:
				return n >= -16 and n <= 16
			else:
				return n >= 0 and n <= 16

	def load_keydef(self, key):
		old_should = self.should_notify
		self.should_notify = False
		self.scancode.set(key.scancode)
		self.pressaction.set(key.press.kind)
		self.pressarg.set(key.press.arg)
		self.releaseaction.set(key.release.kind)
		self.releasearg.set(key.release.arg)
		self.radio_changed(self.pressaction, self.pressnum)
		self.radio_changed(self.releaseaction, self.releasenum)
		self.should_notify = old_should
		self.focus()

	def get_keydef(self):
		try:
			sc = int(self.scancode.get())
		except ValueError:
			sc = 0
		pr = Action(self.pressaction.get(), int(self.pressarg.get()))
		re = Action(self.releaseaction.get(), int(self.releasearg.get()))
		return KeyDef(sc, press = pr, release = re)

	def focus(self):
		self.scentry.focus_set()
		self.scentry.selection_range(0, END)

class MainWindow:
	def __init__(self, master):
		# FIXME: read params from xml...
		self.cur_filename = None
		self.modified = False
		self.layout = Layout(64, 4)
		master.wm_geometry("800x600+0+0")
		self.master = master
		self.menu = MainMenu(master, self.on_menu_action)
		master.config(menu = self.menu)

		self.toolbar = Frame(master, bd = 1, relief = RAISED)
		self.toolbar.pack(side = TOP, fill = X)
		b = Button(self.toolbar, text = "new", width = 6, command = self.callback)
		b.pack(side = LEFT, padx = 1, pady = 1)
		b = Button(self.toolbar, text = "open", width = 6, command = self.callback)
		b.pack(side = LEFT, padx = 1, pady = 1)
		self.layer = IntVar(master)
		self.layer.set(0)
		fr = Frame(self.toolbar)
		fr.pack(side = RIGHT, padx = 1, pady = 1)
		l = Label(fr, text = "Layer: ")
		l.grid(column = 0, row = 0)
		ls = OptionMenu(fr, self.layer, *range(0, 16), command = self.on_change_layer)
		ls.grid(column = 1, row = 0)

		self.mainframe = Frame(master, relief = GROOVE)
		self.mainframe.pack(side = TOP, fill = BOTH, expand = True)

		self.status = StatusBar(master)
		self.status.pack(side = BOTTOM, fill = X)

		self.split = 0.7
		self.topframe = Frame(self.mainframe, bd = 1, relief = FLAT)
		self.topframe.bind("<Configure>", self.configure_event)
		self.bottomframe = Frame(self.mainframe, bd = 1, relief = SUNKEN)
		self.adjuster = Frame(self.mainframe, bd = 2, relief = RAISED, width = 8, height = 8)
		self.adjuster.bind("<B1-Motion>", self.adjust)
		self.place_frames()

		self.kbframe = KeyboardFrame(self.topframe, self.on_key_chosen)
		self.kbframe.load_xml("gh60.xml")

		self.props = PropsFrame(self.bottomframe, self.on_props_changed)
		self.on_change_layer(self.layer.get())

	def configure_event(self, event):
		ratio = float(self.kbframe.kwidth) / self.kbframe.kheight
		myratio = float(self.topframe.winfo_width()) / self.topframe.winfo_height()
		if myratio > ratio:
			h = self.topframe.winfo_height()
			w = h * ratio
		else:
			w = self.topframe.winfo_width()
			h = w / ratio
		self.kbframe.place(
				anchor = CENTER,
				width = w, height = h,
				relx = 0.5, rely = 0.5
		)

	def place_frames(self):
		self.topframe.place(y = 0, relheight = self.split, relwidth = 1)
		self.bottomframe.place(rely = self.split, relheight = 1.0-self.split, relwidth = 1)
		self.adjuster.place(relx = 0.9, rely = self.split, anchor = E)

	def adjust(self, event):
		height = self.topframe.winfo_height() + self.bottomframe.winfo_height()
		split = self.split + float(event.y) / height
		if split > 0.3 and split < 0.9:
			self.split = split
			self.place_frames()

	def say_hi(self):
		print("hi there, everyone!")

	def callback(self):
		self.status.set("hello, %i", 4)

	def on_key_chosen(self, no):
		if no is None:
			self.props.pack_forget()
		else:
			self.props.pack(side = TOP, fill = X)
			kd = self.layout[self.layer.get(), no]
			self.props.load_keydef(kd)

	def on_props_changed(self):
		kd = self.props.get_keydef()
		self.kbframe.update_button(self.kbframe.get_current_btn(), kd)
		self.layout[self.layer.get(), self.kbframe.get_current_btn()] = kd
		self.modified = True
		if self.cur_filename is not None:
			self.menu.set_save_state(True)

	def on_change_layer(self, l):
		# FIXME: take that from xml
		for b in self.kbframe.buttons.values():
			try:
				kd = self.layout[l, b.iden]
				self.kbframe.update_button(b.iden, kd)
			except KeyError:
				pass
		# reload button props on the new layer
		self.on_key_chosen(self.kbframe.get_current_btn())
		if sys.platform.startswith("win"):
			for b in self.kbframe.buttons.values():
				b.do_layout()

	def on_menu_action(self, cmd):
		if cmd == "saveas":
			fname = asksaveasfilename(filetypes =
					(("Keyboard layout files", "*.lay"), ("All files", "*.*"))
			)
			if fname == "":
				return
			try:
				f = open(fname, "wb")
				f.write(self.layout.binary())
				f.close()
				self.status.set("Saved as: %s.", fname)
				self.cur_filename = fname
				self.menu.set_save_state(False)
				self.modified = False
			except:
				self.status.set("Failed to write file: %s!", fname)
		elif cmd == "save":
			f = open(self.cur_filename, "wb")
			f.write(self.layout.binary())
			f.close()
			self.status.set("Saved.")
			self.menu.set_save_state(False)
			self.modified = False
		elif cmd == "open":
			fname = askopenfilename(filetypes =
					(("Keyboard layout files", "*.lay"), ("All files", "*.*"))
			)
			if fname == "":
				return
			try:
				f = open(fname, "rb")
				f.read()
			except:
				pass
		elif cmd == "exit":
			if self.modified:
				ans = askyesnocancel("Close", "Save modified layout?")
				if ans is None:
					return
				elif ans and self.cur_filename is not None:
					self.on_menu_action("save")
				elif ans and self.cur_filename is None:
					self.on_menu_action("saveas")
			self.master.destroy()


class MainMenu(Menu):
	def __init__(self, master, command):
		super(MainMenu, self).__init__(master)

		self.filemenu = Menu(self, tearoff = False)
		self.add_cascade(label = "File", menu = self.filemenu)
		self.filemenu.add_command(label = "New", command = self.callback)
		self.filemenu.add_command(label = "Open...", command = lambda: command("open"))
		self.filemenu.add_command(label = "Save", command = lambda: command("save"))
		self.filemenu.add_command(label = "Save as...", command = lambda: command("saveas"))
		self.filemenu.add_separator()
		self.filemenu.add_command(label = "Exit", command = lambda: command("exit"))
		self.set_save_state(False)

		helpmenu = Menu(self, tearoff = False)
		self.add_cascade(label = "Help", menu = helpmenu)
		helpmenu.add_command(label = "About...", command = self.callback)

	def callback(self):
		pass

	# Public API starts here...

	def set_save_state(self, st):
		if st:
			self.filemenu.entryconfig(2, state = NORMAL)
		else:
			self.filemenu.entryconfig(2, state = DISABLED)


class StatusBar(Frame):
	def __init__(self, master):
		Frame.__init__(self, master)
		self.label = Label(self, bd = 1, relief = SUNKEN, anchor = W)
		self.label.pack(fill = X)

	def set(self, format, *args):
		self.label.config(text = format % args)
		self.label.update_idletasks()

	def clear(self):
		self.label.config(text = "")
		self.label.update_idletasks()

root = Tk()

app = MainWindow(root)

root.mainloop()
