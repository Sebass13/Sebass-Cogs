from discord.ext import commands
from .utils import checks
from __main__ import send_cmd_help
from cogs.utils.dataIO import dataIO
from .utils.chat_formatting import box, pagify
import logging
import os
import re
from typing import Union, List

try:
    from tabulate import tabulate
except Exception as e:
    raise RuntimeError("You must run `pip3 install tabulate`.") from e

FILE_PATH = "data/factions/settings.json"
log = logging.getLogger('red.factions')
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%d-%m-%Y:%H:%M:%S')

default_language = {
    "alias_delete": "Alias deleted.",
    "alias_new": "Alias added.",
    "alias_none": "There are no aliases on this server, use <prefix>points alias new to add a new alias.",
    "alias_no_exists": "The alias <alias> doesn't exist.",
    "confirm_reset": "This will clear the <point_name> for every faction. Type \"yes\" to continue.",
    "faction_create": "Faction created.",
    "faction_delete": "Faction deleted.",
    "faction_exists": "There is already a faction named <faction_name>.",
    "faction_no_exists": "The faction <faction_name> doesn't exist.",
    "faction_none": "There are no factions on this server, use <prefix>points create to add a new faction.",
    "lang_no_line": "No line named <lang_name> in language.",
    "lang_reset": "Language reset to default.",
    "point_name": "point",
    "points_added": "Added <points> <point_name> to <faction_name>, they now have <new_points>.",
    "points_bad": "The <point_name> value must be greater than zero.",
    "points_faction": "<faction_name> has <points> <point_name>.",
    "points_removed": "Removed <points> <point_name> from <faction_name>, they now have <new_points>.",
    "points_set": "The faction <faction_name> now has <points> <point_name>.",
    "points_zero": "Can't remove any more <point_name> from <faction_name>, they are already at zero.",
    "reset_no": "Okay, <point_name> will not be reset.",
    "reset_yes": "Reset <point_name>.",
    "suffix": "s",
    #  Special cases, each are used as the headers for tabulations of their respective values.
    "AliasActual": "Alias Actual",
    "Faction": "Faction",
    "NameValue": "Name Value",
}


