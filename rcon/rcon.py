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
import sys
import asyncio
import aiorcon


file_path = "data/rcon/settings.json"
log = logging.getLogger('red.rcon')


class Address(commands.Converter):
    def convert(self):
        IP, port = self.argument.split()
        return IP, int(port)


class RCONContainer:
    def __init__(self, rcon, chatenabled):
        self.rcon = rcon
        self.chatenabled = chatenabled


class RCON:
    """Connect to Servers via RCON"""
    def __unload(self):
        for rcon in self.active_rcon.values():
            rcon.rcon.close()
        if self.task:
            self.task.cancel()

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.json = dataIO.load_json(file_path)
        self.active_rcon = {}
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
        if message.channel in self.active_rcon and self.active_rcon[message.channel].chatenabled:
            try:
                await self.bot.delete_message(message)
            except discord.Forbidden:
                pass
            rcon = self.active_rcon[message.channel].rcon
            sendchatcommand = self.active_rcon[message.channel].chatenabled[1]
            try:
                msg = "{} {}: {}".format(sendchatcommand, message.author.name, message.content.rstrip())
                await self.bot.send_message(message.channel, msg)
                await rcon.execute(msg)
            except Exception as e:
                await self.bot.send_message(message.channel, traceback.format_exc())
                await self.bot.send_message(message.channel, sys.exc_info()[0])
            await self.chat_update()

    async def chat_update(self):
        for channel, rc in self.active_rcon.items():
            rcon = rc.rcon
            chat = rc.chatenabled
            if not chat:
                continue
            receivechatcommand = self.active_rcon[channel].chatenabled[0]
            res = await rcon(receivechatcommand)
            res = res.strip()
            if not res or (res in ["Server received, But no response!!"]):
                return
            result = list(pagify(res))
            for page in result:
                await self.bot.send_message(channel, page)

    async def intervalled(self):
        with contextlib.suppress(asyncio.CancelledError):
            try:
                while self == self.bot.get_cog("RCON"):
                    await self.chat_update()
                    await asyncio.sleep(1)
            except Exception as e:
                print(repr(e))


    @commands.group(pass_context=True)
    async def server(self, ctx):
        """Add, remove, and connect to RCON servers."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @server.command(pass_context=True)
    @checks.admin()
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
    @checks.admin()
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

    @server.command(pass_context=True, no_pm=True)
    @checks.admin()
    async def connect(self, ctx, name: str, autoreconnect: bool=False):
        """Sets the active RCON in this channel."""
        if name not in self.json:
            await self.say(ctx, "There are no servers named {}, check "
                           "`{}server list` for all servers.".format(name, ctx.prefix))
            return
        if ctx.message.channel in self.active_rcon:
            await self.say(ctx, "There is already an active RCON in this channel.")
            return
        server = self.json[name]
        try:
            rcon = await aiorcon.RCON.create(server["IP"], server["port"], server["PW"], loop=self.bot.loop, auto_reconnect_attempts=5)
        except OSError:
            await self.say(ctx, "Connection failed, ensure the IP/port is correct and that the server is running.")
            return
        except aiorcon.RCONAuthenticationError as e:
            await self.say(ctx, e)
            return
        except Exception as e:
            await self.say(ctx, "An unexpected error has occured: %s" % e)
            return

        assert rcon.authenticated
        await self.say(ctx, "The server is now active in this channel. "
                           "Use `{}rcon` in this channel to execute commands".format(ctx.prefix))
        self.active_rcon[ctx.message.channel] = RCONContainer(rcon, False)

    @server.command(pass_context=True, no_pm=True)
    @checks.admin()
    async def disconnect(self, ctx):
        """Closes the RCON connection in the channel."""
        if ctx.message.channel not in self.active_rcon:
            await self.say(ctx, "No RCON is active in the channel; use `{}server connect`.".format(ctx.prefix))
            return
        rcon = self.active_rcon[ctx.message.channel].rcon
        rcon.disconnect()
        del self.active_rcon[ctx.message.channel]
        await self.say(ctx, "The RCON connection has been closed.")

    @server.command(pass_context=True, no_pm=True)
    @checks.admin()
    async def chat(self, ctx, enabled: bool, receivechatcommand=None, sendchatcommand=None):
        """Enables/disables live chat for the RCON connection in the channel."""
        if ctx.message.channel not in self.active_rcon:
            await self.say(ctx, "No RCON is active in the channel; use `{}server connect`.".format(ctx.prefix))
            return
        self.active_rcon[ctx.message.channel].chatenabled = (receivechatcommand, sendchatcommand) if enabled else False
        await self.say(ctx, "Live chat is now {}.".format(['disabled', 'enabled'][enabled]))

    @commands.command(pass_context=True)
    @checks.mod()
    async def rcon(self, ctx, *, command: str):
        """Executes a command in the active RCON on the channel."""
        if ctx.message.channel not in self.active_rcon:
            await self.say(ctx, "No RCON is active in the channel, use `{}server connect`.".format(ctx.prefix))
            return
        rcon = self.active_rcon[ctx.message.channel].rcon
        try:
            res = await rcon(command)
        except TimeoutError:
            await self.say(ctx, "Response expected but none received.")
            return
        except Exception as e:
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
