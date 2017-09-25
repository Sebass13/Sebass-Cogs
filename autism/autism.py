import discord

class Autism:
    """Autism"""
    
    def __init__(self, bot):
        self.bot = bot
        
    async def _autism_checker(self, message):
        if message.author == self.bot.user:
            return
        content = message.clean_content
        if any(autistic_b in content for autistic_b in ['\U0001f1e7', '\U0001f171']):
            try:
                await self.bot.delete_message(message)
                new_content = content.translate({127345: 98, 127463: 98})
                new_embed = discord.Embed(title=new_content)
                new_embed.set_author(name=message.author.name, icon_url=message.author.avatar_url)
                new_embed.set_footer(text="Please try to be less autistic next time.")
                await self.bot.send_message(message.channel, embed=new_embed)
            except discord.errors.Forbidden:
                await self.bot.send_message(message.channel, "delet this ^^ becuz I can't ://///////////")
        
    async def on_message(self, message):
        await self._autism_checker(message)
                
    async def on_message_edit(self, old_message, new_message):
        await self._autism_checker(new_message)


def setup(bot):
    bot.add_cog(Autism(bot))
