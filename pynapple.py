#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Pynapple IRC Client. Copyright 2013 Windsor Schmidt <windsor.schmidt@gmail.com>
#
# Notes/caveats:
#
# > doesn't handle large nick-lists (i.e. lists spanning multiple 353 messages)
#
# By the way, this line is 80 characters long....................................

import queue
from datetime import datetime
import hashlib
import socket
import string
import threading
import time

from pynapple_tkui import *
#from pynapple_ncui import *

class IRC:
    # Encapsulates a connection to an IRC server. Handles sending / receiving of
    # messages, message parsing, connection and disconnection, etc.
    nick = "pynapple"
    host = "localhost"
    server = ""
    topic = ""
    user = "pynapple"
    name = "Pynapple"
    partMessage = "Parting!"
    quitMessage = "Quitting!"
    logfile = "log.txt"
    version = "0.0000001"
    channel = ""
    nicklist = []
    connected = False
    joined = False
    logEnabled = False
    stopThreadRequest = threading.Event()
    rxQueue = queue.Queue()

    def start_thread(self):
        # Spawn a new thread to handle incoming data. This function expects that
        # the class variable named socket is a handle to a currently open socket.
        self.socketThread = SocketThread(self.stopThreadRequest,
                                         self.rxQueue,
                                         self.server,
                                         self.port,
                                         self.sock)
        self.stopThreadRequest.clear()
        self.socketThread.start()

    def stop_thread(self):
        # Signal the socket thread to terminate by setting a shared event flag.
        self.stopThreadRequest.set()

    def connect(self, server, port):
        # Connect to an IRC server using a given host name and port. Creates a
        # network socket that is used by a separate thread when receiving data.
        if (not self.connected):
            self.server = server
            self.port = port
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((server, port))
            self.start_thread()
            ui.add_status_message("connecting to %s:%s" % (server, str(port)))
            self.connected = True
            self.login(self.nick, self.user, self.name, self.host, server)
        else:
            ui.add_status_message("already connected")

    def send(self, command):
        # Send data to a connected IRC server.
        if (self.connected):
            self.sock.send(bytes(command + '\n', 'UTF-8'))
            ui.add_debug_message("-> " + command)

    def send_message(self, s):
        # Send a message to the currently joined channel.
        if (self.joined):
            ui.add_nick_message(irc.get_nick(), s)
            self.send("PRIVMSG %s :%s" % (self.channel, s))
        else:
            ui.add_status_message("not in a channel")

    def send_private_message(self, nick, s):
        # Send a private message to the given nickname.
        if (self.connected):
            self.send("PRIVMSG %s :%s" % (nick, s))
            ui.add_nick_message(irc.get_nick(), "[%s] %s" % (nick, s))
        else:
            ui.add_status_message("not connected")

    def get_status(self):
        return (self.nick, self.server, self.channel, self.topic)

    def disconnect(self):
        # Disconnect from the currently connected IRC server.
        if (self.connected):
            self.send("QUIT :%s" % self.quitMessage)
            self.stop_thread()
            self.connected = False
            self.server = ""
            ui.add_status_message("disconnected")
            ui.update_status()
        else:
            ui.add_status_message("not connected")

    def login(self, nick, user, name, host, server):
        # Send a log-in stanza to the currently connected server.
        self.send("USER %s %s %s %s" % (user, host, server, name))
        self.send("NICK %s" % nick)
        ui.add_status_message("using nickname %s" % nick)

    def join(self, channel):
        # Join the given channel.
        if (self.connected):
            if (not self.joined):
                self.send("JOIN %s" % channel)
            else:
                ui.add_status_message("already in a channel")
        else:
            ui.add_status_message("not connected")

    def part(self):
        # Leave the current channel.
        if (self.joined):
            self.send("PART %s" % self.channel)
            self.set_nicklist([])
            ui.add_status_message("left channel %s " % self.channel)
            self.joined = False
            self.channel = ""
            ui.update_status()
        else:
            ui.add_status_message("not in a channel")

    def add_nick(self, s):
        # Add a nickname to the list of nicknames we think are in the channel.
        # Called when a user joins the current channel, in response to a join.
        self.nicklist.append(s)
        self.nicklist.sort()
        ui.set_nicklist(self.nicklist)

    def del_nick(self, s):
        # Remove a nickname the list of nicknames we think are in the channel.
        if s in self.nicklist:
            self.nicklist.remove(s)
            ui.set_nicklist(self.nicklist)

    def replace_nick(self, old, new):
        self.del_nick(old)
        self.add_nick(new)
        ui.set_nicklist(self.nicklist)
        ui.add_status_message("%s is now known as %s" % (old, new))

    def request_nicklist(self):
        # Send a request to the IRC server to give us a list of nicknames
        # visible in the current channel.
        if (self.joined):
            self.send("NAMES %s" % self.channel)

    def set_nicklist(self, a):
        # Replace the list of nicknames with the list given.
        self.nicklist = a
        ui.set_nicklist(self.nicklist)

    def set_nick(self, s):
        # Change our own nickname.
        if (self.connected):
            self.send(":%s!%s@%s NICK %s" % (self.nick, self.user, self.host, s))

    def get_nick(self):
        # Return our own nickname.
        return self.nick

    def get_channel(self):
        # Return the name of the currently joined channel.
        if (self.joined):
            return self.channel
        else:
            return "~"

    def is_connected(self):
        # Return our IRC server connection state.
        return self.connected

    def handle_ctcp(self, cmd, msg):
        ui.add_status_message("got CTCP message: " + cmd)
        if (cmd == "VERSION"):
            self.send("VERSION pynapple-irc %s" % self.version)
        if (cmd == "ACTION"):
            ui.add_emote_message(self.nick, msg)

    def get_version(self):
        return self.version

    def logToFile(self, s):
        # Write the given string to a log file on disk, appending a newline.
        # The logfile is opened for writing if not already open.
        if (not self.logEnabled):
            self.logEnabled = True
            self.file = open(self.logfile, 'w')
        self.file.write(s + "\n")
        self.file.flush()

    def poll(self):
        # Check for incoming messages from the IRC server by polling a shared
        # message-queue populated by the socket handling thread. Strings read
        # from the queue have been buffered from the receiving socket and each
        # string represents a logical message sent by the server.
        rx = ""
        try:
            rx = self.rxQueue.get(True, 0.01)
        except:
            pass
        if (rx != ""):
            ui.add_debug_message("<- " + rx)
            self.logToFile(rx)
            self.handle_message(self.parse_message(rx))

    def parse_message(self, s):
        # Transform incoming message strings received by the IRC server in to
        # component parts common to all messages.
        prefix = ''
        trailing = []
        if (s[0] == ':'):
            prefix, s = s[1:].split(' ', 1)
        if (s.find(' :')) != -1:
            s, trailing = s.split(' :', 1)
            args = s.split()
            args.append(trailing)
        else:
            args = s.split()
        command = args.pop(0)
        return prefix, command, args

    def handle_message(self, msg):
        # Respond to incoming IRC messages by handling them here or passing
        # control to other class methods for further processing.
        prefix, cmd, args = msg
        if (cmd == "PING"):
            # Reply to PING, per RFC 1459 otherwise we'll get disconnected.
            irc.send("PONG %s" % args[0])
        if (cmd == "PRIVMSG"):
            # Either a channel message or a private message; check and display.
            message = ' '.join(args[1:])
            nick = prefix[:prefix.find('!')]
            if (args[1].startswith(chr(1))):
                ctcp = message.translate(None, chr(1)).split()
                ctcp_cmd = ctcp[0]
                ctcp_msg = ' '.join(ctcp[1:])
                self.handle_ctcp(ctcp_cmd, ctcp_msg)
            elif (args[0] == irc.channel):
                ui.add_nick_message(nick, message)
            else:
                ui.add_private_message(nick, message)
        if (cmd == "JOIN"):
            nick = prefix[:prefix.find('!')]
            if (not self.joined):
                # We weren't joined, so join message must be us joining.
                self.joined = True
                self.channel = args[0]
                ui.update_status()
                ui.add_status_message("joined channel %s " % self.channel)
            elif (nick != self.nick):
                # A user has joined the channel. Update nick list.
                irc.add_nick(prefix[:prefix.find('!')])
                ui.add_status_message("%s joined the channel" % nick)
        if (cmd == "PART" and args[0] == irc.channel):
            # A user has left the channel. Update nick list.
            nick = prefix[:prefix.find('!')]
            irc.del_nick(nick)
            ui.add_status_message("%s left the channel" % nick)
        if (cmd == "353"):
            # Receiving a list of users in the channel (aka RPL_NAMEREPLY).
            # Note that the user list may span multiple 353 messages.
            nicklist = ' '.join(args[3:]).split()
            irc.set_nicklist(nicklist)
        if (cmd == "376"):
            # Finished receiving the message of the day (MOTD).
            ui.add_status_message("MOTD received, ready for action")
            ui.update_status()
        if (cmd == "NICK"):
            old = prefix[:prefix.find('!')]
            new = args[0]
            if (old == self.nick):
                # server acknowledges we changed our own nick
                self.nick = new
            self.replace_nick(old, new)
            ui.update_status()

