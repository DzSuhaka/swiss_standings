from Tkinter import *
import Tkinter, Tkconstants, tkFileDialog
from functools import partial
from ScrolledText import *
import tkMessageBox
import standings_logic as standings_logic
import sys
import hex_events_handler as heh
import json

class TournamentWindow():
    def __init__(self):
        self.very_left_frame = Frame(root)
        self.canvas = Canvas(self.very_left_frame, bd=0, highlightthickness=0)

        if sys.platform == 'win32':
            self.canvas.bind_all("<MouseWheel>", lambda event: self.canvas.yview_scroll(-1*(event.delta/120), "units"))
        else:
            self.canvas.bind_all("<4>", lambda event: self.canvas.yview_scroll(-1, "units"))
            self.canvas.bind_all("<5>", lambda event: self.canvas.yview_scroll(1, "units"))

        self.right_frame = Frame(root)
        self.scrollbar = Scrollbar(self.very_left_frame, command=self.canvas.yview, orient=VERTICAL)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        split = 0.5
        self.very_left_frame.place(rely=0, relheight=1, relwidth=split)
        self.scrollbar.pack(side=RIGHT, fill=Y, ipadx=2, expand=False)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=TRUE)
        self.right_frame.place(relx=split, relwidth=1.0-split, relheight=1)

        self.left_frame = Frame(self.canvas)
        self.lf_id = self.canvas.create_window(0, 0, window=self.left_frame, anchor=NW)

        # track changes to the canvas and frame width and sync them,
        # also updating the scrollbar
        def _configure_interior(event):
            # update the scrollbars to match the size of the inner frame
            size = (self.left_frame.winfo_reqwidth(), self.left_frame.winfo_reqheight())
            self.canvas.config(scrollregion="0 0 %s %s" % size)
            if self.left_frame.winfo_reqwidth() != self.canvas.winfo_width():
                # update the canvas's width to fit the inner frame
                self.canvas.config(width=self.left_frame.winfo_reqwidth())
        self.left_frame.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if self.left_frame.winfo_reqwidth() != self.canvas.winfo_width():
                # update the inner frame's width to fill the canvas
                self.canvas.itemconfigure(self.lf_id, width=self.canvas.winfo_width())
        self.canvas.bind('<Configure>', _configure_canvas)


        self.gc = []
        self.labels = {}
        self.left_labels = {}
        self.bg_colors = {}

        weights = [5, 1, 1, 1, 5]

        for i in xrange(0,5):
	    self.right_frame.grid_columnconfigure(i, weight=weights[i])

    def update_and_reload(self, match, result):
        match.fake_match(result)
        self.reload(full=False)
        self.colorize()

    def colorize(self, undo=False):
        for p in self.labels:
            if p not in self.bg_colors:
                self.left_labels[p].configure(bg="LightGoldenrod1")
        for p in self.bg_colors:
            if p in self.labels:
                self.labels[p].configure(bg=self.right_frame.cget("bg") if undo else self.bg_colors[p])
            self.left_labels[p].configure(bg=self.right_frame.cget("bg") if undo else self.bg_colors[p])

    def change_colors(self, player, event):
        self.colorize(undo=True)
        self.bg_colors = {}
        self.bg_colors[player.name]="chartreuse"
        for opp in player.opponents:
            self.bg_colors[opp.name]="light salmon"
        self.colorize()

    def reload_right_frame(self):
        for widget in self.right_frame.winfo_children():
            widget.destroy()
        self.labels = {}
        j = 0
        for match in standings_logic.t.ongoing_matches:
            self.gc.append(IntVar())
            for i in xrange(0,5):
                if i%4:
                    Radiobutton(self.right_frame, text='', value=i, variable=self.gc[-1], command=partial(self.update_and_reload, match, i-1)).grid(row=j, column=i)
                else:
                    name = match.players[i%3].name
                    self.labels[name] = Label(self.right_frame, text=name)
                    self.labels[name].grid(row=j, column=i, sticky = W if i else E)
            j+=1

    def reload(self, full=True):
        if full:
            for widget in self.left_frame.winfo_children():
                widget.destroy()
            self.left_labels = {}
        else:
            for widget in self.left_frame.winfo_children():
                widget.forget()
            
        i=0
        for p in standings_logic.t.get_standings():
            if full:
                self.left_labels[p.name] = Label(self.left_frame)
                self.left_labels[p.name].bind("<Button-1>", partial(self.change_colors, p))
            i+=1
            self.left_labels[p.name].configure(text="{:>3}{}".format(i, p.info))
            self.left_labels[p.name].pack()

