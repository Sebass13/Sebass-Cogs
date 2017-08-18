import discord
from discord.ext import commands

try:
    from pyHS100 import SmartPlug
except Exception as e:
    raise RuntimeError("You must run `pip3 install pyHS100`.") from e
    
class Fan:
    """Turn on my fan!"""
    
    def __init__(self, bot):
        self.bot = bot
        self.fan = SmartPlug("192.168.0.175")
        
    @commands.group(pass_context=True)
    async def fan(self, *, mode: str = "toggle"):
        if mode.upper() == fan.state:
            await self.bot.say("The fan is already " + mode.lower() + "!")
        else:
            if fan.state == "OFF":
                fan.turn_on()
            else:
                fan.turn_off()
            await self.bot.say("The fan is now " + mode.lower() + "!")
            
    @commands.command(hidden=True)
    async def pang(self, *, mode : str = "haha"):
        """Pong."""
        await self.bot.say(mode)
            
def setup(bot):
    bot.add_cog(Fan(bot))