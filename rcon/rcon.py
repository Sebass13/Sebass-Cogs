import discord
from discord.ext import commands
from .utils import checks
from .utils.chat_formatting import pagify, box
from cogs.utils.dataIO import dataIO
import os
import logging
import contextlib
from __main__ import send_cmd_help
import traceback
import asyncio
import aiorcon
from collections import namedtuple
import ast
from aiorcon.exceptions import *
import importlib
try:
    from pip import main as pipmain
except ImportError:
    from pip._internal import main as pipmain

file_path = "data/rcon/settings.json"
log = logging.getLogger('red.rcon')
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%d-%m-%Y:%H:%M:%S',
                    level=logging.DEBUG)


required_aiorcon_version = '0.6.4'


class Address(commands.Converter):
    def convert(self):
        ip, port = self.argument.split(':')
        return ip, int(port)


class Setting(commands.Converter):
    valid_keys = {"IP", "port", "PW", "MULTI", "TIMEOUT", "SCC", "RCC", "NR"}

    def convert(self):
        key, value = self.argument.split("=")
        assert key in self.valid_keys
        return key, value


CommandTuple = namedtuple('Commands', ['send', 'recv', 'nores'])


class RCON:
    """Connect to Servers via RCON"""

    def __unload(self):
        for rcon in self.active_rcon.values():
            rcon.close()
        if self.task:
            self.task.cancel()

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.json = dataIO.load_json(file_path)
        self.active_rcon = {}
        self.active_chat = {}
        self.task = self.bot.loop.create_task(self.intervalled())

    async def say(self, ctx, *args, **kwargs):
        """A stronger version of self.bot.say that is used because of magic breaking :("""
        return await self.bot.send_message(ctx.message.channel, *args, **kwargs)

    async def on_message(self, message: discord.Message):
        prefixes = await self.bot._get_prefix(message)
        if any(message.content.startswith(prefix) for prefix in prefixes):
            return
        if message.author == self.bot.user:
            return
        if message.channel in self.active_chat:
            try:
                await self.bot.delete_message(message)
            except discord.Forbidden:
                pass
            rcon = self.active_rcon[message.channel]
            sendchatcommand = self.active_chat[message.channel].send
            content = message.content.encode('ascii', 'ignore').rstrip().decode()
            command = "{} {}: {}".format(sendchatcommand, message.author.name, content)
            try:
                await rcon(command)
            except Exception as e:
                #  TODO: This should be removed eventually
                await self.bot.send_message(message.channel, traceback.format_exc())
            await self.chat_update()

    async def chat_update(self):
        for channel, commands_ in self.active_chat.items():
            rcon = self.active_rcon[channel]
            receivechatcommand = commands_.recv
            try:
                res = await rcon(receivechatcommand)
            except Exception as e:
                #  TODO: Remove usages of traceback
                await self.bot.send_message(channel, traceback.format_exc())
                del self.active_rcon[channel]
                del self.active_chat[channel]
                return
            res = res.strip()
            if not res or (res == commands_.nores):
                return
            result = list(pagify(res))
            for page in result:
                await self.bot.send_message(channel, page)

    async def intervalled(self):
        with contextlib.suppress(asyncio.CancelledError):
            while self == self.bot.get_cog("RCON"):
                try:
                    await self.chat_update()
                    await asyncio.sleep(1)
                except:
                    log.exception('An error has occured in intervalled: ')

    @commands.group(pass_context=True)
    async def server(self, ctx):
        """Manage and connect to RCON servers."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @server.command(pass_context=True)
    @checks.admin()
    async def add(self, ctx, address: Address, password: str, name: str, multiple_packet: bool = True,
                  timeout: int = None):
        """Adds and names a server's RCON.

        Use this command in a direct message to keep your password secret.
        Disable multiple packet responses only if you know what you're doing."""
        if name in self.json:
            await self.say(ctx,
                           "A server with the name {} already exists, please choose a different name.".format(name))
            return
        self.json[name] = {"IP": address[0], "port": address[1], "PW": password,
                           "MULTI": multiple_packet, "TIMEOUT": timeout}
        dataIO.save_json(file_path, self.json)
        await self.say(ctx, "Server added.")

    @server.command(pass_context=True, hidden=True)
    @checks.admin()
    async def edit(self, ctx, name: str, *settings: Setting):
        """Edit parts of the saved settings for a server.

        Example: [p]server edit SERVER PW="test" MULTI=False
        Only use this if you know what you're doing."""

        if name not in self.json:
            await self.say(ctx, "There are no servers named {}, check "
                                "`{}server list` for all servers.".format(name, ctx.prefix))
            return

        if not settings:
            await send_cmd_help(ctx)
            return

        try:
            args = {key: ast.literal_eval(value) for key, value in settings}
        except ValueError:
            await self.say(ctx, "The value must be a valid object in Python.")
            return
        self.json[name].update(args)
        await self.say(ctx, "Updated.")
        dataIO.save_json(file_path, self.json)

    @server.command(pass_context=True)
    @checks.admin()
    async def list(self, ctx, passwords_visible: bool = False):
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
    @checks.admin()
    async def remove(self, ctx, name: str):
        """Removes a server by name."""
        if name not in self.json:
            await self.say(ctx, "There are no servers named {}, check "
                                "`{}server list` for all servers.".format(name, ctx.prefix))
            return
        del self.json[name]
        dataIO.save_json(file_path, self.json)
        await self.say(ctx, "Server removed.")

    async def _connect(self, ctx, name, autoreconnect):
        if name not in self.json:
            await self.say(ctx, "There are no servers named {}, check "
                                "`{}server list` for all servers.".format(name, ctx.prefix))
            return
        if ctx.message.channel in self.active_rcon:
            await self.say(ctx, "There is already an active RCON in this channel.")
            return
        server = self.json[name]
        multipacket = server.get("MULTI", True)
        timeout = server.get("TIMEOUT", None)
        try:
            rcon = await aiorcon.RCON.create(server["IP"], server["port"], server["PW"], loop=self.bot.loop,
                                             auto_reconnect_attempts=-autoreconnect,
                                             multiple_packet=multipacket, timeout=timeout)
        except OSError:
            await self.say(ctx, "Connection failed, ensure the IP/port is correct and that the server is running.")
            return
        except RCONAuthenticationError as e:
            await self.say(ctx, e)
            return
        except Exception as e:
            await self.say(ctx, traceback.format_exc())
            return

        assert rcon.authenticated
        await self.say(ctx, "The server is now active in this channel. "
                            "Use `{}rcon` in this channel to execute commands".format(ctx.prefix))
        self.active_rcon[ctx.message.channel] = rcon
        return True

    @server.command(name="connect", pass_context=True, no_pm=True)
    @checks.admin()
    async def server_connect(self, ctx, name: str, autoreconnect: bool = True):
        """Sets the active RCON in this channel."""
        return await self._connect(ctx, name, autoreconnect)

    @server.command(name="disconnect", pass_context=True, no_pm=True)
    @checks.admin()
    async def server_disconnect(self, ctx):
        """Closes the RCON connection in the channel."""
        channel = ctx.message.channel
        if channel not in self.active_rcon:
            await self.say(ctx, "No RCON is active in the channel; use `{}server connect`.".format(ctx.prefix))
            return
        rcon = self.active_rcon[channel]
        rcon.close()
        del self.active_rcon[channel]
        if channel in self.active_chat:
            del self.active_chat[channel]
        await self.say(ctx, "The RCON connection has been closed.")

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin()
    async def chat(self, ctx):
        """Manage and connect live chat for a server."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @chat.command(name="commands", pass_context=True, no_pm=True)
    @checks.admin()
    async def chat_commands(self, ctx, name: str, receivechatcommand: str, sendchatcommand: str, noresponse: str = ""):
        """Set the commands with which the server will receive and send chat commands.

        Optional noresponse to set the message that the server returns when there is no response."""
        if name not in self.json:
            await self.say(ctx, "There are no servers named {}, check "
                                "`{}server list` for all servers.".format(name, ctx.prefix))
            return
        self.json[name].update({"RCC": receivechatcommand, "SCC": sendchatcommand, "NR": noresponse})
        dataIO.save_json(file_path, self.json)
        await self.say(ctx, "Commands set.")

    @chat.command(name="connect", pass_context=True, no_pm=True)
    @checks.admin()
    async def chat_connect(self, ctx, name, autoreconnect: bool = True):
        """Sets the active chat session in the channel.

        This also connects RCON in the channel if this hasn't already been done, and  the autoreconnect setting
        will only apply under this circumstance."""
        if "SCC" not in self.json[name]:
            await self.say(ctx, "You first must set up the commands for this server with `{}chat commands`."
                           .format(ctx.prefix))
            return

        channel = ctx.message.channel
        if channel not in self.active_rcon:
            if not (await self._connect(ctx, name, autoreconnect)):
                return

        if channel in self.active_chat:
            await self.say(ctx, "There is already an active chat in this channel.")
            return
        self.active_chat[channel] = CommandTuple(send=self.json[name]["SCC"],
                                                 recv=self.json[name]["RCC"],
                                                 nores=self.json[name]["NR"])
        await self.say(ctx, "Live chat is now enabled.")

    @chat.command(name="disconnect", pass_context=True, no_pm=True)
    async def chat_disconnect(self, ctx):
        """Disables live chat in this channel.

        This does not close the RCON connection."""
        channel = ctx.message.channel
        if channel not in self.active_chat:
            await self.say(ctx, "No chat is active in this channel; use `{}server chat connect`.".format(ctx.prefix))
            return
        del self.active_chat[channel]
        await self.say(ctx, "Live chat is now disabled.")

    @commands.command(pass_context=True)
    @checks.mod()
    async def rcon(self, ctx, *, command: str):
        """Executes a command in the active RCON on the channel."""
        channel = ctx.message.channel
        if channel not in self.active_rcon:
            await self.say(ctx, "No RCON is active in the channel, use `{}server connect`.".format(ctx.prefix))
            return
        rcon = self.active_rcon[channel]
        try:
            res = await rcon(command)
        except Exception as e:
            #  TODO: Remove usages of traceback
            await self.say(ctx, traceback.format_exc())
            del self.active_rcon[channel]
            if channel in self.active_chat:
                del self.active_chat[channel]
            return
        res = res.rstrip()
        result = list(pagify(res, shorten_by=16))

        for i, page in enumerate(result):
            if i != 0 and i % 4 == 0:
                last = await self.say(ctx, "There are still {} messages. "
                                           "Type `more` to continue."
                                           "".format(len(result) - (i + 1)))
                msg = await self.bot.wait_for_message(author=ctx.message.author,
                                                      channel=channel,
                                                      check=lambda m: m.content.strip().lower() == "more",
                                                      timeout=25)
                if msg is None:
                    try:
                        await self.bot.delete_message(last)
                    except discord.HTTPException:
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


def maybe_update(module_, required_version):
    def outdated(expected, actual):
        for num1, num2 in zip(*map(lambda v: v.split('.'), (expected, actual))):
            if int(num1) > int(num2):
                return True
        else:
            return False

    if outdated(required_version, module_.__version__):
        pipmain(['install', module_.__name__])
        importlib.reload(module_)


def setup(bot):
    check_folder()
    check_file()
    maybe_update(aiorcon, required_aiorcon_version)
    bot.add_cog(RCON(bot))
