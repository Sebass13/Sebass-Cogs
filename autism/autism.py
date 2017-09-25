import discord

def makeEmbed(*, name=None, icon=None, colour=0x171848, values={}):
    '''Creates an embed messasge with specified inputs'''

    # Create an embed object with the specified colour
    embedObj = discord.Embed(colour=colour)

    # Set the author and URL
    embedObj.set_author(name=name, icon_url=icon)

    # Create all of the fields
    for i in values:
        if values[i] == '':
            values[i] = 'None'
        embedObj.add_field(name=i, value='{}'.format(values[i]))

    # Return to user
    return embedObj

class Autism:
    """Autism"""
    
    def __init__(self, bot):
        self.bot = bot
        
    def makeEmbed(*, name=None, icon=None, colour=0x171848, values={}):
        '''Creates an embed messasge with specified inputs'''

        # Create an embed object with the specified colour
        embedObj = discord.Embed(colour=colour)

        # Set the author and URL
        embedObj.set_author(name=name, icon_url=icon)

        # Create all of the fields
        for i in values:
            if values[i] == '':
                values[i] = 'None'
            embedObj.add_field(name=i, value='{}'.format(values[i]))

        # Return to user
        return embedObj

    async def on_message(self, message):
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


def setup(bot):
    bot.add_cog(Autism(bot))
