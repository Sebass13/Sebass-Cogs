from discord.ext import commands
from .utils import checks
from .utils.chat_formatting import pagify, box
from cogs.utils.dataIO import dataIO
import os
import logging
from __main__ import send_cmd_help
#Will be installed due to info.json
import valve.rcon

file_path = "data/rcon/settings.json"
log = logging.getLogger('red.rcon')


class Address(commands.Converter):
    def convert(self):
        return valve.rcon._parse_address(self.argument)


class RCON:
    """Connect to Servers via RCON"""
    def __unload(self):
        for rcon in self.active_rcon.values():
            rcon.close()

    def __init__(self, bot):
        self.bot = bot
        self.json = dataIO.load_json(file_path)
        self.active_rcon = {}

    @commands.group(pass_context=True)
    async def server(self, ctx):
        """Add, remove, and connect to RCON servers."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @server.command(pass_context=True)
    @checks.is_owner()
    async def add(self, ctx, address: Address, password: str, name: str):
        """Adds and names a server's RCON.

        Use this command in direct message to keep your
        password secret."""
        if name in self.json:
            await self.bot.say("A server with the name {} already exists, please choose a different name.".format(name))
            return
        self.json[name] = {"IP":address[0], "port":address[1], "PW":password}
        dataIO.save_json(file_path, self.json)
        await self.bot.say("Server added.")

    @server.command(pass_context=True)
    @checks.is_owner()
    async def list(self, ctx, passwords_visible:bool=False):
        """Lists all servers.

        Will optionally show the passwords for the servers with [p]list True,
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
            await self.bot.say(box(page))

    @server.command(pass_context=True)
    @checks.is_owner()
    async def remove(self, ctx, name: str):
        """Removes a server by name."""
        if name not in self.json:
            await self.bot.say("There are no servers named {}, check "
                               "`{}server list` for all servers.".format(name, ctx.prefix))
            return
        del self.json[name]
        dataIO.save_json(file_path, self.json)
        await self.bot.say("Server removed.")

    @server.command(pass_context=True, no_pm=True)
    @checks.is_owner()
    async def connect(self, ctx, name):
        """Sets the active RCON in this channel."""
        if name not in self.json:
            await self.bot.say("There are no servers named {}, check "
                               "{}server list for all servers.".format(name, ctx.prefix))
            return
        if ctx.message.channel in self.active_rcon:
            await self.bot.say("There is already an active RCON in this channel.")
            return
        server = self.json[name]
        rcon = valve.rcon.RCON((server["IP"], server["port"]), server["PW"], timeout=20)
        try:
            await self.bot.loop.run_in_executor(None, rcon.connect)
        except (ConnectionRefusedError, TimeoutError, OSError):
            await self.bot.say("Connection failed, ensure the IP/port is correct and that the server is running.")
            return
        except Exception as e:
            await self.bot.say("An unexpected error has occured: %s" % e)
            return

        try:
            await self.bot.loop.run_in_executor(None, rcon.authenticate)
        except valve.rcon.RCONAuthenticationError as e:
            await self.bot.say("Authentication failed: %s" % e)
            return
        except Exception as e:
            await self.bot.say("An unexpected error has occured: %s" % e)
            return

        assert rcon.authenticated
        await self.bot.say("The server is now active in this channel. "
                           "Use `{}rcon` in this channel to execute commands".format(ctx.prefix))
        self.active_rcon[ctx.message.channel] = rcon

    @server.command(pass_context=True, no_pm=True)
    @checks.is_owner()
    async def disconnect(self, ctx):
        """Closes the RCON connection in the channel."""
        if ctx.message.channel not in self.active_rcon:
            await self.bot.say("No RCON is active in the channel; use `{}server connect`.".format(ctx.prefix))
            return
        rcon = self.active_rcon[ctx.message.channel]
        await self.bot.loop.run_in_executor(None, rcon.close)
        del self.active_rcon[ctx.message.channel]
        await self.bot.say("The RCON connection has been closed.")

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def rcon(self, ctx, *, command: str):
        """Executes a command in the active RCON on the channel."""
        if ctx.message.channel not in self.active_rcon:
            await self.bot.say("No RCON is active in the channel, use `{}server connect`.".format(ctx.prefix))
            return
        rcon = self.active_rcon[ctx.message.channel]
        try:
            res = await self.bot.loop.run_in_executor(None, rcon.execute, command)
        except valve.rcon.RCONTimeoutError:
            await self.bot.say("Response expected but none received.")
        except valve.rcon.RCONCommunicationError:
            await self.bot.say("Could not communicate with server, connection now closed.")
            del self.active_rcon[ctx.message.channel]
        msg = res.text
        if not msg:
            await self.bot.say("`Command received, no response`")
            return
        result = list(pagify(msg, shorten_by=16))

        for i, page in enumerate(result):
            if i != 0 and i % 4 == 0:
                last = await self.bot.say("There are still {} messages. "
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
            await self.bot.say(box(page, lang="LDIF"))


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
