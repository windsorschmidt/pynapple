from tkinter import *
from tkinter import ttk
import tkinter.font
import random
root = Tk()

class UserInterfacePlugin:
    medVarFnt = tkinter.font.Font(family="Sans", size=10)
    bigVarFnt = tkinter.font.Font(family="Sans", size=20)
    medFixFnt = tkinter.font.Font(family="Courier", size=14)
    bigFixFnt = tkinter.font.Font(family="Courier", size=24)

    hilite_bg = "#882255"
    hilite_fg = "#ffccee"

    root.title("pynapple")
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)

    notebook = ttk.Notebook(root)
    notebook.grid(sticky="nsew", padx=4, pady=4)

    p1 = Frame(notebook);
    p1.rowconfigure(1, weight=1)
    p1.columnconfigure(0, weight=1)
    notebook.add(p1, text="Channel")

    p2 = Frame(notebook);
    p2.rowconfigure(0, weight=1)
    p2.columnconfigure(0, weight=1)
    notebook.add(p2, text="Server")

    statustxt = StringVar()
    status = Label(p1, textvariable=statustxt, font=medVarFnt)
    status.grid(sticky="ew", row=0, columnspan=2, padx=4, pady=4)

    chat = Text(p1, font=medFixFnt, state = "disabled", background = "#0a0a0a")
    chat.grid(sticky="nsew", row=1, padx=2)

    nicktxt = StringVar()
    nicks = Listbox(p1, listvariable=nicktxt, width=20)
    nicks.configure(state = "disabled", font=medFixFnt, background = "#0a0a0a")
    nicks.grid(row=1, column=1, sticky="ns", padx=2)

    cmdtxt = StringVar()
    cmd = Entry(p1, textvariable=cmdtxt, font=medFixFnt)
    cmd.grid(sticky="ew", row=2, columnspan=2, padx=4, pady=4)
    cmd.focus()

    server = Text(p2, font=medFixFnt, state = "disabled", background = "#0a0a0a")
    server.grid(sticky="nsew", padx=2, pady=2)

    def __init__(self, irc, kb):
        self.ircHandle = irc
        self.kbHandle = kb
        root.title("pynapple-irc v" + self.ircHandle.get_version())
        self.cmd.bind('<Return>', self.handle_input)
        self.maxColors = 128
        self.init_colors()
        self.ircHandle.get_status()

    def init_colors(self):
        # Called once during program initialization to generate the color tags
        # used by tk in order to display strings in color.
        self.chat.tag_configure(0, foreground = "#1B1D1E")
        self.chat.tag_configure(1, foreground = "#F92672")
        self.chat.tag_configure(2, foreground = "#82B414")
        self.chat.tag_configure(3, foreground = "#FD971F")
        self.chat.tag_configure(4, foreground = "#4E82AA")
        self.chat.tag_configure(5, foreground = "#8C54FE")
        self.chat.tag_configure(6, foreground = "#465457")
        self.chat.tag_configure(7, foreground = "#CCCCC6")
        self.server.tag_configure("server", foreground = "#CCCCC6")
        # TODO: make colors less pastel (only one of RGB values allowed > x)
        for tag in range(self.maxColors):
            rgb = [random.randint(64,255) for x in range(3)]
            colorString = '#%02x%02x%02x' % (rgb[0], rgb[1], rgb[2])
            self.chat.tag_configure(tag+8, foreground = colorString)

    def get_max_colors(self):
        return self.maxColors

    def old_set_status(self, nick, server, channel, topic):
        # TODO: merge this in to update_status()
        if (server != ""):
            a = "connected to %s," % server
            if (channel != ""):
                b = "in %s" % channel
                c = "topic: %s" % topic
            else:
                b = "not in a channel"
                c = ""
        else:
            a = "not connected"
            b = ""
            c = ""
        s  = "%s %s %s %s" % (nick, a, b, c)
        self.statustxt.set(s)

    def update_status(self):
        nick, server, channel, topic = self.ircHandle.get_status()
        if (server != ""):
            a = "connected to %s," % server
            if (channel != ""):
                b = "in channel %s" % channel
                if (topic != ""):
                    c = ", topic: %s" % topic
                else:
                    c = ""
            else:
                b = "not in a channel"
                c = ""
        else:
            a = "not connected"
            b = ""
            c = ""
        s  = "%s %s %s %s" % (nick, a, b, c)
        self.statustxt.set(s)

    def add_message(self, s, color, hilite):
        self.chat.configure(state = "normal")
        self.chat.insert('end', "\n")
        if (hilite):
            self.chat.tag_configure("h", background = self.hilite_bg,
                                    foreground = self.hilite_fg)
            self.chat.insert('end', s, "h")
        else:
            self.chat.insert('end', s, color)
        self.chat.configure(state = "disabled")
        self.chat.see('end')

    def add_debug_message(self, s):
        self.server.configure(state = "normal")
        self.server.insert('end', "\n" + s, "server")
        self.server.configure(state = "disabled")
        self.server.see('end')

    def set_nicklist(self, a):
        # Populate the nick-list with an alphabetically sorted array of nicks.
        self.nicktxt.set(tuple(a))


    def handle_input(self, event):
        s = self.cmdtxt.get()
        if (s != ""):
            self.kbHandle.parse_input(s)
            self.cmdtxt.set("")

    def toggle_debug(self):
        self.notebook.select(self.p2)
        self.chat.configure(font=self.bigFixFnt)
        self.cmd.configure(font=self.bigFixFnt)
        self.nicks.configure(font=self.bigFixFnt)
        self.status.configure(font=self.bigVarFnt)
        # TODO: what does 'toggle' mean for tabs?

    def polling_task(self):
        self.ircHandle.poll()
        root.after(4, self.polling_task)

    def run(self):
        root.after(4, self.polling_task)
        root.mainloop()

    def shutdown(self):
        root.destroy()
