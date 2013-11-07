import curses

class UserInterfacePlugin:
    # Uses the curses terminal handling library to display a chat log,
    # a list of users in the current channel, and a command prompt for
    # entering messages and application commands.
    def __init__(self, irc, kb):
        self.ircHandle = irc
        self.kbHandle = kb
        self.buf = ""
        curses.setupterm()
        self.colors = curses.tigetnum("colors")
        self.screen = curses.initscr()
        curses.cbreak()
        curses.noecho()
        if (curses.has_colors()):
            curses.start_color()
            curses.use_default_colors() # transparent background
            self.statusPair = curses.color_pair(7)
            self.debugPair = curses.color_pair(7)
            self.borderPair = curses.color_pair(7)
            self.haveColor = True
        else:
            self.haveColor = False

        if (self.haveColor):
            # If curses says we can use color, then we need to make color pairs,
            # which are a structure used to hold color and face attributes for
            # the foreground and background colors used when drawing.
            self.init_colors()
        self.update_geometry()
        self.make_windows()
        self.update()
        self.clear_input_window() # also puts the cursor in the input window

    def run(self):
        while (True):
            self.ircHandle.poll()
            self.poll_kb()

    def poll_kb(self):
        # Detect keys pressed on the keyboard, and assemble a string, character
        # by character. The string is passed to downstream logic when the user
        # presses the enter key.
        #
        # Note: We can't use curses' simpler line-based keyboard input routine
        # getstr(), because it would block our thread until the user pressed
        # enter, and we wouldn't be able to display messages coming in from the
        # network in real time. To work around this, we use curses' cbreak()
        # function which causes its keyboard routines to return immediately.
        # A side effect of this is that we must continuously poll for characters.
        keycode = self.inputWin.getch()
        if (keycode >= 0):
            if (keycode == 10):
                # The enter key was pressed.
                if (self.buf != ""):
                    self.kbHandle.parse_input(self.buf)
                    self.buf = ""
                    self.clear_input_window()
            elif (keycode == 127):
                # The backspace key was pressed.
                # Note: curses.KEY_BACKSPACE is listed as "unreliable" in the
                # curses+python documentation. I have found this to be true when
                # switching between differing terminal types (inside and outside
                # of tmux, i.e. screen-256 and rxvt-unicode.
                if (self.buf != ""):
                    self.buf = self.buf[:-1]
                    y, x = self.inputWin.getyx()
                    self.inputWin.delch(y, x-1)
            elif ((keycode >= 32) and (keycode < 127)):
                self.buf = self.buf + chr(keycode)
                self.inputWin.addch(keycode)

    def make_windows(self):
        # Create the curses windows we'll be using to display text.
        self.inputWin = curses.newwin(self.inputWinH,
                                      self.screenW,
                                      self.nickWinH + self.borderSize,
                                      0)
        self.chatWin = curses.newwin(self.chatWinH,
                                     self.chatWinW,
                                     0,
                                     0)
        self.nickWin = curses.newwin(self.nickWinH,
                                     self.nickWinW,
                                     0,
                                     self.chatWinW + self.borderSize)
        self.dbgBorder = curses.newwin(self.dbgWinH,
                                       self.dbgWinW,
                                       self.dbgWinY,
                                       self.dbgWinX)
        self.dbgWin = curses.newwin(self.dbgWinH-2,
                                    self.dbgWinW-2,
                                    self.dbgWinY+1,
                                    self.dbgWinX+1)
        self.chatWin.move(self.chatWinH-1, 0)
        self.chatWin.scrollok(1)
        self.nickWin.scrollok(1)
        self.inputWin.scrollok(1)
        self.inputWin.nodelay(1)
        self.dbgWin.scrollok(1)
        self.debugEnabled = False

    def update_geometry(self):
        # Compute window geometry parameters used to draw our interface.
        self.chatWinSize = 85 # chat window width vs. screen width (as %).
        self.inputWinH = 1
        self.borderSize = 1
        self.screenH, self.screenW = self.screen.getmaxyx()
        self.chatWinW = int(self.screenW * self.chatWinSize / 100)
        self.chatWinH = self.screenH - self.inputWinH - self.borderSize
        self.nickWinW = self.screenW - self.chatWinW - 1
        self.nickWinH = self.screenH - self.inputWinH - self.borderSize
        self.dbgWinW = int(self.screenW - 6)
        self.dbgWinH = int(self.screenH/2)
        self.dbgWinX = 3
        self.dbgWinY = int(self.screenH/8)

    def resize_window(self):
        # Handle a change in window size by recreating the curses windows based
        # on the current window size, and then refresh the screen.
        self.update_geometry()
        self.make_windows()
        self.update()

    def update(self):
        # Redraw the contents of the screen.
        h, w = self.screen.getmaxyx()
        if ((w != self.screenW) or (h != self.screenH)):
            self.resize_window()
        self.screen.attron(self.borderPair)
        self.screen.hline(self.chatWinH, 0, curses.ACS_HLINE, self.screenW)
        self.screen.vline(0, self.chatWinW, curses.ACS_VLINE, self.chatWinH)
        self.screen.addch(self.chatWinH, self.chatWinW, curses.ACS_BTEE)
        # Curses doesn't show changes in a window until you refresh it.
        self.screen.nooutrefresh()
        self.chatWin.nooutrefresh()
        self.nickWin.nooutrefresh()
        self.inputWin.noutrefresh()
        if (self.debugEnabled):
            self.dbgBorder.attron(self.borderPair)
            self.dbgBorder.border(0)
            self.dbgBorder.nooutrefresh()
            self.dbgWin.redrawwin()
            self.dbgWin.nooutrefresh()
        curses.doupdate()

    def clear_input_window(self):
        # Clear the input window after the user presses the enter key.
        self.inputWin.move(0, 0)
        self.inputWin.deleteln()
        self.inputWin.addstr(self.ircHandle.get_nick() +
                             "@" + self.ircHandle.get_channel() + "> ")

    def add_message(self, s, color, hilite):
        # Add a message in the chat window, using the given color.
        pair = curses.color_pair(color)
        if (hilite):
            pair = pair | curses.A_REVERSE
        self.chatWin.addstr("\n" + s, pair)
        self.update()

    def add_debug_message(self, s):
        # Add a message to the debug window. The message will be added to the
        # debug window, even if the debug window itself isn't currently visible.
        if (self.haveColor):
            self.dbgWin.addstr("\n" + s, self.debugPair)
        else:
            self.dbgWin.addstr("\n" + s)
        if (self.debugEnabled):
            self.update()

    def set_nicklist(self, a):
        # Populate the nick-list with an alphabetically sorted array of nicks.
        self.nickWin.clear()
        nicks = sorted(a)[:self.nickWinH]
        for i, nick in enumerate(nicks):
            self.nickWin.move(i, 0)
            self.nickWin.addstr(self.truncate_name(nick))
        self.update()

    def init_colors(self):
        # Called once during program initialization to generate the logical
        # color pairs used by curses in order to display strings in color.
        for x in range(self.colors):
            curses.init_pair(x, x, -1)

    def shutdown(self):
        # Deinitialize curses. Called before the program exits.
        curses.nocbreak()
        curses.endwin()

    def toggle_debug(self):
        # Enable or disable the display of the debug log.
        self.debugEnabled = not self.debugEnabled
        self.chatWin.touchwin()
        self.nickWin.touchwin()
        self.dbgWin.touchwin()
        self.update()

    def truncate_name(self, s):
        # Ensure the given string is resized to fit in the nick-list window.
        if (len(s) < self.nickWinW):
            return s
        else:
            return s[:self.nickWinW-1] + "+"
