import discord
from discord.ext import commands
from .utils import checks
from cogs.utils.dataIO import dataIO
import os
import logging
#will be installed due to info.json
import rocket_snake as rs
from steam import steamid
#Debugging
from time import time

log = logging.getLogger('red.ranks')

def _parse_steam(input):
    if "steamcommunity.com" in input:
        return str(steamid.steam64_from_url(input))
    elif input.isdigit():
        return input
    else:
        return None

class Rank:
    """Check Rocket League Rank with this cog."""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/rank/settings.json"
        self.settings = dataIO.load_json(self.file_path)

    @commands.group(no_pm=True, invoke_without_command=True, pass_context=True)
    async def rank(self, ctx, steam, *, playlist):
        """Check your rank in Rocket League"""
        author = ctx.message.author
        channel = ctx.message.channel
        try:
            SteamID64 = _parse_steam(steam)
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

    async def get_rank(self, SteamID64, playlist):
        client = rs.RLS_Client(self.settings["key"])
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
        start_time = time()
        me = await client.get_player(SteamID64, rs.constants.STEAM)
        await self.bot.say(time() - start_time)
        seasons = me.ranked_seasons
        current_season = seasons.get(max(seasons.keys()))
        playlist_rank = current_season.get(playlist_id)
        tier = playlist_rank.tier
        division = playlist_rank.division
        tiers = await client.get_tiers()
        if tier == 0:
            return "Unranked"
        else:
            return "{} Division {}".format(tiers[tier].name, division+1)



def check_folder():
    if not os.path.exists('data/rank'):
        log.debug('Creating folder: data/rank')
        os.makedirs('data/rank')


def check_file():
    f = 'data/rank/settings.json'
    if dataIO.is_valid_json(f) is False:
        log.debug('Creating json: settings.json')
        dataIO.save_json(f, {})

def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(Rank(bot))
