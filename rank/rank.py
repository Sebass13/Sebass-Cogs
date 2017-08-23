import discord
from discord.ext import commands
from .utils import checks
from cogs.utils.dataIO import dataIO
import os
import logging
#will be installed due to info.json
import requests
from steam import steamid
#Debugging
from time import time

log = logging.getLogger('red.rank')

def _parse_steam(input):
    if input.isdigit():
        url = "https://steamcommunity.com/profiles/" + input
    else:
        url = "https://steamcommunity.com/id/" + input.split('/id/')[-1]
    return str(steamid.steam64_from_url(url))

class Rank:
    """Check Rocket League Rank with this cog."""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/rank/settings.json"
        self.settings = dataIO.load_json(self.file_path)

    @commands.group(invoke_without_command=True, pass_context=True)
    async def rank(self, ctx, steam, *, playlist):
        """Check your rank in Rocket League"""
        author = ctx.message.author
        channel = ctx.message.channel
        if steam == "me":
            SteamID64 = self.settings['SteamID64'].get(author.id)
            if SteamID64 is None:
                await self.bot.say("No SteamID found, "
                                   "set it using {p}setsteam".format(p=ctx.prefix))
        else:
            SteamID64 = _parse_steam(steam)
        try:
            await self.bot.send_typing(channel)
            rank = await self.get_rank(SteamID64, playlist)
            await self.bot.say("Your rank is: " + rank)
        except Exception as e:
            await self.bot.say(e)


    @rank.command(hidden=True)
    @checks.is_owner()
    async def apikey(self, key: str):
        """Sets token to be used with rocketleaguestats.com

        Use this command in direct message to keep your
        token secret."""
        self.settings["key"] = key
        dataIO.save_json(self.file_path, self.settings)
        await self.bot.say("Credentials set.")

    @commands.command(pass_context = True)
    async def setsteam(self, ctx, steam):
        """Link your Steam Account to your Discord"""
        author = ctx.message.author
        SteamID64 = _parse_steam(steam)
        if SteamID64 is None:
            await self.bot.say("Invalid input, SteamID not set.")
            return
        self.settings['SteamID64'][author.id] = SteamID64
        dataIO.save_json(self.file_path, self.settings)
        await self.bot.say("SteamID set.")

    async def get_rank(self, SteamID64, playlist):
        url = 'https://api.rocketleaguestats.com/v1/'
        playlist = playlist.lower()
        playlists = {'1v1': '10',
                     'duel': '10',
                     '2v2': '11',
                     'doubles': '11',
                     'solo standard': '12',
                     '3v3': '13',
                     'standard': '13'}
        if (playlist not in playlists):
            await self.bot.say("Please enter a valid playlist!")
            return
        else:
            playlist_id = playlists.get(playlist)
        player = requests.get(url + 'player', params={'apikey' : self.settings["key"], 'platform_id' : "1", 'unique_id' : SteamID64}).json()
        seasons = player['rankedSeasons']
        current_season = seasons.get(max(seasons.keys()))
        playlist_rank = current_season.get(playlist_id)
        tier = playlist_rank['tier']
        division = playlist_rank['division']
        tiers = requests.get(url + 'data/tiers', params={'apikey' : self.settings["key"]}).json()
        if tier == 0:
            return "Unranked"
        else:
            return "{} Division {}".format(tiers[tier].get('tierName'), division+1)



def check_folder():
    if not os.path.exists('data/rank'):
        log.debug('Creating folder: data/rank')
        os.makedirs('data/rank')


def check_file():
    f = 'data/rank/settings.json'
    if dataIO.is_valid_json(f) is False:
        log.debug('Creating json: settings.json')
        dataIO.save_json(f, {'SteamID64' : {}})

def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(Rank(bot))
