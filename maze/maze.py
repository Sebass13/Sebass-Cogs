# -*- coding: utf-8 -*-
import random

# Easy to read representation for each cardinal direction.
N, S, W, E = ('n', 's', 'w', 'e')

class Cell(object):
    """
    Class for each individual cell. Knows only its position and which walls are
    still standing.
    """
    def __init__(self, x, y, walls):
        self.x = x
        self.y = y
        self.walls = set(walls)

    def __repr__(self):
        # <15, 25 (es  )>
        return '<{}, {} ({:4})>'.format(self.x, self.y, ''.join(sorted(self.walls)))

    def __contains__(self, item):
        # N in cell
        return item in self.walls

    def is_full(self):
        """
        Returns True if all walls are still standing.
        """
        return len(self.walls) == 4

    def _wall_to(self, other):
        """
        Returns the direction to the given cell from the current one.
        Must be one cell away only.
        """
        assert abs(self.x - other.x) + abs(self.y - other.y) == 1, '{}, {}'.format(self, other)
        if other.y < self.y:
            return N
        elif other.y > self.y:
            return S
        elif other.x < self.x:
            return W
        elif other.x > self.x:
            return E
        else:
            assert False

    def connect(self, other):
        """
        Removes the wall between two adjacent cells.
        """
        other.walls.remove(other._wall_to(self))
        self.walls.remove(self._wall_to(other))

