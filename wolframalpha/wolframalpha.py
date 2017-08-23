import discord
from discord.ext import commands
from .utils import checks
from cogs.utils.dataIO import dataIO
import os
import logging
#Will be installed due to info.json
import wolframalpha

log = logging.getLogger('red.wolframalpha')

class WolframAlpha:
    """Query Wolfram Alpha"""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/wolframalpha/settings.json"
        self.settings = dataIO.load_json(self.file_path)

    def build_embed(self, input_interpretation = None, result_list = [], image=None):
        wolfram_url = 'http://www.wolframalpha.com/'
        icon_url = 'https://png.icons8.com/wolfram-alpha/color/1600'
        embed=discord.Embed(title=input_interpretation, color=0xf44336)
        embed.set_author(name="Wolfram|Alpha", url=wolfram_url, icon_url=icon_url)
        for result in result_list:
            embed.add_field(name=result[0], value=result[1], inline=False)
        if image:
            embed.set_image(url=image)
        return embed

    def is_image(self, pod):
        return not any(answer.get('plaintext') for answer in pod.subpod)


    @commands.group(no_pm=True, pass_context=True, aliases=["w"], invoke_without_command=True)
    async def wolfram(self, ctx, *, query : str):
        """Searches Wolfram|Alpha for the answer to your query."""
        channel = ctx.message.channel
        if "AppID" not in self.settings:
            await self.bot.say("You must first set your AppID, do this with "
                               "[p]AppID")
            return
        try:
            client = wolframalpha.Client(self.settings["AppID"])
            await self.bot.send_typing(channel)
            res = client.query(query, reinterpret='true')
        except Exception as e:
            if "Error 1:" in str(e):
                await self.bot.say("Invalid AppID, set it with {p}AppID".format(p=ctx.prfix))
            else:
                await self.bot.say("I'm unable to contact Wolfram|Alpha at this time.")
        #RESPONSE PARSING
        ###################
        #Checks if response is valid
        if res.get('@success') == 'false':
            await self.bot.say('Wolfram|Alpha was unable to parse your input.')
            return
        #list of pods
        pod_list = list(res.pods)
        #Parses input interpretation
        if res.get('warnings'):
            if res.get('warnings').get('reinterpret'):
                input_interpretation = "Using closest Wolfram|Alpha interpretation: "
        else:
            input_interpretation = ""
        input_interpretation += pod_list[0].get('subpod')['plaintext']
        #Creates tuples out of results
        result_list = []
        for result in res.results:
            for answer in result.subpod:
                if answer.get('@title'):
                    title = answer.get('@title')
                else:
                    title = result.get('@title')
                result_list.append((title, answer.get('plaintext')))
        #Adds in image if applicable (only takes the image if it's one of
        #the first three pods, images past that point are usually irrelevant)
        image = next((next(pod.subpod)['img']['@src'] for pod in pod_list[:3] if self.is_image(pod)), None)
        embed = self.build_embed(input_interpretation, result_list, image)
        await self.bot.say(embed=embed)

    @wolfram.command(hidden=True)
    @checks.is_owner()
    async def AppID(self, AppID: str):
        """Sets token to be used with products.wolframalpha.com/api

        Use this command in direct message to keep your
        token secret."""
        self.settings["AppID"] = AppID
        dataIO.save_json(self.file_path, self.settings)
        await self.bot.say("Credentials set.")

def check_folder():
    if not os.path.exists('data/wolframalpha'):
        log.debug('Creating folder: data/wolframalpha')
        os.makedirs('data/wolframalpha')


def check_file():
    f = 'data/wolframalpha/settings.json'
    if dataIO.is_valid_json(f) is False:
        log.debug('Creating json: settings.json')
        dataIO.save_json(f, {})

def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(WolframAlpha(bot))