class SocketThread(threading.Thread):
    # A worker thread used to receive data from the connected IRC server. Once
    # started, sits in a loop reading data and assembling line-based messages
    # from the server. This thread terminates after a shared status flag is set
    # by the main thread in response to a disconnect command.
    running = True
    def __init__(self, event, rxQueue, server, port, sock):
        super(SocketThread, self).__init__()
        self.stopThreadRequest = event
        self.rxQueue = rxQueue
        self.server = server
        self.port = port
        self.sock = sock

    def run(self):
        # Continuously read from our (blocking) socket. We want to add complete
        # messages from the IRC server to our queue to be handled downstream, but
        # since the network buffer may contain only part of a message, we'll use
        # a local buffer to store incomplete messages.
        rx = ""
        while(not self.stopThreadRequest.isSet()):
            rx = rx + self.sock.recv(1024).decode("utf-8")
            if (rx != ""):
                temp = rx.split("\n")
                rx = temp.pop( ) # put left-over data back in our local buffer
                for line in temp:
                    line = line.rstrip()
                    self.rxQueue.put(line)
            else:
                # remote end disconnected, so commit thread suicide!
                self.stopThreadRequest.set()
        return

class UserInterface:
    # Uses the curses terminal handling library to display a chat log,
    # a list of users in the current channel, and a command prompt for
    # entering messages and application commands.
    badwords = []
    hilites = []
    def __init__(self):
        self.badwords = self.load_list("badwords.txt")
        self.hilites = self.load_list("hilites.txt")
        self.uiPlugin = UserInterfacePlugin(irc, kb)
        self.colors = self.uiPlugin.get_max_colors()
        self.draw_pineapple()
        self.add_status_message("welcome to pynapple-irc v" + irc.get_version())
        self.add_status_message("type /help for a list of commands")

    def run(self):
        self.uiPlugin.run()

    def add_message(self, s, color, hilite):
        msgtxt = self.censor(s)
        msg = self.time_stamp() + " " + msgtxt
        self.uiPlugin.add_message(msg, color, hilite)

    def add_nick_message(self, nick, s):
        # Add another user's message in the chat window.
        color = self.get_nick_color(nick)
        hilite = False
        if (nick != irc.get_nick()):
            hilite = self.hilite(s)
        self.add_message("<" + nick + "> " + s, color, hilite)

    def add_emote_message(self, nick, s):
        # Add another user's "emoted" message in the chat window.
        color = self.get_nick_color(nick)
        if (nick != irc.get_nick()):
            hilite = self.hilite(s)
        self.add_message("* " + nick + " " + s, color, hilite)

    def add_private_message(self, nick, s):
        # Add another user's private message in the chat window.
        self.add_nick_message(nick, "[private] " + s)

    def add_status_message(self, s):
        # Add a status message in the chat window.
        self.add_message("== " + s, 7, False)

    def add_debug_message(self, s):
        self.uiPlugin.add_debug_message(s)

    def hilite(self, s):
        # Return an true if the given word matches our highlight list.
        # The attribute is combined with any other attributes (e.g. colors)
        # when printing string. It is typical for IRC clients to highlight
        # incoming messages containing our own nick.
        if any(w in s for w in self.hilites + [irc.get_nick()]):
            return True
        else:
            return False

    def set_nicklist(self, a):
        # Populate the nick-list with an alphabetically sorted array of nicks.
        self.uiPlugin.set_nicklist(a)

    def init_colors(self):
        self.uiPlugin.init_colors()

    def get_nick_color(self, s):
        # It is often helpful to color messages based on the nick of the message
        # sender. Map an input string (the nick) to a color ID using Python's
        # hashing functions. The modulo operator here is used to map the hash
        # output value to a range within bounds of the color look up table.
        return(int(hashlib.md5(s.encode('utf-8')).hexdigest(), 16) % self.colors)

    def shutdown(self):
        self.uiPlugin.shutdown()

    def toggle_debug(self):
        self.uiPlugin.toggle_debug()

    def draw_pineapple(self):
        # Draw a sweet ASCII art rendition of a pinapple. Come to think of it,
        # it has been getting increasingly difficult to type the word pinapple
        # without replacing the "i" with a "y" instead.
        self.add_message("                \\\\//", 2, False)
        self.add_message("                \\\\//", 2, False)
        self.add_message("                \\\\//", 2, False)
        self.add_message("                /..\\", 3, False)
        self.add_message("                |..|", 3, False)
        self.add_message("                \\__/", 3, False)

    def time_stamp(self):
        # Generate a string containing the current time, used to prefix messages.
        return datetime.now().strftime("[%H:%M]")

    def load_list(self, s):
        # A utility function that loads each line from a given file in to a list.
        try:
            with open(s) as f:
                lines = f.readlines()
                f.close()
        except IOError:
            return []
        return [x.strip() for x in lines]

    def censor(self, s):
        # Replace bad words with an equal length string of asterisks
        for tag in self.badwords:
            s = s.replace(tag, "*" * len(tag))
        return s

    def update_status(self):
        self.uiPlugin.update_status()