class Maze(object):
    """
    Maze class containing full board and maze generation algorithms.
    """

    # Unicode character for a wall with other walls in the given directions.
    UNICODE_BY_CONNECTIONS = {'ensw': '┼',
                              'ens': '├',
                              'enw': '┴',
                              'esw': '┬',
                              'es': '┌',
                              'en': '└',
                              'ew': '─',
                              'e': '╶',
                              'nsw': '┤',
                              'ns': '│',
                              'nw': '┘',
                              'sw': '┐',
                              's': '╷',
                              'n': '╵',
                              'w': '╴'}

    def __init__(self, width=20, height=10, player=None, target=None):
        """
        Creates a new maze with the given sizes, with all walls standing.
        """
        self.width = width
        self.height = height
        self.target = target
        if not (player and target):
            self.player = self._get_random_position()
            self.target = self._get_random_position()
            while self.target == self.player:
                self.target = self._get_random_position()
                
            
        self.cells = []
        for y in range(self.height):
            for x in range(self.width):
                self.cells.append(Cell(x, y, [N, S, E, W]))

    def __getitem__(self, index):
        """
        Returns the cell at index = (x, y).
        """
        x, y = index
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.cells[x + y * self.width]
        else:
            return None

    def neighbors(self, cell):
        """
        Returns the list of neighboring cells, not counting diagonals. Cells on
        borders or corners may have less than 4 neighbors.
        """
        x = cell.x
        y = cell.y
        for new_x, new_y in [(x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y)]:
            neighbor = self[new_x, new_y]
            if neighbor is not None:
                yield neighbor        
        
    def _get_random_position(self):
        """
        Returns a random position on the maze.
        """
        return (random.randrange(0, self.width),
                random.randrange(0, self.height))
        
    def _adjust_pos(self, tup):
        return (tup[1] * 2 + 1, tup[0] * 4 + 2)

    def _to_str_matrix(self):
        """
        Returns a matrix with a pretty printed visual representation of this
        maze. Example 5x5:

        OOOOOOOOOOO
        O       O O
        OOO OOO O O
        O O   O   O
        O OOO OOO O
        O   O O   O
        OOO O O OOO
        O   O O O O
        O OOO O O O
        O     O   O
        OOOOOOOOOOO
        """
        str_matrix = [['O'] * (self.width * 2 + 1)
                      for i in range(self.height * 2 + 1)]

        for cell in self.cells:
            x = cell.x * 2 + 1
            y = cell.y * 2 + 1
            str_matrix[y][x] = ' '
            if N not in cell and y > 0:
                str_matrix[y - 1][x + 0] = ' '
            if S not in cell and y + 1 < self.width:
                str_matrix[y + 1][x + 0] = ' '
            if W not in cell and x > 0:
                str_matrix[y][x - 1] = ' '
            if E not in cell and x + 1 < self.width:
                str_matrix[y][x + 1] = ' '

        return str_matrix

    def _matrix(self):
        """
        Returns an Unicode representation of the maze. Size is doubled
        horizontally to avoid a stretched look. Example 5x5:

        ┌───┬───────┬───────┐
        │   │       │       │
        │   │   ╷   ╵   ╷   │
        │   │   │       │   │
        │   │   └───┬───┘   │
        │   │       │       │
        │   └───────┤   ┌───┤
        │           │   │   │
        │   ╷   ╶───┘   ╵   │
        │   │               │
        └───┴───────────────┘
        """
        # Starts with regular representation. Looks stretched because chars are
        # twice as high as they are wide (look at docs example in
        # `Maze._to_str_matrix`).
        skinny_matrix = self._to_str_matrix()

        # Simply duplicate each character in each line.
        double_wide_matrix = []
        for line in skinny_matrix:
            double_wide_matrix.append([])
            for char in line:
                double_wide_matrix[-1].append(char)
                double_wide_matrix[-1].append(char)

        # The last two chars of each line are walls, and we will need only one.
        # So we remove the last char of each line.
        matrix = [line[:-1] for line in double_wide_matrix]

        def g(x, y):
            """
            Returns True if there is a wall at (x, y). Values outside the valid
            range always return false.

            This is a temporary helper function.
            """
            if 0 <= x < len(matrix[0]) and 0 <= y < len(matrix):
                return matrix[y][x] != ' '
            else:
                return False

        # Fix double wide walls, finally giving the impression of a symmetric
        # maze.
        for y, line in enumerate(matrix):
            for x, char in enumerate(line):
                if not g(x, y) and g(x - 1, y):
                    matrix[y][x - 1] = ' '

        # Right now the maze has the correct aspect ratio, but is still using
        # 'O' to represent walls.

        # Finally we replace the walls with Unicode characters depending on
        # their context.
        for y, line in enumerate(matrix):
            for x, char in enumerate(line):
                if not g(x, y):
                    continue

                connections = set((N, S, E, W))
                if not g(x, y + 1): connections.remove(S)
                if not g(x, y - 1): connections.remove(N)
                if not g(x + 1, y): connections.remove(E)
                if not g(x - 1, y): connections.remove(W)

                str_connections = ''.join(sorted(connections))
                # Note we are changing the matrix we are reading. We need to be
                # careful as to not break the `g` function implementation.
                matrix[y][x] = Maze.UNICODE_BY_CONNECTIONS[str_connections]
        return matrix

    def __repr__(self):
        mat = self._matrix()
        player = self._adjust_pos(self.player)
        target = self._adjust_pos(self.target)
        mat[target[0]][target[1]] = "$"
        mat[player[0]][player[1]] = "@"
        return '\n'.join(''.join(line) for line in mat) + '\n'

    def randomize(self):
        """
        Knocks down random walls to build a random perfect maze.

        Algorithm from http://mazeworks.com/mazegen/mazetut/index.htm
        """
        cell_stack = []
        cell = random.choice(self.cells)
        n_visited_cells = 1

        while n_visited_cells < len(self.cells):
            neighbors = [c for c in self.neighbors(cell) if c.is_full()]
            if len(neighbors):
                neighbor = random.choice(neighbors)
                cell.connect(neighbor)
                cell_stack.append(cell)
                cell = neighbor
                n_visited_cells += 1
            else:
                cell = cell_stack.pop()

    @staticmethod
    def generate(width=20, height=10):
        """
        Returns a new random perfect maze with the given sizes.
        """
        m = Maze(width, height)
        m.randomize()
        return m
        
############################
# BEGIN COG IMPLEMENTATION #
############################

import asyncio
from discord.ext import commands
from cogs.utils.chat_formatting import box
from __main__ import send_cmd_help

