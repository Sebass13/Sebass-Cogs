import discord
import random
from discord.ext import commands

class Penis:
    """Penis related commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def penis(self, *, user : discord.Member):
        """Detects user's penis length

        This is 100% accurate."""
        state = random.getstate()
        random.seed(user.id)
        dong = "8{}D".format("=" * random.randint(0, 30))
        random.setstate(state)
        if user.id == "199974404560519178":
            await self.bot.say("Size: 8=========================================D")
        elif user.id in ["313519333265506307", "323247765431779338"]:
            await self.bot.say("`Error: Penis not found for ID#" + user.id + "`")
        else:
            await self.bot.say("Size: " + dong)


def setup(bot):
    bot.add_cog(Penis(bot))