CIS61 Final Project Documentation

Pynapple: An IRC Client

Windsor Schmidt
Laney College
Spring 2013
Prof. P. McDermott

1

Introduction

1.1

Purpose

Pynapple is a simple text-based chat client used to participate in mutli-user chat sessions over IP networks (e.g. the
Internet). IRC stands for Internet relay chat.

1.2

RFC 1459

The IRC protocol is formally defined by a document known as RFC 1459 (and later revised per RFC 2812). IRC is based
on a client-server architecture, where multiple clients connect to a single IRC server in order to exchange messages.
While the official RFC was published in 1993, the first IRC server was created in 1988.1

2

Usage and Features

2.1

IRC Basics

Once connected to an IRC server, communication takes place in “channels” that users may join. Text directed to a
channel will be sent to all users joined to that channel. Direct peer-to-peer communication between users is also
possible, though technically the communication data still passes through the IRC server en-route.
Operation of an IRC client typically divides in to two categories; sending commands to the IRC client, and sending
messages to a channel or user. Generally speaking, a string of text entered in the client’s input window will be sent to
the currently joined channel, unless it is prefixed with a forward slash character (“/”), causing it to be interpreted as a
command intended to be handled locally by the client.

2.2

Usage Example

A typical session begins by starting Pynapple from a command shell (Bash in this example):
user@host:~$ ./pynapple.py
Upon starting, Pynapple’s main (and only) user interface is displayed, including a chat log, a list of users in the current channel, and a text input area. Next, a server a server connection is established using the host name and port of
the IRC server:
pynapple@~> /connect irc.rizon.net:6667
At this point, the client has sent some basic identification to the server, and now we are ready to join a channel.
Channel names begin with a hash character (“#”), and generally an attempt to join a nonexistent channel will cause a
channel with that name to be created:
pynapple@~> /join #pynapple
The server responds by sending a list of nicknames for the users currently in the channel (including our own nickname), and Pynapple immediately updates the user list window to reflect this.
Now that we have joined a channel, messages from other users in the channel will appear in Pynapple’s chat log.
Likewise, messages entered in to Pynapple’s input area will be sent to the current channel for other users to see. We
can now carry on a lively chat session, until we get bored or until another user insults us. When we decide to leave the
channel, “parting” is accomplished simply with:
pynapple@#pynapple> /part
At this point we are no longer in the channel, but still maintain a connection to the IRC server. From here we could
join another channel as before, or instead, to end our session with Pynapple we can quit the program by typing:
pynapple@~> /quit
1 http://en.wikipedia.org/wiki/Internet_Relay_Chat

2

3

Command Reference

All commands are prefixed by a forward slash character (“/”). A list of available commands can be displayed in Pynapple
by issuing the help command. Command arguments shown here in angle brackets (“< >”) are mandatory, whereas
arguments in square brackets (“[ ]”) are optional. Leaving out an optional argument directs Pynapple to assume default
behavior. The previously entered command (or chat message) may be repeated by entering only a single forward slash.

connect <server:port>
Connect to an IRC server using the given host name and port. The host name can instead be a numeric IPv4 address
of the form n.n.n.n. The port number can be any integer value from 1-65535, although IRC servers typically use port
6667 to service incoming connections.

debug
Toggle the visibility of a debugging window that displays the raw data being sent to and received from a connected IRC
server. Lines of data displayed in this window are prefixed by either “->” or “<-” to denote whether the data is being
sent or received.

disconnect
Disconnect from a connected IRC server.

help
Display a list of available commands.

join <channel name>
Join the given channel. IRC channel names generally begin with a hash character (“#”) which must be included in the
channel name passed to the join command. If attempt is made to join a channel that does not already exist, most IRC
servers will respond by creating the channel, resulting in the user joining a channel as the only user.

msg <nick> <message>
Send a private message to a user. If the nickname given does not match any online user’s nickname, then the command
will not issue an error (though the debug window will indicate the absence of the message recipient).

nick <new nick>
Change the currently used nickname to the name given. Nicknames on a single IRC network must be unique, and if the
nickname given is already in use, then the command will have no effect as the IRC server will not generate the response
required to trigger a nickname change locally.

part
Part from the currently joined channel.

quit
End the program. If Pynapple is connected to a server when this command is issued, the connection will first be closed.

3

4

Program Design

4.1

Overview

At program start, Pynapple initializes the display and then immediately enters a polling loop, checking for keyboard
and network input. Program flow stays within this loop until the user issues the quit command.

4.2

Class Layout

Internally, Pynapple is divided in to three main functional blocks, implemented as Python classes:
• The IRC class encapsulates the state associated with a connection to an IRC server, and provides methods to
handle the connection state, send and receive messages, etc.
• The UserInterface class provides an interface to easily update the chat log and user list. A windowing library
named curses is used to maintain much of the actual window state.
• The KeyboardHandler class receives individual keystrokes typed by the user, assembles them in to commands
strings, and then parses those strings as either channel messages or commands to be sent to the IRC class.

4.3

Communications Model

There are several options for handling socket communications in Python. Pynapple implements a helper class as a
subclass of python’s Thread class to handle network input concurrently from the main thread used for keyboard input.
This approach avoids the main thread from being blocked while waiting for network input. In operation, a thread-safe
queue is used to pass data from the helper thread to the main thread.

Program Entry Point
- initialize global objects
- inﬁnite loop polls for network and keyboard input

Physical Keyboard
- poll to receive characters

KeyboardHandler Class
- get keyboard input one character at a time
- assemble as commands and channel messages

IRC Class
- handle IRC communication protocol
- manage nick list

SocketThread Class
- watch socket for data from IRC server
- run concurrent to main thread, use queue

UserInterface Class
- manage display state
- draw layout, messages, nick list

Physical Display
- use either curses or tkinter

Figure 1: Pynapple’s class diagram. Polled class relationships are shown with dashed lines.

4

5
5.1

Appendix
References

Lutz, Mark. Programming Python. O’Reilly, 2010. Print.
Mutton, Paul. IRC hacks. O’Reilly, 2004. Print.
http://irchelp.org/irchelp/rfc/rfc.html
http://drunkenbotanist.com (cover image)

5.2

Program Listing: pynapple.py (Core Logic)

#!/usr/bin/env python3
# -*- coding: utf-8 -*#
# Pynapple IRC Client. Copyright 2013 Windsor Schmidt <windsor.schmidt@gmail.com>
#
# Notes/caveats:
#
# > doesn’t handle large nick-lists (i.e. lists spanning multiple 353 messages)
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

5

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
self.sock.send(bytes(command + ’\n’, ’UTF-8’))
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
6

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

7

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
self.file = open(self.logfile, ’w’)
self.file.write(s + "\n")
self.file.flush()
def poll(self):
# Check for incoming messages from the IRC server by polling a shared
# message-queue populated by the socket handling thread. Strings read
# from the queue have been buffered from the receiving socket and each
# string represents a logical message sent by the server.
rx = ""
try:
8

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
prefix = ’’
trailing = []
if (s[0] == ’:’):
prefix, s = s[1:].split(’ ’, 1)
if (s.find(’ :’)) != -1:
s, trailing = s.split(’ :’, 1)
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
# Reply to PING, per RFC 1459 otherwise we’ll get disconnected.
irc.send("PONG %s" % args[0])
if (cmd == "PRIVMSG"):
# Either a channel message or a private message; check and display.
message = ’ ’.join(args[1:])
nick = prefix[:prefix.find(’!’)]
if (args[1].startswith(chr(1))):
ctcp = message.translate(None, chr(1)).split()
ctcp_cmd = ctcp[0]
ctcp_msg = ’ ’.join(ctcp[1:])
self.handle_ctcp(ctcp_cmd, ctcp_msg)
elif (args[0] == irc.channel):
ui.add_nick_message(nick, message)
else:
ui.add_private_message(nick, message)
if (cmd == "JOIN"):
nick = prefix[:prefix.find(’!’)]
if (not self.joined):
# We weren’t joined, so join message must be us joining.
self.joined = True
self.channel = args[0]
ui.update_status()
ui.add_status_message("joined channel %s " % self.channel)
elif (nick != self.nick):
# A user has joined the channel. Update nick list.
irc.add_nick(prefix[:prefix.find(’!’)])
ui.add_status_message("%s joined the channel" % nick)
if (cmd == "PART" and args[0] == irc.channel):
9

# A user has left the channel. Update nick list.
nick = prefix[:prefix.find(’!’)]
irc.del_nick(nick)
ui.add_status_message("%s left the channel" % nick)
if (cmd == "353"):
# Receiving a list of users in the channel (aka RPL_NAMEREPLY).
# Note that the user list may span multiple 353 messages.
nicklist = ’ ’.join(args[3:]).split()
irc.set_nicklist(nicklist)
if (cmd == "376"):
# Finished receiving the message of the day (MOTD).
ui.add_status_message("MOTD received, ready for action")
ui.update_status()
if (cmd == "NICK"):
old = prefix[:prefix.find(’!’)]
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
# since the network buffer may contain only part of a message, we’ll use
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
10

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
# Add another user’s message in the chat window.
color = self.get_nick_color(nick)
hilite = False
if (nick != irc.get_nick()):
hilite = self.hilite(s)
self.add_message("<" + nick + "> " + s, color, hilite)
def add_emote_message(self, nick, s):
# Add another user’s "emoted" message in the chat window.
color = self.get_nick_color(nick)
if (nick != irc.get_nick()):
hilite = self.hilite(s)
self.add_message("* " + nick + " " + s, color, hilite)
def add_private_message(self, nick, s):
# Add another user’s private message in the chat window.
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

11

def set_nicklist(self, a):
# Populate the nick-list with an alphabetically sorted array of nicks.
self.uiPlugin.set_nicklist(a)
def init_colors(self):
self.uiPlugin.init_colors()
def get_nick_color(self, s):
# It is often helpful to color messages based on the nick of
# sender. Map an input string (the nick) to a color ID using
# hashing functions. The modulo operator here is used to map
# output value to a range within bounds of the color look up
return(int(hashlib.md5(s.encode(’utf-8’)).hexdigest(), 16) %

the message
Python’s
the hash
table.
self.colors)

def shutdown(self):
self.uiPlugin.shutdown()
def toggle_debug(self):
self.uiPlugin.toggle_debug()
def draw_pineapple(self):
# Draw a sweet ASCII art rendition of a pinapple. Come to think of it,
# it has been getting increasingly difficult to type the word pinapple
# without replacing the "i" with a "y" instead.
self.add_message("
\\\\//", 2, False)
self.add_message("
\\\\//", 2, False)
self.add_message("
\\\\//", 2, False)
self.add_message("
/..\\", 3, False)
self.add_message("
|..|", 3, False)
self.add_message("
\\__/", 3, False)
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
12

# Parse local user input and handle by dispatching commands or sending
# messages to the current IRC channel.
if ((s == "/") and (self.lastInput != "")):
# Protip: Re-use the last input if a single forward slash is entered.
s = self.lastInput
self.lastInput = s
if (s[0] == ’/’):
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
server, port = args[0].split(’:’)
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
msg = ’ ’.join(args[1:])
irc.send_private_message(args[0], msg)
elif (cmd == "nick"):
if (len(args) < 1):
ui.add_status_message("usage: nick <new nick>")
else:
irc.set_nick(args[0])
elif (cmd == "debug"):
# Show or hide the debug window.
ui.toggle_debug()
13

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

5.3

Program Listing: pynapple_tkui.py (TkInter GUI)

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

14

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
self.cmd.bind(’<Return>’, self.handle_input)
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
15

colorString = ’#%02x%02x%02x’ % (rgb[0], rgb[1], rgb[2])
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
s = "%s %s %s %s" % (nick, a, b, c)
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
s = "%s %s %s %s" % (nick, a, b, c)
self.statustxt.set(s)
def add_message(self, s, color, hilite):
self.chat.configure(state = "normal")
self.chat.insert(’end’, "\n")
if (hilite):
self.chat.tag_configure("h", background = self.hilite_bg,
foreground = self.hilite_fg)
self.chat.insert(’end’, s, "h")
else:
self.chat.insert(’end’, s, color)
self.chat.configure(state = "disabled")
self.chat.see(’end’)
def add_debug_message(self, s):
self.server.configure(state = "normal")
16

self.server.insert(’end’, "\n" + s, "server")
self.server.configure(state = "disabled")
self.server.see(’end’)
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
# TODO: what does ’toggle’ mean for tabs?
def polling_task(self):
self.ircHandle.poll()
root.after(4, self.polling_task)
def run(self):
root.after(4, self.polling_task)
root.mainloop()
def shutdown(self):
root.destroy()

5.4

Program Listing: pynapple_ncui.py (ncurses GUI)

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
17

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
# Note: We can’t use curses’ simpler line-based keyboard input routine
# getstr(), because it would block our thread until the user pressed
# enter, and we wouldn’t be able to display messages coming in from the
# network in real time. To work around this, we use curses’ cbreak()
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
# Create the curses windows we’ll be using to display text.
self.inputWin = curses.newwin(self.inputWinH,
self.screenW,
self.nickWinH + self.borderSize,
18

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
# Curses doesn’t show changes in a window until you refresh it.
19

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
# debug window, even if the debug window itself isn’t currently visible.
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

20

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

21

