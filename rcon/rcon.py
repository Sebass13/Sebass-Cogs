#<editor-fold desc="import SourceRcon">
import struct
import asyncio

SERVERDATA_AUTH = 3
SERVERDATA_AUTH_RESPONSE = 2

SERVERDATA_EXECCOMMAND = 2
SERVERDATA_RESPONSE_VALUE = 0

MAX_COMMAND_LENGTH = 510  # found by trial & error

MIN_MESSAGE_LENGTH = 4+4+1+1  # command (4), id (4), string1 (1), string2 (1)
MAX_MESSAGE_LENGTH = 4+4+4096+1  # command (4), id (4), string (4096), string2 (1)

# there is no indication if a packet was split, and they are split by lines
# instead of bytes, so even the size of split packets is somewhat random.
# Allowing for a line length of up to 400 characters, risk waiting for an
# extra packet that may never come if the previous packet was this large.
PROBABLY_SPLIT_IF_LARGER_THAN = MAX_MESSAGE_LENGTH - 400


class SourceRconError(Exception):
    pass

class SourceRcon(object):
    """Port of SourceRcon for async usage in Python 3

       Example usage:
       import SourceRcon, asyncio
       server = SourceRcon.SourceRcon('1.2.3.4', 27015, 'secret')
       print(asyncio.get_event_loop().run_until_complete(server.rcon('cvarlist'))
    """
    def __init__(self, host, port=27015, password='', timeout=1.0, loop=asyncio.get_event_loop()):
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self.loop = loop
        self.reader = None
        self.writer = None
        self.authenticated = False
        self.reqid = 0

    @property
    def connected(self):
        return self.writer and not self.writer._transport.is_closing()

    async def connect(self):
        """Connect to the server. Should only be used internally."""
        self.reader, self.writer = await asyncio.wait_for(asyncio.open_connection(self.host, self.port, loop=self.loop), self.timeout)

    async def authenticate(self):
        self.send(SERVERDATA_AUTH, self.password)

        auth = await self.receive()
        # the first packet may be a "you have been banned" or empty string.
        # in the latter case, fetch the second packet
        if auth == b'':
            auth = await self.receive()

        if auth is not True:
            self.disconnect()
            raise SourceRconError('RCON authentication failure: %s' % (repr(auth),))
        else:
            self.authenticated = True

    def disconnect(self):
        """Disconnect from the server."""
        if self.writer:
            self.writer.close()

    def send(self, cmd, message):
        """Send command and message to the server. Should only be used internally."""
        if len(message) > MAX_COMMAND_LENGTH:
            raise SourceRconError('RCON message too large to send')

        self.reqid += 1
        data = struct.pack('<l', self.reqid) + struct.pack('<l', cmd) + message.encode() + '\x00\x00'.encode()
        self.writer.write(struct.pack('<l', len(data)) + data)

    async def receive(self):
        """Receive a reply from the server. Should only be used internally."""
        response = False
        message = b''
        message2 = b''

        # response may be split into multiple packets, we don't know how many
        # so we loop until we decide to finish
        while 1:
            # read the size of this packet
            buf = b''

            while len(buf) < 4:
                try:
                    recv = await self.reader.read(4 - len(buf))
                    if not len(recv):
                        raise SourceRconError('RCON connection unexpectedly closed by remote host')
                    buf += recv
                except SourceRconError:
                    raise
                except Exception as e:
                    break

            if len(buf) != 4:
                # we waited for a packet but there isn't anything
                break

            packetsize = struct.unpack('<l', buf)[0]

            if packetsize < MIN_MESSAGE_LENGTH or packetsize > MAX_MESSAGE_LENGTH:
                raise SourceRconError('RCON packet claims to have illegal size: %d bytes' % (packetsize,))

            # read the whole packet
            buf = b''

            while len(buf) < packetsize:
                try:
                    recv = await self.reader.read(packetsize - len(buf))
                    if not len(recv):
                        raise SourceRconError('RCON connection unexpectedly closed by remote host')
                    buf += recv
                except SourceRconError:
                    raise
                except:
                    break

            if len(buf) != packetsize:
                raise SourceRconError('Received RCON packet with bad length (%d of %d bytes)' % (len(buf),packetsize,))

            # parse the packet
            requestid = struct.unpack('<l', buf[:4])[0]

            if requestid == -1:
                self.disconnect()
                raise SourceRconError('Bad RCON password')

            elif requestid != self.reqid:
                if b"Keep Alive" in buf:
                    return await self.receive()
                raise SourceRconError('RCON request id error: %d, expected %d\n%s' % (requestid, self.reqid,buf))

            response = struct.unpack('<l', buf[4:8])[0]

            if response == SERVERDATA_AUTH_RESPONSE:
                # This response says we're successfully authed.
                return True

            elif response != SERVERDATA_RESPONSE_VALUE:
                raise SourceRconError('Invalid RCON command response: %d' % (response,))

            # extract the two strings using index magic
            str1 = buf[8:]
            pos1 = str1.index(b'\x00')
            str2 = str1[pos1+1:]
            pos2 = str2.index(b'\x00')
            crap = str2[pos2+1:]

            if crap:
                raise SourceRconError('RCON response contains %d superfluous bytes' % (len(crap),))

            # add the strings to the full message result
            message += str1[:pos1]
            message2 += str2[:pos2]

            if not self.reader._buffer and packetsize < PROBABLY_SPLIT_IF_LARGER_THAN:
                # no packets waiting, previous packet wasn't large: let's stop here.
                break

        if response is False:
            raise SourceRconError('Timed out while waiting for reply')

        elif message2:
            raise SourceRconError('Invalid response message: %s' % (repr(message2),))

        return message

    async def execute(self, command):
        """Send RCON command to the server. Connect and auth if necessary,
           handle dropped connections, send command and return reply."""
        # special treatment for sending whole scripts
        if '\n' in command:
            commands = command.split('\n')
            def f(x): y = x.strip(); return len(y) and not y.startswith("//")
            commands = filter(f, commands)
            results = []
            for command in commands:
                result = await self.rcon(command)
                results.append(result)
            return "".join(results)

        if not self.connected:
            await self.connect()

        if not self.authenticated:
            await self.authenticate()

        self.send(SERVERDATA_EXECCOMMAND, command)
        return (await self.receive()).decode()
