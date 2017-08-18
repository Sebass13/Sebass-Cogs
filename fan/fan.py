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
        self.plug = SmartPlug("192.168.0.175")
        
    @commands.command()
    async def fan(self, *, mode: str = "toggle"):
        if mode.upper() == self.plug.state:
            await self.bot.say("The fan is already " + mode.lower() + "!")
        else:
            if self.plug.state == "OFF":
                self.plug.turn_on()
            else:
                self.plug.turn_off()
            await self.bot.say("The fan is now " + self.plug.state.lower() + "!")
            
            
def setup(bot):
    bot.add_cog(Fan(bot))