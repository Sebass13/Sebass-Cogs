import discord
from discord.ext import commands
import requests

class CatFact:
    """Penis related commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def catfact(self):
        """Random Cat Facts!"""
        fact = requests.get(r'https://catfact.ninja/fact').json()['fact']
        await self.bot.say(fact)

def setup(bot):
    bot.add_cog(CatFact(bot))