#</editor-fold>
from discord.ext import commands
from .utils import checks
from .utils.chat_formatting import pagify, box
from cogs.utils.dataIO import dataIO
import os
import logging
from __main__ import send_cmd_help

file_path = "data/rcon/settings.json"
log = logging.getLogger('red.rcon')

class Address(commands.Converter):
    def convert(self):
        IP, port = self.argument.split(':')
        return IP, int(port)

class RCON:
    """Connect to Servers via RCON"""
    def __unload(self):
        for rcon in self.active_rcon.values():
            rcon.disconnect()

    def __init__(self, bot):
        self.bot = bot
        self.json = dataIO.load_json(file_path)
        self.active_rcon = {}

    @commands.group(pass_context=True)
    async def server(self, ctx):
        """Add, remove, and connect to RCON servers."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    async def say(self, ctx, *args, **kwargs):
        """A stronger version of self.bot.say that is used because of the run_in_executor."""
        return await self.bot.send_message(ctx.message.channel, *args, **kwargs)

    @server.command(pass_context=True)
    @checks.is_owner()
    async def add(self, ctx, address: Address, password: str, name: str):
        """Adds and names a server's RCON.

        Use this command in direct message to keep your
        password secret."""
        if name in self.json:
            await self.say(ctx, "A server with the name {} already exists, please choose a different name.".format(name))
            return
        self.json[name] = {"IP":address[0], "port":address[1], "PW":password}
        dataIO.save_json(file_path, self.json)
        await self.say(ctx, "Server added.")

    @server.command(pass_context=True)
    @checks.is_owner()
    async def list(self, ctx, passwords_visible:bool=False):
        """Lists all servers.

        Will optionally show the passwords for the servers with `[p]list True`,
        use this command in a direct message to keep them secret."""
        servers = []
        longest = max(len(name) for name in self.json)
        for name, data in self.json.items():
            server = "{name:>{longest}s}: {IP:>15s}:{port:05d}".format(longest=longest, name=name, **data)
            if passwords_visible:
                server += ", {PW}".format(**data)
            servers.append(server)
        msg = "\n".join(servers)
        for page in pagify(msg, shorten_by=16):
            await self.say(ctx, box(page))

    @server.command(pass_context=True)
    @checks.is_owner()
    async def remove(self, ctx, name: str):
        """Removes a server by name."""
        if name not in self.json:
            await self.say(ctx, "There are no servers named {}, check "
                               "`{}server list` for all servers.".format(name, ctx.prefix))
            return
        del self.json[name]
        dataIO.save_json(file_path, self.json)
        await self.say(ctx, "Server removed.")

    @server.command(pass_context=True, no_pm=True)
    @checks.is_owner()
    async def connect(self, ctx, name):
        """Sets the active RCON in this channel."""
        if name not in self.json:
            await self.say(ctx, "There are no servers named {}, check "
                               "`{}server list` for all servers.".format(name, ctx.prefix))
            return
        if ctx.message.channel in self.active_rcon:
            await self.say(ctx, "There is already an active RCON in this channel.")
            return
        server = self.json[name]
        rcon = SourceRcon(server["IP"], server["port"], server["PW"], timeout=5.0, loop=self.bot.loop)
        try:
            await rcon.connect()
        except (ConnectionRefusedError, TimeoutError, OSError):
            await self.say(ctx, "Connection failed, ensure the IP/port is correct and that the server is running.")
            return
        except Exception as e:
            await self.say(ctx, "An unexpected error has occured: %s" % e)
            return

        try:
            await rcon.authenticate()
        except SourceRconError as e:
            await self.say(ctx, e)
            return
        except Exception as e:
            await self.say(ctx, "An unexpected error has occured: %s" % e)
            return

        assert rcon.authenticated
        await self.say(ctx, "The server is now active in this channel. "
                           "Use `{}rcon` in this channel to execute commands".format(ctx.prefix))
        self.active_rcon[ctx.message.channel] = rcon

    @server.command(pass_context=True, no_pm=True)
    @checks.is_owner()
    async def disconnect(self, ctx):
        """Closes the RCON connection in the channel."""
        if ctx.message.channel not in self.active_rcon:
            await self.say(ctx, "No RCON is active in the channel; use `{}server connect`.".format(ctx.prefix))
            return
        rcon = self.active_rcon[ctx.message.channel]
        rcon.disconnect()
        del self.active_rcon[ctx.message.channel]
        await self.say(ctx, "The RCON connection has been closed.")

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def rcon(self, ctx, *, command: str):
        """Executes a command in the active RCON on the channel."""
        if ctx.message.channel not in self.active_rcon:
            await self.say(ctx, "No RCON is active in the channel, use `{}server connect`.".format(ctx.prefix))
            return
        rcon = self.active_rcon[ctx.message.channel]
        try:
            res = await rcon.execute(command)
        except TimeoutError:
            await self.say(ctx, "Response expected but none received.")
            return
        except SourceRconError as e:
            await self.say(ctx, e)
            del self.active_rcon[ctx.message.channel]
            return
        res = res.rstrip()
        result = list(pagify(res, shorten_by=16))

        for i, page in enumerate(result):
            if i != 0 and i % 4 == 0:
                last = await self.say(ctx, "There are still {} messages. "
                                          "Type `more` to continue."
                                          "".format(len(result) - (i+1)))
                msg = await self.bot.wait_for_message(author=ctx.message.author,
                                                      channel=ctx.message.channel,
                                                      check=lambda m: m.content.strip().lower() == "more",
                                                      timeout=25)
                if msg is None:
                    try:
                        await self.bot.delete_message(last)
                    except:
                        pass
                    finally:
                        break
            await self.say(ctx, box(page, lang="LDIF"))


def check_folder():
    folder = os.path.dirname(file_path)
    if not os.path.exists(folder):
        log.debug('Creating folder: %s' % folder)
        os.makedirs(folder)


def check_file():
    if dataIO.is_valid_json(file_path) is False:
        log.debug('Creating json: %s' % os.path.basename(file_path))
        dataIO.save_json(file_path, {})


def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(RCON(bot))
