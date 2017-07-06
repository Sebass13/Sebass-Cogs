import discord
import re

class Neato:
    """Neato"""

    def __init__(self, bot):
        self.bot = bot

    async def on_message(self, message):
        await self.bot.send_message(message.channel, "That's a neat message, man")

def setup(bot):
    bot.add_cog(Neato(bot))
