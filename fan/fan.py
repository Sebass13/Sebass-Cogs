import discord
from discord.ext import commands
from .utils import checks
from pyHS100 import SmartPlug
    
class Fan:
    """Turn on my fan!"""
    
    def __init__(self, bot):
        self.bot = bot
        self.plug = SmartPlug("192.168.0.175") #Change to the IP of your fan's Smart Plug.
        self.fan_enabled = True

    def toggle_plug(self):
        if self.plug.is_off:
            self.plug.turn_on()
        else:
            self.plug.turn_off()
        
    @commands.group(pass_context = True)
    async def fan(self, ctx):
        """Manage your fan"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
    
    @fan.command(pass_context = True)
    async def on(self, ctx):
        """Turn it on!"""
        if not self.fan_enabled and not checks.is_owner_check(ctx):
            await self.bot.say("The fan's state currently cannot be changed.")
            return

        if self.plug.is_on:
            await self.bot.say("The fan is already on!")
        else:
            self.toggle_plug()
            await self.bot.say("The fan is now on!")

    @fan.command(pass_context = True)
    async def off(self, ctx):
        """Turn it off!"""
        if not self.fan_enabled and not checks.is_owner_check(ctx):
            await self.bot.say("The fan's state currently cannot be changed.")
            return

        if self.plug.is_off:
            await self.bot.say("The fan is already off!")
        else:
            self.toggle_plug()
            await self.bot.say("The fan is now off!")

    @fan.command(pass_context = True)
    async def toggle(self, ctx):
        """Toggle its state!"""
        if not self.fan_enabled and not checks.is_owner_check(ctx):
            await self.bot.say("The fan's state currently cannot be changed.")
            return

        self.toggle_plug()
        await self.bot.say("The fan is now {}!".format(self.plug.state.lower()))

    @fan.command()
    @checks.is_owner()
    async def enable(self):
        """Enable use of the fan by anyone."""
        self.fan_enabled = True
        await self.bot.say("Fan powers enabled!")
        
    @fan.command()
    @checks.is_owner()
    async def disable(self):
        """Disable use of the fan by anyone but yourself."""
        self.fan_enabled = False  
        await self.bot.say("Fan powers disabled!")
            
def setup(bot):
    bot.add_cog(Fan(bot))
