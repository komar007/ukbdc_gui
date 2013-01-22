#!/usr/bin/env python3
from tkinter import *
from tkinter.filedialog import *
from tkinter.messagebox import *
import sys
import xml.etree.ElementTree as ET

from ukbdc_lib.layout import *
from ukbdc_lib.ukbdc import UKBDC
from ukbdc_lib.mnemonics import mnemonics

from buttons import Buttons

def platform_windows():
	return sys.platform.startswith("win")

class KeyButton(Button):
	_fgcol    = "black"   # text color
	_inhfgcol = "#999999" # text color if inherited
	_prcol    = "red"     # press action label color
	_recol    = "blue"    # release action label color
	_nocol    = "#555555" # number label color
	_hibgcol  = "#90EE90" # background color if highlighted
	_ahibgcol = "#60FF60" # mouse-over background color if highlighted
	_labfont  = (None, 7, "normal") # label font
	# on windows, reset active highlighted color, because windows does not highlight
	if platform_windows():
		_ahibgcol = _hibgcol

	def __init__(self, master, number, command = lambda: False):
		super(KeyButton, self).__init__(master, command = self._on_click)
		self._ = {} # subwidgets
		self._mouse_over = False
		self._number = number
		self._command = command
		self._bgcol = self.cget("bg") # remember bg color for later use
		self._abgcol = self.cget("activebackground") # ... and mouse-over background color
		self.bind("<Leave>", self._on_leave)
		self.bind("<Enter>", self._on_enter)
		# make labels
		self._['l_no'] = Label(self, text = self.number,
				fg = self._nocol, font = self._labfont)
		self._['l_pr'] = Label(self, text = "",
				fg = self._prcol, font = self._labfont)
		self._['l_re'] = Label(self, text = "",
				fg = self._recol, font = self._labfont)
		# make sure clicking on labels works
		for label in self._.values():
			label.bind("<Button-1>", lambda x: self.invoke())
		self._layout_labels()
		for x in range(3):
			Grid.columnconfigure(self, x, weight = 1)
			Grid.rowconfigure(self, x, weight = 1)
		Grid.columnconfigure(self, 1, weight = 10)
		Grid.rowconfigure(self, 1, weight = 10)

	def _layout_labels(self):
		# windows quirk hack
		self._['l_no'].grid_forget()
		self._['l_pr'].grid_forget()
		self._['l_re'].grid_forget()
		self._['l_no'].grid(column = 0, row = 0, sticky = N+W)
		self._['l_pr'].grid(column = 0, row = 2, sticky = S+W)
		self._['l_re'].grid(column = 2, row = 2, sticky = S+E)

	def _on_enter(self, event):
		self._mouse_over = True
		# update labels to have the same background as button
		color = self.cget("activebackground")
		self._set_labels_color(color)

	def _on_leave(self, event):
		self._mouse_over = False
		# update labels to have the same background as button
		color = self.cget("background")
		self._set_labels_color(color)
		# windows hack
		if platform_windows():
			self._layout_labels()

	def _on_click(self):
		# run callback
		self._command(self)

	def _set_labels_color(self, color):
		for label in self._.values():
			label.config(bg = color)

	# returns label for an action (relative or absolute)
	def _generate_label(self, prefix, action):
		try:
			arg = str(action.arg)
		except ValueError:
			arg = ""
		if action.kind == Action.Rel:
			if action.arg >= 0:
				s = "+" + arg
			else:
				s = arg
			n = s
		elif action.kind == Action.Abs:
			n = arg
		else:
			n = ""
		if n == "":
			return ""
		else:
			return prefix + n

	def _update_press_label(self, action, inherited):
		self._['l_pr'].config(text = self._generate_label("↓", action))
		if inherited:
			self._['l_pr'].config(fg = self._inhfgcol)
		else:
			self._['l_pr'].config(fg = self._prcol)

	def _update_release_label(self, action, inherited):
		self._['l_re'].config(text = self._generate_label("↑", action))
		if inherited:
			self._['l_re'].config(fg = self._inhfgcol)
		else:
			self._['l_re'].config(fg = self._recol)

	# Public API starts here...

	@property
	def number(self):
		return self._number

	def highlight(self):
		self.config(activebackground = self._ahibgcol, bg = self._hibgcol)
		if self._mouse_over:
			self._set_labels_color(self._ahibgcol)
		else:
			self._set_labels_color(self._hibgcol)

	def dehighlight(self):
		self.config(activebackground = self._abgcol, bg = self._bgcol)
		if self._mouse_over:
			self._set_labels_color(self._abgcol)
		else:
			self._set_labels_color(self._bgcol)

	def set_keydef(self, kd):
		self.config(text = str(kd.nicename))
		if kd.inherited:
			self.config(fg = self._inhfgcol, relief = SUNKEN)
			self._['l_no'].config(fg = self._inhfgcol)
		else:
			self.config(fg = self._fgcol, relief = RAISED)
			self._['l_no'].config(fg = self._nocol)
		self._update_press_label(kd.press, kd.inherited)
		self._update_release_label(kd.release, kd.inherited)