class KeyboardHandler:
    lastInput = ""
    def parse_input(self, s):
        # Parse local user input and handle by dispatching commands or sending
        # messages to the current IRC channel.
        if ((s == "/") and (self.lastInput != "")):
            # Protip: Re-use the last input if a single forward slash is entered.
            s = self.lastInput
        self.lastInput = s
        if (s[0] == '/'):
            if (len(s) > 1):
                # got a command; handle locally,
                self.handle_cmd(s[1:])
        else:
            # otherwise send input as a channel message
            irc.send_message(s)

    def handle_cmd(self, s):
        # Respond to a command string intended to be processed locally.
        cmd = s.split()[0]
        args = s.split()[1:]
        if (cmd == "connect"):
            # Connect to the given IRC server.
            if (len(args) == 1) and (args[0].count(":") == 1):
                server, port = args[0].split(':')
                if port.isdigit():
                    ui.add_status_message("connecting to " + server + ":" + port)
                    irc.connect(server, int(port))
                else:
                    ui.add_status_message("port must be specified as an integer")
            else:
                ui.add_status_message("usage: connect <server:port>")
        elif (cmd == "disconnect"):
            # Disconnect from the current IRC server.
            irc.part()
            irc.disconnect()
        elif (cmd == "join"):
            # Join the given channel.
            if (len(args) < 1):
                ui.add_status_message("usage: join <channel>")
            else:
                irc.join(args[0])
        elif (cmd == "part"):
            # Leave the current channel.
            irc.part()
        elif (cmd == "msg"):
            # Send a private message to the given user.
            if (len(args) < 2):
                ui.add_status_message("usage: msg <nick> <message>")
            else:
                msg = ' '.join(args[1:])
                irc.send_private_message(args[0], msg)
        elif (cmd == "nick"):
            if (len(args) < 1):
                ui.add_status_message("usage: nick <new nick>")
            else:
                irc.set_nick(args[0])
        elif (cmd == "debug"):
            # Show or hide the debug window.
            ui.toggle_debug()
        elif (cmd == "names"):
            # Ask server for a list of nicks in the channel. TODO: Remove this.
            irc.request_nicklist()
        elif (cmd == "help"):
            # Print a list of commands.
            ui.add_status_message("available commands:")
            ui.add_status_message("/connect <server:port>")
            ui.add_status_message("/disconnect")
            ui.add_status_message("/join <channel>")
            ui.add_status_message("/part")
            ui.add_status_message("/msg <nick> <message>")
            ui.add_status_message("/nick <new nick>")
            ui.add_status_message("/quit")
        elif (cmd == "quit"):
            # Quit the program.
            irc.part()
            irc.disconnect()
            ui.shutdown()
            exit()
        elif (cmd == "test"):
            irc.connect("localhost", 6667)
            irc.join("#pynapple")
        else:
            # The user entered an unknown command, punish them!
            msg = "unknown command: " + cmd
            ui.add_status_message(msg)
        self.lastCommandString = s

# I suppose the program actually starts here. Create some global objects which
# initialize themselves, and then jump in to a polling loop, checking for input
# from the keyboard and network. The program exits when the user types /quit.
irc = IRC()
kb = KeyboardHandler()
ui = UserInterface()
ui.run()
