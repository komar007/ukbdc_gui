#!/usr/bin/env python3
from tkinter import *
from tkinter.filedialog import *
from tkinter.messagebox import *
import sys
import xml.etree.ElementTree as ET

from ukbdc_lib.layout import *
from ukbdc_lib.ukbdc import UKBDC

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
		self.fgcol = "black"
		self.inhfgcol = "#999999"
		self.prcol = "red"
		self.recol = "blue"
		self.nocol = "#555555"
		self.no = Label(self, text = self.iden, fg = self.nocol, font = (None, 7, "normal"))
		self.pr = Label(self, text = "", fg = self.prcol, font = (None, 7, "normal"))
		self.re = Label(self, text = "", fg = self.recol, font = (None, 7, "normal"))
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

	def update_press_label(self, act, inherited):
		self.pr.config(text = self.generate_label("↓", act))
		if inherited:
			self.pr.config(fg = self.inhfgcol)
		else:
			self.pr.config(fg = self.prcol)

	def update_release_label(self, act, inherited):
		self.re.config(text = self.generate_label("↑", act))
		if inherited:
			self.re.config(fg = self.inhfgcol)
		else:
			self.re.config(fg = self.recol)

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
		self.command(button.iden)

	def on_click_nothing(self, w):
		if self.cur_button is not None:
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
		b.config(text = str(kd.nicename))
		if kd.inherited:
			b.config(fg = b.inhfgcol, relief = SUNKEN)
			b.no.config(fg = b.inhfgcol)
		else:
			b.config(fg = b.fgcol, relief = RAISED)
			b.no.config(fg = b.nocol)
		b.update_press_label(kd.press, kd.inherited)
		b.update_release_label(kd.release, kd.inherited)

	def get_current_btn(self):
		if self.cur_button is None:
			return None
		else:
			return self.cur_button.iden

	def set_current_btn(self, no):
		if self.cur_button is not None:
			self.cur_button.dehighlight()
			self.cur_button = None
		if no is not None:
			self.cur_button = self.buttons[no]
			self.cur_button.highlight()

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
		self.widgets = []
		top = Frame(self)
		top.pack(side = TOP, fill = X)
		l = Label(top, text = "mode: ")
		l.grid(column = 0, row = 0, sticky = W)
		self.mode = IntVar()
		self.mode.set(0)
		self.moderadios = []
		for i, t in enumerate(["defined", "inherited"]):
			r = Radiobutton(top, text = t, variable = self.mode, value = i,
					command = self.mode_changed)
			r.grid(column = 1+i, row = 0, sticky = W)
			self.moderadios.append(r)
		l = Label(top, text = "scancode: ")
		l.grid(column = 0, row = 1)
		self.scancode = StringVar()
		self.scancode.set(0)
		self.scancode.trace("w", self.on_props_changed)
		self.scentry = Entry(top, textvariable = self.scancode)
		self.scentry.grid(column = 1, row = 1, columnspan = 2)
		self.widgets.append(self.scentry)
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
		self.widgets.append(self.pressnum)
		for i, t in enumerate(self.kinds):
			r = Radiobutton(acts, text = t, variable = self.pressaction, value = i,
					command = lambda: self.radio_changed(self.pressaction, self.pressnum))
			r.grid(column = 1, row = i, sticky = W)
			self.widgets.append(r)
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
		self.widgets.append(self.releasenum)
		for i, t in enumerate(self.kinds):
			r = Radiobutton(acts, text = t, variable = self.releaseaction, value = i,
					command = lambda: self.radio_changed(self.releaseaction, self.releasenum))
			r.grid(column = 4, row = i, sticky = W)
			self.widgets.append(r)
		self.should_notify = True

	def mode_changed(self):
		if self.mode.get() == 0:
			for w in self.widgets:
				w.config(state = NORMAL)
		else:
			for w in self.widgets:
				w.config(state = DISABLED)
		# fix action enties
		self.update_actions_form(self.pressaction, self.pressnum)
		self.update_actions_form(self.releaseaction, self.releasenum)
		if self.should_notify:
			self.on_props_changed()

	def on_props_changed(self, *args):
		if not self.scancode_correct(self.scancode.get()):
			self.scentry.config(bg = "#FF6D72")
		else:
			self.scentry.config(bg = self.cget("bg"))

		can_notify = self.scancode_correct(self.scancode.get()) and \
			self.releasearg.get() not in ["", "-"] and \
			self.pressarg.get() not in ["", "-"]
		if self.should_notify and can_notify:
			self.notify()

	def radio_changed(self, act, entry):
		self.update_actions_form(act, entry)
		if act.get() == 0:
			self.scentry.focus_set()
		else:
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

	def update_actions_form(self, act, entry):
		if act.get() == 0:
			entry.config(state = DISABLED)
		else:
			entry.config(state = NORMAL)


	def scancode_correct(self, text):
		if text[0:2] == "0x":
			try:
				return 0 <= int(text, 16) <= 255
			except ValueError:
				return False
		else:
			valid_mnemonics = mnemonics.values()
			return text in valid_mnemonics

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
		self.scancode.set(key.nicename)
		self.pressaction.set(key.press.kind)
		self.pressarg.set(key.press.arg)
		self.releaseaction.set(key.release.kind)
		self.releasearg.set(key.release.arg)
		if key.inherited:
			self.mode.set(1)
		else:
			self.mode.set(0)
		self.mode_changed()
		self.update_actions_form(self.pressaction, self.pressnum)
		self.update_actions_form(self.releaseaction, self.releasenum)
		self.should_notify = old_should
		self.focus()

	def get_keydef(self):
		if self.mode.get() == 1:
			return None
		scancode = self.scancode.get()
		try:
			if scancode[0:2] == "0x":
				sc = int(self.scancode.get(), 16)
			else:
				sc = self.scancode.get()
		except ValueError:
			sc = self.scancode.get()
		pr = Action(self.pressaction.get(), int(self.pressarg.get()))
		re = Action(self.releaseaction.get(), int(self.releasearg.get()))
		return KeyDef(scancode = sc, press = pr, release = re)

	def set_inheritable(self, inh):
		if inh:
			self.moderadios[1].config(state = NORMAL)
		else:
			self.moderadios[1].config(state = DISABLED)

	def focus(self):
		self.scentry.selection_range(0, END)
		self.scentry.focus_set()

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

		topbar = Frame(master, bd = 1, relief = RAISED)
		topbar.pack(side = TOP, fill = X)
		self.toolbar = Toolbar(topbar, self.on_menu_action, self.set_tip)
		self.toolbar.grid(column = 0, row = 0, stick = W+N+S)
		self.layer = IntVar(master)
		self.layer.set(0)
		fr = Frame(topbar)
		fr.grid(column = 1, row = 0, stick = E+N+S)
		l = Label(fr, text = "Layer: ")
		l.grid(column = 0, row = 0, stick = N+S+W+E)
		Grid.rowconfigure(fr, 0, weight = 1)
		ls = OptionMenu(fr, self.layer, *range(0, 16), command = self.on_change_layer)
		ls.grid(column = 1, row = 0)
		Grid.columnconfigure(topbar, 0, weight = 1)
		Grid.columnconfigure(topbar, 1, weight = 1)

		f = Frame(master)
		f.pack(side = TOP, fill = X)
		l = Label(f, text = "Inherits from layer: ")
		l.pack(side = LEFT)
		self.inh = StringVar()
		self.inh.set("none")
		self.inhopt = OptionMenu(f, self.inh, "none", command = self.on_change_inh)
		self.inhopt.pack(side = LEFT)
		self.layprops = f

		self.status = StatusBar(master)
		self.status.pack(side = BOTTOM, fill = X)

		self.topframe = Frame(master, bd = 1, relief = FLAT)
		self.topframe.bind("<Configure>", self.configure_event)
		self.bottomframe = Frame(master, bd = 1, relief = SUNKEN)

		self.topframe.pack(side = TOP, fill = BOTH, expand = True)
		self.bottomframe.pack(side = BOTTOM, fill = BOTH)

		self.kbframe = KeyboardFrame(self.topframe, self.on_key_chosen)
		master.bind("<Escape>", lambda x: self.on_key_chosen(None))
		self.kbframe.load_xml("gh60.xml")

		self.props = PropsFrame(self.bottomframe, self.on_props_changed)
		self.on_change_layer(self.layer.get())

	def set_tip(self, tip):
		if tip is None:
			self.status.clear_tip()
		else:
			self.status.set_tip(tip)

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

	def say_hi(self):
		print("hi there, everyone!")

	def callback(self):
		self.status.set("hello, %i" % 4)

	def set_save_state(self, st):
		self.menu.set_save_state(st)
		self.toolbar.set_save_state(st)

	def on_key_chosen(self, no):
		self.kbframe.set_current_btn(no)
		if no is None:
			self.props.pack_forget()
		else:
			self.props.pack(side = TOP, fill = X)
			kd = self.layout[self.layer.get(), no]
			self.props.load_keydef(kd)

	def on_change_inh(self, lay):
		if lay == "none":
			lay = -1
		else:
			lay = int(lay)
		self.layout.parents[self.layer.get()] = lay
		self.on_change_layer(self.layer.get())
		self.modified = True
		self.status.set("Layout modified")
		if self.cur_filename is not None:
			self.set_save_state(True)

	def on_props_changed(self):
		cur_no = self.kbframe.get_current_btn()
		kd = self.props.get_keydef()
		if kd is None:
			kd = KeyDef(layout = self.layout, no = cur_no, layer = self.layer.get(),
					inherited = True)
		self.kbframe.update_button(cur_no, kd)
		self.layout[self.layer.get(), cur_no] = kd
		self.modified = True
		self.status.set("Layout modified")
		if self.cur_filename is not None:
			self.set_save_state(True)

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
		self.inhopt.pack_forget()
		opts = [str(i) for i in range(0, l)]
		if l == 0:
			opts = ["none"] + opts
		self.inhopt = OptionMenu(self.layprops, self.inh, *opts, command = self.on_change_inh)
		self.inhopt.pack(side = LEFT)
		if self.layout.parents[l] == -1:
			self.inh.set("none")
		else:
			self.inh.set(str(self.layout.parents[l]))
		self.props.set_inheritable(self.inh.get() != "none")

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
				self.status.set("Saved as: %s." % fname)
				self.cur_filename = fname
				self.set_save_state(False)
				self.modified = False
			except Exception as e:
				self.status.set("Failed to write file %s: %s!" % (fname, str(e)))
		elif cmd == "save":
			try:
				f = open(self.cur_filename, "wb")
				f.write(self.layout.binary())
				f.close()
				self.status.set("Saved.")
				self.set_save_state(False)
				self.modified = False
			except Exception as e:
				self.status.set("Failed to write file %s: %s!" % (fname, str(e)))
		elif cmd == "open":
			if self.modified:
				cont = self.ask_save()
				if not cont:
					return
			fname = askopenfilename(filetypes =
					(("Keyboard layout files", "*.lay"), ("All files", "*.*"))
			)
			if fname == "":
				return
			try:
				f = open(fname, "rb")
				data = f.read()
				self.layout = Layout.from_binary(data)
				self.layer.set(0)
				self.on_change_layer(0)
				self.cur_filename = fname
				self.set_save_state(False)
				self.on_key_chosen(None)
				self.status.set("Opened file: %s" % fname)
			except Exception as e:
				self.status.set("Error opening file: %s" % str(e))
		elif cmd == "new":
			if self.modified:
				cont = self.ask_save()
				if not cont:
					return
			# FIXME: take that from xml
			self.layout = Layout(64, 4)
			self.layer.set(0)
			self.on_change_layer(0)
			self.cur_filename = None
			self.set_save_state(False)
			self.status.set("Created new layout")
		elif cmd == "exit":
			if self.modified:
				cont = self.ask_save()
				if not cont:
					return
			self.master.destroy()
		elif cmd == "program":
			u = UKBDC()
			try:
				binary = self.layout.binary(fordevice = True)
				u.attach()
				u.program_layout(binary)
				u.detach()
				self.status.set("Programmed %i bytes of layout" % len(binary))
			except Exception as e:
				self.status.set("Programming error: %s" % str(e))

	def ask_save(self):
		ans = askyesnocancel("Layout modified", "Save modified layout?")
		if ans is None:
			return False
		elif ans and self.cur_filename is not None:
			self.on_menu_action("save")
		elif ans and self.cur_filename is None:
			self.on_menu_action("saveas")
		return True


