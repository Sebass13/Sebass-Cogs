import discord
from discord.ext import commands
import aiohttp

class CatFact:
    """Penis related commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def catfact(self):
        """Random Cat Facts!"""
        async with aiohttp.get(r'https://catfact.ninja/fact') as r:
            fact = await r.json()['fact']
        await self.bot.say(fact)

def setup(bot):
    bot.add_cog(CatFact(bot))
