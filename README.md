Pynapple: A Simple IRC Client
=============================

More or less a toy IRC client, written as a class project. Select either the curses-based console user interface (unavailable on Windows), or the TK user interface, by changing the line near the top of pynapple.py.

Command Reference
-----------------

All commands are prefixed by a forward slash character (“/”). A list of available commands can be displayed in Pynapple
by issuing the help command. Command arguments shown here in angle brackets (“< >”) are mandatory, whereas
arguments in square brackets (“[ ]”) are optional. Leaving out an optional argument directs Pynapple to assume default
behavior. The previously entered command (or chat message) may be repeated by entering only a single forward slash.

**connect <server:port>**

Connect to an IRC server using the given host name and port. The host name can instead be a numeric IPv4 address
of the form n.n.n.n. The port number can be any integer value from 1-65535, although IRC servers typically use port
6667 to service incoming connections.

**debug**

Toggle the visibility of a debugging window that displays the raw data being sent to and received from a connected IRC
server. Lines of data displayed in this window are prefixed by either “->” or “<-” to denote whether the data is being
sent or received.

**disconnect**

Disconnect from a connected IRC server.

**help**

Display a list of available commands.

**join <channel name>**

Join the given channel. IRC channel names generally begin with a hash character (“#”) which must be included in the
channel name passed to the join command. If attempt is made to join a channel that does not already exist, most IRC
servers will respond by creating the channel, resulting in the user joining a channel as the only user.

**msg <nick> <message>**

Send a private message to a user. If the nickname given does not match any online user’s nickname, then the command
will not issue an error (though the debug window will indicate the absence of the message recipient).

**nick <new nick>**

Change the currently used nickname to the name given. Nicknames on a single IRC network must be unique, and if the
nickname given is already in use, then the command will have no effect as the IRC server will not generate the response
required to trigger a nickname change locally.

**part**

Part from the currently joined channel.

**quit**

End the program. If Pynapple is connected to a server when this command is issued, the connection will first be closed.
