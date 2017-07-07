from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
import os

class ShutUp:
    

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/shutup/settings.json"
        self.shutup = dataIO.load_json(self.file_path)
        
    @commands.group(pass_context=True, no_pm=True)
    async def tts(self, ctx)
        """Enable/Disable TTS with a curt message."""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
            
    @customcom.command(name="enable", pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def tts_enable(self, ctx):
        server = ctx.message.server
        if server.id not in self.shutup:
            self.shutup[server.id] = {}
        serversettings = self.shutup[server.id]
        if serversettings["tts"] == False:
		    await self.bot.say("TTS already enabled.")
		else:
            serversettings["tts"] == False		
        dataIO.save_json(self.file_path, self.shutup)
		
	@customcom.command(name="enable", pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def tts_enable(self, ctx):
        server = ctx.message.server
        if server.id not in self.shutup:
            self.shutup[server.id] = {}
        serversettings = self.shutup[server.id]
        if serversettings["tts"] == True:
		    await self.bot.say("TTS already enabled.")
		else:
            serversettings["tts"] == True		
        dataIO.save_json(self.file_path, self.shutup)	
        
        
    async def on_message(self, message):
        if message.server is None:
            return
        if message.author == self.bot.user:
            return
        if not self.bot.user_allowed(message):
            return
        if self.is_command(message):
            return
          
        if self.message.tts && self.shutup[server.id]["tts"]:
	        await self.bot.send_message(message.channel, "Don't use TTS " + author.mention ", you fucking weaboo faggot", tts=True) 

def check_folder():
    if not os.path.exists("data/shutup"):
        print("Creating data/alias folder...")
        os.makedirs("data/shutup")


def check_file():
    f = "data/shutup/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating default alias's aliases.json...")
        dataIO.save_json(f, {})

def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(ShutUp(bot))