class MazeCog:
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(pass_context=True, name="maze")
    async def play_maze(self, ctx, width: int=20, height: int=10):
        """Create an interactive maze just for you!
        Maximum width of 20 and maximum height of 10."""
        if width > 20 or height > 10:
            await send_cmd_help(ctx)
            return
        
        author = ctx.message.author
        maze = Maze.generate(width, height)
        msgobj = await self.bot.say(box(maze))
        choices = {"\u25c0": (W, -1, 0),
                   "\U0001f53c": (N, 0, -1),
                   "\U0001f53d": (S, 0, 1),
                   "\u25b6": (E, 1, 0),
                   "\u274c": "exit"}
        
        for em in choices:
            await self.bot.add_reaction(msgobj, em)
        
        choice = True
        while maze.player != maze.target:
            choice = await wait_for_interaction(self.bot, msgobj, author, choices)
            if choice is None:
                await self.bot.say("Inactive for 2 minutes, game has concluded.")
                for em in reversed(list(choices)):
                    self.bot.remove_reaction(msgobj, em)
                return
            if choice == "exit":
                await self.bot.delete_message(msgobj)
                return
            direction, difx, dify = choice

            current_cell = maze[maze.player]
            if direction not in current_cell:
                maze.player = (maze.player[0] + difx, maze.player[1] + dify)
            msgobj = await self.bot.edit_message(msgobj, box(maze))
        await self.bot.say("You win!")
        
        
    async def on_reaction_remove(self, reaction, user):
        """Handles watching for reactions for wait_for_reaction_remove"""
        for event in _reaction_remove_events:
            if (event and not event.is_set() and
                event.check(reaction, user) and
                reaction.emoji in event.emojis):
                event.set(reaction)
        
##############
# EMOJI SHIT #
##############
     
_reaction_remove_events = set()

class ReactionRemoveEvent(asyncio.Event):
    def __init__(self, emojis, author, check=None):
        super().__init__()
        self.emojis = emojis
        self.author = author
        self.reaction = None
        self.check = check

    def set(self, reaction):
        self.reaction = reaction
        return super().set()
    
async def wait_for_result(task, converter):
    """await the task call and return its results parsed through the converter"""
    # why did I do this?
    return converter(await task)

async def wait_for_first_response(tasks, converters):
    """given a list of unawaited tasks and non-coro result parsers to be called on the results,
    this function returns the 1st result that is returned and converted
    if it is possible for 2 tasks to complete at the same time,
    only the 1st result deteremined by asyncio.wait will be returned
    returns None if none successfully complete
    returns 1st error raised if any occur (probably)
    """
    primed = [wait_for_result(t, c) for t, c in zip(tasks, converters)]
    done, pending = await asyncio.wait(primed, return_when=asyncio.FIRST_COMPLETED)
    for p in pending:
        p.cancel()

    try:
        return done.pop().result()
    except NotImplementedError as e:
        raise e
    except:
        return None
        
async def wait_for_interaction(bot, msg, author, choices,
                               timeout=120):
    """waits for a reaction add/remove"""

    emojis = tuple(choices.keys())

    def rcheck(reaction, user):
        return True

    kwreact = {'timeout': timeout, 'message': msg,
               'emoji': emojis, 'check': rcheck,
               'user': author}

    tasks = (bot.wait_for_reaction(**kwreact),
             wait_for_reaction_remove(bot, **kwreact))

    def mojichoice(r):
        if not r:
            return None
        return choices[r.reaction.emoji]

    converters = (mojichoice, mojichoice)
    return await wait_for_first_response(tasks, converters)


async def wait_for_reaction_remove(bot, emoji=None, *, user=None,
                                   timeout=None, message=None, check=None):
    """Waits for a reaction to be removed by a user from a message within a time period.
    Made to act like other discord.py wait_for_* functions but is not fully implemented.
    Because of that, wait_for_reaction_remove(self, emoji: list, user, message, timeout=None)
    is a better representation of this function's def
    returns the actual event or None if timeout
    """
    if not emoji or isinstance(emoji, str):
        raise NotImplementedError("wait_for_reaction_remove(self, emoji, "
                                  "message, user=None, timeout=None, "
                                  "check=None) is a better representation "
                                  "of this function definition")
    remove_event = ReactionRemoveEvent(emoji, user, check=check)
    _reaction_remove_events.add(remove_event)
    done, pending = await asyncio.wait([remove_event.wait()],
                                       timeout=timeout)
    still_in = remove_event in _reaction_remove_events
    _reaction_remove_events.remove(remove_event)
    try:
        return done.pop().result() and still_in and remove_event
    except:
        return None
    
def setup(bot):
    bot.add_cog(MazeCog(bot))