class Factions:
    """Factions"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.json = dataIO.load_json(FILE_PATH)

    def _load_server(self, server, key: Union[str, List[str]]="factions") -> Union[dict, List[dict]]:
        if server.id not in self.json:
            self.json[server.id] = {"factions": {},
                                    "aliases": {},
                                    "language": default_language}
            dataIO.save_json(FILE_PATH, self.json)
        if isinstance(key, str):
            return self.json[server.id][key]
        elif isinstance(key, list):
            return [self.json[server.id][k] for k in key]
        elif key is None:
            return self.json[server.id]
        else:
            raise TypeError

    def _get_alias(self, server, faction_name):
        aliases = self._load_server(server, key="aliases")
        return aliases.get(faction_name.lower(), faction_name)

    def _parse_line(self, server, key, plural=True, **kwargs):
        language = self._load_server(server, key="language")
        kwargs.update({k: language[k] for k in ("point_name", "suffix")})
        line = language[key]
        if plural:
            line = line.replace("<point_name>", "<point_name><suffix>")
        return re.sub(r"<(.+?)>", lambda m: str(kwargs[m.group(1)]), line)

    @commands.group(pass_context=True)
    async def points(self, ctx: commands.Context):
        """Faction and point related commands."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @points.command(pass_context=True)
    @checks.admin()
    async def create(self, ctx: commands.Context, *, faction_name: str):
        """Create a faction."""
        server = ctx.message.server
        factions, aliases = self._load_server(server, ["factions", "aliases"])
        if faction_name.lower() in aliases:
            await self.bot.say(self._parse_line(server, "faction_exists", faction_name=faction_name))
        else:
            aliases[faction_name.lower()] = faction_name
            factions[faction_name] = 0
            await self.bot.say(self._parse_line(server, "faction_create"))
            dataIO.save_json(FILE_PATH, self.json)

    @points.command(pass_context=True, name="delete")
    @checks.admin()
    async def faction_delete(self, ctx: commands.Context, *, faction_name: str):
        """Delete a faction and its associated points and aliases."""
        server = ctx.message.server
        factions = self._load_server(server)
        if faction_name not in factions:
            await self.bot.say(self._parse_line(server, "faction_no_exists", faction_name=faction_name))
        else:
            del factions[faction_name]
            await self.bot.say(self._parse_line(server, "faction_delete"))
            dataIO.save_json(FILE_PATH, self.json)

    @points.command(pass_context=True, name="set")
    @checks.admin()
    async def faction_set(self, ctx: commands.Context, faction_name: str, points: int):
        """Set the amount of points for a faction."""
        server = ctx.message.server
        faction_name = self._get_alias(server, faction_name)
        factions = self._load_server(server)
        if faction_name not in factions:
            await self.bot.say(self._parse_line(server, "faction_no_exists", faction_name=faction_name))
        else:
            factions[faction_name] = points
            await self.bot.say(self._parse_line(server, "points_set", faction_name=faction_name, points=points))
            dataIO.save_json(FILE_PATH, self.json)

    @points.command(pass_context=True, name="reset")
    @checks.admin()
    async def faction_reset(self, ctx: commands.Context):
        """Resets the points for all factions to zero."""
        server = ctx.message.server
        factions = self._load_server(server)
        await self.bot.say(self._parse_line(server, "confirm_reset"))
        answer = await self.bot.wait_for_message(timeout=30, author=ctx.message.author)
        if answer is None or "yes" not in answer.content.lower():
            await self.bot.say(self._parse_line(server, "reset_no"))
        else:
            for faction in factions:
                factions[faction] = 0
            await self.bot.say(self._parse_line(server, "reset_yes"))
            dataIO.save_json(FILE_PATH, self.json)

    @points.group(pass_context=True)
    @checks.admin()
    async def alias(self, ctx: commands.Context):
        """Manage aliases for factions."""
        if ctx.invoked_subcommand is self.alias:
            await send_cmd_help(ctx)

    @alias.command(pass_context=True, name="set")
    @checks.admin()
    async def alias_set(self, ctx: commands.Context, faction_name: str, alias: str):
        """Add alias for a given faction."""
        server = ctx.message.server
        factions, aliases = self._load_server(server, ["factions", "aliases"])
        if faction_name not in factions:
            await self.bot.say(self._parse_line(server, "faction_no_exists", faction_name=faction_name))
        else:
            aliases[alias.lower()] = faction_name
            await self.bot.say(self._parse_line(server, "alias_new"))
            dataIO.save_json(FILE_PATH, self.json)

    @alias.command(pass_context=True, name="delete")
    @checks.admin()
    async def alias_delete(self, ctx: commands.Context, *, alias: str):
        """Delete an alias."""
        server = ctx.message.server
        aliases = self._load_server(server, "aliases")
        if alias.lower() not in aliases:
            await self.bot.say(self._parse_line(server, "faction_no_exists", alias=alias))
        else:
            del aliases[alias.lower()]
            await self.bot.say(self._parse_line(server, "alias_delete"))
            dataIO.save_json(FILE_PATH, self.json)

    @alias.command(pass_context=True, name="list")
    @checks.admin()
    async def alias_list(self, ctx: commands.Context):
        """List all aliases."""
        server = ctx.message.server
        aliases = self._load_server(server, "aliases")
        actual_aliases = [(alias, actual) for alias, actual in aliases.items() if alias != actual.lower()]
        if not actual_aliases:
            await self.bot.say(self._parse_line(server, "alias_none", prefix=ctx.prefix))
        else:       
            msg = box(tabulate(actual_aliases,
                               self._parse_line(server, "AliasActual").split()))
            await self.bot.say(msg)
        
    @points.group(pass_context=True)
    @checks.admin()
    async def language(self, ctx: commands.Context):
        """Edit language used for factions."""
        if ctx.invoked_subcommand is self.language:
            await send_cmd_help(ctx)
            
    @language.command(pass_context=True, name="edit")
    @checks.admin()
    async def lang_edit(self, ctx: commands.Context, lang_name: str, new_lang: str):
        """Edits a line in the language.
        WARNING: Make sure you know what parameters are in the line!
        Misspellings of parameter names will likely result in a crash.
        Also note that if a parameter is not used in the default language line, it is not available for use in your custom language line.
        Finally, any multi-word language lines must be encapsulated in quotes, as seen in the first example.

        Examples: [p]points language edit points_added \"<faction_name> has earned <points> <point_name>!\"
                  [p]points language edit point_name karma
        Note that if you edit the point name to a mass noun, you should also edit the suffix appropriately:
                  [p]points language edit suffix \"\""""
        server = ctx.message.server
        language = self._load_server(server, "language")
        if lang_name not in language:
            await self.bot.say(self._parse_line(server, "lang_no_line", lang_name=lang_name))
        else:
            language[lang_name] = new_lang
            dataIO.save_json(FILE_PATH, self.json)

    @language.command(pass_context=True,  name="list")
    @checks.admin()
    async def lang_list(self, ctx: commands.Context):
        """Lists all language lines."""
        server = ctx.message.server
        language = self._load_server(server, "language")
        msg = tabulate(sorted(language.items()), self._parse_line(server, "AliasActual").split())
        for page in pagify(msg, ["\n"]):
            await self.bot.say(box(page))

    @language.command(pass_context=True, name="reset")
    @checks.admin()
    async def lang_reset(self, ctx: commands.Context):
        """Resets all language back to defaults."""
        server = ctx.message.server
        language = self._load_server(server, "language")
        language.update(default_language)
        dataIO.save_json(FILE_PATH, self.json)
        await self.bot.say(self._parse_line(server, "lang_reset"))

    @points.command(pass_context=True)
    @checks.mod_or_permissions(administrator=True)
    async def add(self, ctx: commands.Context, faction_name: str, points: int):
        """Adds a given number of points to a faction."""
        server = ctx.message.server
        if points <= 0:
            await self.bot.say(self._parse_line(server, "points_added", plural=False))
        faction_name = self._get_alias(server, faction_name)
        factions = self._load_server(server)
        if faction_name not in factions:
            await self.bot.say(self._parse_line(server, "faction_no_exists", faction_name=faction_name))
        else:
            factions[faction_name] += points
            await self.bot.say(self._parse_line(server, "points_added", plural=points > 1, points=points, faction_name=faction_name, new_points=factions[faction_name]))
            dataIO.save_json(FILE_PATH, self.json)

    @points.command(pass_context=True)
    @checks.mod_or_permissions(administrator=True)
    async def remove(self, ctx: commands.Context, faction_name: str, points: int):
        """Removes a given number of points to a faction."""
        server = ctx.message.server
        faction_name = self._get_alias(server, faction_name)
        factions = self._load_server(server)
        if faction_name not in factions:
            await self.bot.say(self._parse_line(server, "faction_no_exists", faction_name=faction_name))
        else:
            if factions[faction_name] <= 0:
                await self.bot.say(self._parse_line(server, "points_zero", faction_name=faction_name))
                return
            points = min(points, factions[faction_name])
            factions[faction_name] -= points
            await self.bot.say(self._parse_line(server, "points_removed", plural=points > 1, points=points, faction_name=faction_name, new_points=factions[faction_name]))
            dataIO.save_json(FILE_PATH, self.json)

    @points.command(pass_context=True)
    async def check(self, ctx: commands.Context, *, faction_name: str):
        """Checks the current point tally for a faction."""
        server = ctx.message.server
        faction_name = self._get_alias(server, faction_name)
        factions = self._load_server(server)
        if faction_name not in factions:
            await self.bot.say(self._parse_line(server, "faction_no_exists", faction_name=faction_name))
        else:
            points = factions[faction_name]
            await self.bot.say(self._parse_line(server, "points_faction", plural=points > 1, faction_name=faction_name, points=points))

    @points.command(pass_context=True)
    async def checkall(self, ctx: commands.Context):
        """Lists the point tallies for all factions."""
        server = ctx.message.server
        factions = self._load_server(server)
        if not factions:
            await self.bot.say(self._parse_line(server, "faction_none", prefix=ctx.prefix))
        else:
            await self.bot.say(box(tabulate(sorted(factions.items(), key=lambda k: k[1], reverse=True), (self._parse_line(server, "Faction"), self._parse_line(server, "point_name").title()+self._parse_line(server, "suffix")))))


def check_folder():
    folder = os.path.dirname(FILE_PATH)
    if not os.path.exists(folder):
        log.debug('Creating folder: %s' % folder)
        os.makedirs(folder)


def check_file():
    if dataIO.is_valid_json(FILE_PATH) is False:
        log.debug('Creating json: %s' % os.path.basename(FILE_PATH))
        dataIO.save_json(FILE_PATH, {})


def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(Factions(bot))