class KeyboardFrame(Frame):
	# on_button_pressed will receive the button number
	# or Null if a button was deselected
	def __init__(self, master, on_button_pressed):
		super(KeyboardFrame, self).__init__(master)
		self._ = {}
		self._button_callback = on_button_pressed
		self._cur_button = None
		# initialize actual keyboard dimensions to (1, 1),
		# because we don't know the dimensions yet
		self.bind("<Button-1>", self._on_click_nothing)
		self.bind("<Configure>", self._on_change_size)
		self._['f_cont'] = Frame(self)

	# set keyboard containter size to a fixed ratio, and fill the frame with it
	def _on_change_size(self, event):
		ratio = float(self._bdefs.width) / self._bdefs.height
		myratio = float(self.winfo_width()) / self.winfo_height()
		if myratio > ratio:
			h = self.winfo_height()
			w = h * ratio
		else:
			w = self.winfo_width()
			h = w / ratio
		self._['f_cont'].place(
				anchor = CENTER,
				width = w, height = h,
				relx = 0.5, rely = 0.5)

	# triggered by one of the contained buttons
	# pass button press info to parent to decide what to do with it
	def _on_button_pressed(self, button):
		self._button_callback(button.number)

	def _on_click_nothing(self, event):
		if self._cur_button is not None:
			self._button_callback(None)

	def _get_btn_widget(self, no):
		return self._['b_%i' % no]

	# Public API starts here...

	def update_button(self, no, kd):
		b = self._get_btn_widget(no)
		b.set_keydef(kd)

	def get_current_btn(self):
		if self._cur_button is None:
			return None
		else:
			return self._cur_button.number

	def set_current_btn(self, no):
		if self._cur_button is not None:
			self._cur_button.dehighlight()
			self._cur_button = None
		if no is not None:
			self._cur_button = self._get_btn_widget(no)
			self._cur_button.highlight()

	# Goes to the next button. Maybe it shouldn't be here...
	def next_button(self):
		if self._cur_button is None:
			return
		nos = sorted(self._bdefs.keys())
		pos = nos.index(self._cur_button.number) + 1
		if pos >= len(nos):
			pos = 0
		self._on_button_pressed(self._get_btn_widget(nos[pos]))

	def setup_buttons(self, btns):
		self._bdefs = btns
		for no, button in btns.items():
			widget = KeyButton(self._['f_cont'], no, command = self._on_button_pressed)
			widget.grid(column = 0, row = 0, sticky = N+S+E+W)
			widget.place(
					relx = float(button.x) / btns.width,
					rely = float(button.y) / btns.height,
					relwidth = float(button.width) / btns.width,
					relheight = float(button.height) / btns.height
			)
			self._['b_%i' % no] = widget

class PropsFrame(Frame):
	kinds = ["None", "Change layer by", "Go to layer"]
	def __init__(self, master, notify = lambda: False, next_button = lambda: False):
		self.should_notify = False
		super(PropsFrame, self).__init__(master)
		self.notify = notify
		self.next_button = next_button
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
		self.scentry.bind("<FocusOut>", self.on_scentry_tab)
		self.scentry.grid(column = 1, row = 1, columnspan = 2)
		self.widgets.append(self.scentry)
		self.lhints = Label(top)
		self.lhints.grid(column = 3, row = 1)
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

		if len(self.scancode.get()) == 0:
			self.hints = []
		else:
			self.hints = list(filter(
					lambda x: x.startswith(self.scancode.get()),
					mnemonics.values())
			)
		self.lhints.config(text = " ".join(self.hints))

		can_notify = self.scancode_correct(self.scancode.get()) and \
			self.releasearg.get() not in ["", "-"] and \
			self.pressarg.get() not in ["", "-"]
		if self.should_notify and can_notify:
			self.notify()

	def on_scentry_tab(self, event):
		if len(self.hints) == 1 and self.scancode.get() != self.hints[0]:
			self.scancode.set(self.hints[0])
			self.scentry.icursor(END)
			self.scentry.focus_set()

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

		self.bottomframe = Frame(master, bd = 1, relief = SUNKEN)

		self.bottomframe.pack(side = BOTTOM, fill = BOTH)

		self.kbframe = KeyboardFrame(master, self.on_key_chosen)
		self.kbframe.pack(side = TOP, fill = BOTH, expand = True)
		master.bind("<Escape>", lambda x: self.on_key_chosen(None))

# blah
		tree = ET.parse("gh60.xml")
		keyboard = tree.getroot()
		w = int(keyboard.attrib['width'])
		h = int(keyboard.attrib['height'])
		buttons = Buttons(w, h)
		self.btn_nos = []
		for key in keyboard:
			no = int(key.attrib['id'])
			self.btn_nos.append(no)
			buttons.add_button(no,
					int(key.attrib['width']), int(key.attrib['height']),
					int(key.attrib['x']), int(key.attrib['y']))
# blah
		self.kbframe.setup_buttons(buttons)

		master.bind("<Control-Return>", lambda x: self.kbframe.next_button())

		self.props = PropsFrame(self.bottomframe,
				notify = self.on_props_changed,
				next_button = self.kbframe.next_button
		)
		self.on_change_layer(self.layer.get())

	def set_tip(self, tip):
		if tip is None:
			self.status.clear_tip()
		else:
			self.status.set_tip(tip)

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
		for b in self.btn_nos:
			try:
				kd = self.layout[l, b]
				self.kbframe.update_button(b, kd)
			except KeyError:
				pass
		# reload button props on the new layer
		self.on_key_chosen(self.kbframe.get_current_btn())
		if platform_windows():
			for b in self.kbframe.buttons.values():
				b._layout_labels()
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
