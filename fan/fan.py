import discord
from discord.ext import commands
from .utils import checks

try:
    from pyHS100 import SmartPlug
except Exception as e:
    raise RuntimeError("You must run `pip3 install pyHS100`.") from e
    
class Fan:
    """Turn on my fan!"""
    
    def __init__(self, bot):
        self.bot = bot
        self.plug = SmartPlug("192.168.0.175")
        self.fan_on = True
        
    @commands.command()
    async def fan(self, ctx, *, mode: str = "toggle"):
        if not self.fan_on and not checks.is_owner_check(ctx):
            await self.bot.say("The fan's state can not currently be changed.")
            return
        
        if mode.upper() == self.plug.state:
            await self.bot.say("The fan is already " + mode.lower() + "!")
        else:
            if self.plug.state == "OFF":
                self.plug.turn_on()
            else:
                self.plug.turn_off()
            await self.bot.say("The fan is now " + self.plug.state.lower() + "!")
            
    @commands.command()
    @checks.is_owner()
    async def yesfan(self)
        self.fan_on = True
        await self.bot.say("Fan powers enabled!")
        
    @commands.command()
    @checks.is_owner()
    async def nofan(self)
        self.fan_on = False  
        await self.bot.say("Fan powers disabled!")
            
def setup(bot):
    bot.add_cog(Fan(bot))