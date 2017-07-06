import discord
import re

class Neato:
    """Neato"""

    def __init__(self, bot):
        self.bot = bot

    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        if re.search(r'\bneat\b', message.content) != None:
            await self.bot.send_message(message.channel, "*neato")


def setup(bot):
    bot.add_cog(Neato(bot))