class MainMenu(Menu):
	def __init__(self, master, command):
		super(MainMenu, self).__init__(master)

		self.filemenu = Menu(self, tearoff = False)
		self.add_cascade(label = "File", menu = self.filemenu)
		self.filemenu.add_command(label = "New", command = lambda: command("new"))
		self.filemenu.add_command(label = "Open...", command = lambda: command("open"))
		self.filemenu.add_command(label = "Save", command = lambda: command("save"))
		self.filemenu.add_command(label = "Save as...", command = lambda: command("saveas"))
		self.filemenu.add_separator()
		self.filemenu.add_command(label = "Exit", command = lambda: command("exit"))
		self.set_save_state(False)

		devmenu = Menu(self, tearoff = False)
		self.add_cascade(label = "Device", menu = devmenu)
		devmenu.add_command(label = "Program", command = lambda: command("program"))

		helpmenu = Menu(self, tearoff = False)
		self.add_cascade(label = "Help", menu = helpmenu)
		helpmenu.add_command(label = "About...", command = lambda: command("about"))

	# Public API starts here...

	def set_save_state(self, st):
		if st:
			self.filemenu.entryconfig(2, state = NORMAL)
		else:
			self.filemenu.entryconfig(2, state = DISABLED)

class Toolbar(Frame):
	def __init__(self, master, command, set_tip):
		super(Toolbar, self).__init__(master)
		self.set_tip = set_tip

		img = PhotoImage(file = "icons/save.gif")
		self.save = Button(self,
				text = "save", image = img,
				command = lambda: command("save")
		)
		self.save.tooltip = "Save current layout"
		self.save.bind("<Enter>", self.on_enter)
		self.save.bind("<Leave>", self.on_leave)
		self.save.img = img
		self.save.pack(side = LEFT, padx = 1, pady = 1)
		img = PhotoImage(file = "icons/program.gif")
		self.program = Button(self,
				text = "program", image = img,
				command = lambda: command("program")
		)
		self.program.tooltip = "Write layout to device"
		self.program.bind("<Enter>", self.on_enter)
		self.program.bind("<Leave>", self.on_leave)
		self.program.img = img
		self.program.pack(side = LEFT, padx = 1, pady = 1)
		self.set_save_state(False)

	def on_enter(self, event):
		self.set_tip(event.widget.tooltip)

	def on_leave(self, event):
		self.set_tip(None)

	def set_save_state(self, st):
		if st:
			self.save.config(state = NORMAL)
		else:
			self.save.config(state = DISABLED)


class StatusBar(Frame):
	def __init__(self, master):
		Frame.__init__(self, master)
		self.label = Label(self, bd = 1, relief = SUNKEN, anchor = W)
		self.label.pack(side = LEFT, fill = BOTH, expand = True)
		self.last_status = ""

	def set(self, status):
		self.last_status = status
		self.label.config(text = status)

	def set_tip(self, tip):
		self.label.config(text = tip)

	def clear_tip(self):
		self.label.config(text = self.last_status)

	def clear(self):
		self.label.config(text = "")
		self.last_status = ""

root = Tk()

app = MainWindow(root)

root.mainloop()
