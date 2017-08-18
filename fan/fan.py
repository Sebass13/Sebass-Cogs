import discord
from discord.ext import commands

try:
    from pyHS100 import SmartPlug
except Exception as e:
    raise RuntimeError("You must run `pip3 install pyHS100`.") from e

def _toggle_fan():
    if plug.state == "OFF":
        plug.turn_on()
    else:
        plug.turn_off()
    
class Fan:
    """Turn on my fan!"""
    
    def __init__(self, bot):
        self.bot = bot
        self.fan = SmartPlug("192.168.0.175")
        
    @commands.command()
    async def fan(self, mode: str = "toggle"):
        if mode.upper() == fan.state:
            await self.bot.say("The fan is already " + mode.lower() + "!")
        else:
            _toggle_fan()