root = Tk(className='Hex Tournament Helper')
root.title("Hex Tournament Helper")

root.option_add("*Label.font", "-*-{}-*-*-*--*-150".format("Lucida Console" if sys.platform == 'win32' else "Monaco" if sys.platform == "darvin" else "Ubuntu Mono"))

tw = TournamentWindow()

menubar = Menu(root)

def _check():
    if apiha.new_m:
        root.title("Hex Tournament Helper. A new event has been found, reload the tournament.")
        filemenu.entryconfigure("Reload tournament", state="active")
        #menubar.entryconfigure("Reload tournament", state="active")
    else:
        root.after(5000, _check)
        filemenu.entryconfigure("Reload tournament", state="disabled")
        #menubar.entryconfigure("Reload tournament", state="disabled")

def _reload(msg=''):
    if not msg:
        msg = apiha.last_tournament_msg
        filemenu.entryconfigure("Reload tournament", state="disabled")
        root.title("Hex Tournament Helper")
        _check()
    standings_logic.reload(msg)
    tw.reload()
    tw.reload_right_frame()

def _open():
    _file = tkFileDialog.askopenfilename(initialdir = "./.", title = "Select file", filetypes = (("hex tournament dumps","*.htd"), ("all files","*.*")))
    if _file:
        f = open(_file, 'r')
        msg = f.read()
        f.close()
        _reload(json.loads(msg))

def _save():
    _file = tkFileDialog.asksaveasfilename(initialdir = "./.", title = "Select file", filetypes = (("hex tournament dumps","*.htd"), ("all files","*.*")))
    if _file:
        f = open(_file, 'w')
        msg = apiha.last_tournament_msg
        f.write(json.dumps(msg))
        f.close()

filemenu = Menu(menubar, tearoff=0)
filemenu.add_command(label="Reload tournament", command=_reload)
filemenu.add_separator()
filemenu.add_command(label="Open tournament", command=_open)
filemenu.add_command(label="Save tournament as...", command=_save)
menubar.add_cascade(label="File", menu=filemenu)

def _simulate(n=15):
    sim_w = Tkinter.Toplevel(root)
    sim_w.wm_title("Sim")
    sim_w.geometry('300x300')
    sc_t = ScrolledText(sim_w, font="-*-{}-*-*-*--*-150".format("Lucida Console" if sys.platform == 'win32' else "Monaco" if sys.platform == "darvin" else "Ubuntu Mono"))
    sc_t.pack(fill=BOTH, expand=True)
    for p in standings_logic.t.gps(n):
        sc_t.insert(END, '{:>20} - {:6.2f}%\n'.format(*p))
        sc_t.see(END)
        sc_t.update()

#  def _debug(n=4):
#      for i in xrange(n):
#          player = standings_logic.t.get_standings()[i]
#          sim_w = Tkinter.Toplevel(root)
#          sim_w.wm_title(player.name)
#          sim_w.geometry('600x200')
#          sc_t = ScrolledText(sim_w, font="-*-{}-*-*-*--*-150".format("Lucida Console" if sys.platform == 'win32' else "Monaco" if sys.platform == "darvin" else "Ubuntu Mono"))
#          sc_t.pack(fill=BOTH, expand=True)
#          sc_t.insert(END, '{}\n'.format(player.info))
#          sc_t.see(END)
#          sc_t.update()
#          for opp in player.opponents:
#              sc_t.insert(END, '{} | {}\n'.format(opp.info, opp.mr))
#              sc_t.see(END)
#              sc_t.update()
#  

magicmenu = Menu(menubar, tearoff=0)
magicmenu.add_command(label="Simulate", command=_simulate)
#  magicmenu.add_command(label="Debug", command=_debug)
menubar.add_cascade(label="Simulate", menu=magicmenu)

apiha = heh.HexApiListener()
root.config(menu=menubar)
root.geometry('1000x700')
root.resizable(width=True, height=True)
_check()

def on_closing():
    if tkMessageBox.askokcancel("Quit", "Do you want to quit?"):
        apiha._stop_listening()
        root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

root = mainloop()
