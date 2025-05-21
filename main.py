import sys
import os
import time
import random
import polars as pl
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="WARNING") 

BOARD_SIZE = 15
EMPTY_CHAR = '.'
DIR_HORIZ = 1
DIR_VERT = 0

START_TILES = "AAAAAAAAABBCCDDDDEEEEEEEEEEEEFFGGGHHIIIIIIIIIJKLLLLMMNNNNNNOOOOOOOOPPQRRRRRRSSSSTTTTTTUUUUVVWWXYYZ**"

TILE_POINTS = {
    'E': 1, 'A': 1, 'I': 1, 'O': 1, 'N': 1, 'R': 1, 'T': 1, 'L': 1, 'S': 1, 'U': 1,
    'D': 2, 'G': 2,
    'B': 3, 'C': 3, 'M': 3, 'P': 3,
    'F': 4, 'H': 4, 'V': 4, 'W': 4, 'Y': 4,
    'K': 5,
    'J': 8, 'X': 8,
    'Q': 10, 'Z': 10,
    '*': 0
}

TW_INDICES = {(0, 0), (7, 0), (14, 0), (0, 7), (14, 7), (0, 14), (7, 14), (14, 14)}
DW_INDICES = {(1, 1), (2, 2), (3, 3), (4, 4), (10, 4), (11, 3), (12, 2), (13, 1),
              (1, 13), (2, 12), (3, 11), (4, 10), (10, 10), (11, 11), (12, 12), (13, 13),
              (7, 7)}
TL_INDICES = {(1, 5), (1, 9), (5, 1), (5, 5), (5, 9), (5, 13),
              (9, 1), (9, 5), (9, 9), (9, 13), (13, 5), (13, 9)}
DL_INDICES = {(0, 3), (0, 11), (2, 6), (2, 8), (3, 0), (3, 7), (3, 14),
              (6, 2), (6, 6), (6, 8), (6, 12), (7, 3), (7, 11),
              (8, 2), (8, 6), (8, 8), (8, 12), (11, 0), (11, 7), (11, 14),
              (12, 6), (12, 8), (14, 3), (14, 11)}


# GADDAG
DELIMITER = '>'

def direction_to_vector(d: int):
    if d == DIR_HORIZ:
        return (1, 0)
    elif d == DIR_VERT:
        return (0, 1)

def score_letters(letters: str):
    score = 0
    for c in letters:
        score += TILE_POINTS[c]
    return score

class Node:
    __slots__ = ('children', 'is_terminal', '_id')
    _next_id_counter = 0  # global id counter

    def __init__(self) -> None:
        self.children = {}  # char -> GaddagNode
        self.is_terminal = False
        self._id = Node._next_id_counter
        Node._next_id_counter += 1

    def __repr__(self) -> str:
        return f"Node(id={self._id}, term={self.is_terminal}, children={list(self.children.keys())})"

class GADDAG:

    def __init__(self, dictionary: str = "") -> None:
        self.root = Node()

        if dictionary != "":
            self._load_dictionary_file(dictionary)

    
    def __repr__(self) -> str:
        node_count = self.root._next_id_counter
        # Show immediate children of the root as a glimpse
        root_children = list(self.root.children.keys()) if self.root else []
        return f"GADDAG(root_children={root_children}, approx_nodes={node_count})"

    def _insert(self, path: str):
        """
        Inserts a single path string into the structure,
        creating nodes as needed. Marks the final node as terminal.
        """
        node = self.root
        for char in path:
            if char not in node.children:
                new_node = Node()
                node.children[char] = new_node
            node = node.children[char]
        node.is_terminal = True

    @classmethod
    def dfs(cls, node: Node, query: str, depth: int = 0, max_depth: int = 26, check_valid_word: bool = True) -> bool:
        if depth == max_depth:
            # suppose valid word
            return True
        if depth == len(query):
            # reached end
            if check_valid_word:
                return node.is_terminal
            return True
        if query[depth] not in node.children:
            return False
        
        return cls.dfs(node.children[query[depth]], query, depth + 1, max_depth, check_valid_word)

    def follow(self, query: str, depth: int = 0, node: Node | None = None):
        if node is None:
            node = self.root

        if depth == len(query):
            return node
        
        if query[depth] not in node.children:
            logger.warning(f"follow {query} was not found.\n\tended at node: {node}")
            return None
        
        return self.follow(query, depth=depth+1, node=node.children[query[depth]])


    def search(self, query: str) -> bool:
        query_reverse_list = list(query.upper())[::-1]

        def dfs(node: Node, depth: int):
            if depth == len(query_reverse_list):
                return node.is_terminal
            if query_reverse_list[depth] not in node.children:
                return False
            return dfs(node.children[query_reverse_list[depth]], depth + 1)

        return dfs(self.root, 0)

    def add_word(self, word: str):
        """
        Generates and inserts all necessary GADDAG paths for a given word.
        Follows the definition L = {REV(x) > y | xy is word, x non-empty}
        and the special case for REV(word) when y is empty.
        """
        word = word.upper()

        # Path for the whole reversed word (suffix y is empty, rule 1 pg 3)
        # This path represents starting at the *last* letter of the word on the board.
        reversed_word = word[::-1]
        self._insert(reversed_word)

        # Paths for REV(prefix) > suffix, where prefix is non-empty
        for i in range(1, len(word)):
            prefix = word[:i]   # x (non-empty)
            suffix = word[i:]   # y
            reversed_prefix = prefix[::-1]

            # Construct path: REV(x) + DELIMITER + y
            path = reversed_prefix + DELIMITER + suffix
            self._insert(path)

    def _load_dictionary_file(self, path: str):
        if os.path.exists(path):
            with open(path, 'r') as f:
                for word in f.read().split('\n'):
                    if word:
                        self.add_word(word)

class ScrabbleBoard:
    """
    Represents a Scrabble board using a 2D list.
    Handles tile placement and basic board queries.
    """
    def __init__(self):
        """Initializes an empty 15x15 board."""
        self.board = [[EMPTY_CHAR for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.anchor_points = {(7, 7)}
        self.blank_positions: set = set()

    def _is_valid(self, x: int, y: int) -> bool:
        """Checks if coordinates are within the board bounds."""
        return 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE

    def place_tile(self, x: int, y: int, tile: str, force: bool = False):
        """Places a tile (uppercase string) on the board."""
        if not self._is_empty_square(x, y) and not force:
            return False
        if not isinstance(tile, str) or len(tile) != 1 or not tile.isalpha():
            return False

        self.board[x][y] = tile
        return True

    def get_tile(self, x: int, y: int) -> str | None:
        """Gets the tile at (x, y), or None if empty or invalid coords."""
        if not self._is_valid(x, y):
            return None
        return self.board[x][y]

    def _add_anchor_point(self, x: int, y: int):
        if self._is_empty_square(x, y):
            self.anchor_points.add((x, y))

    def _update_anchor_point(self, x: int, y: int):
        self.anchor_points.discard((x, y))
        for dx, dy in {(1, 0), (-1, 0), (0, 1), (0, -1)}:
            self._add_anchor_point(x + dx, y + dy)

    def _update_anchor_points(self, x: int, y: int, direction: int, length: int, reverse: bool = False):
        if reverse:
            if direction == DIR_HORIZ:
                x -= length
            elif direction == DIR_VERT:
                y -= length
        dx, dy = (1, 0) if direction == DIR_HORIZ else (0, 1)
        # add prefix
        self._add_anchor_point(x - dx, y - dy)
        for r in range(length):
            self.anchor_points.discard((x + r * dx, y + r * dy))
            self._add_anchor_point(x + r * dx - dy, y + r * dy - dx)
            self._add_anchor_point(x + r * dx + dy, y + r * dy + dx)
        # add suffix
        self._add_anchor_point(x + length * dx, y + length * dy)

    def place_word(self, x: int, y: int, direction: int, word: str, wild_cards: list, reverse: bool = False):
        chars = word.upper()
        for i in range(len(chars)):
            px, py = x, y
            if direction == DIR_HORIZ:
                if reverse:
                    px = x - i
                else:
                    px = x + i
            elif direction == DIR_VERT:
                if reverse:
                    py = y - i
                else:
                    py = y + i

            if reverse:
                char = chars[-i - 1]
            else:
                char = chars[i]
            
            if [px, py] in wild_cards:
                self.blank_positions.add((px, py))

            self.place_tile(px, py, char)
            self._update_anchor_point(px, py)

        # self._update_anchor_points(x, y, direction, len(word), reverse=reverse)

    def _is_empty_square(self, x: int, y: int) -> bool:
        """Checks if the square at (x, y) is empty (and valid)."""
        return self._is_valid(x, y) and self.board[x][y] == EMPTY_CHAR

    def _score_dfs(self, x: int, y: int, dx: int, dy: int, score: int = 0, wild_cards: set = set()):
        if self._is_empty_square(x, y) or not self._is_valid(x, y):
            return score

        return self._score_dfs(x + dx, y + dy, dx, dy, score + self._score_tile(x, y, self.get_tile(x, y), wild_cards))

    def _score_tile(self, x: int, y: int, letter: str | None, wild_cards: set):
        if letter is None:
            # sanity check
            return -1000
        if (x, y) in self.blank_positions or (x, y) in wild_cards:
            return 0
        else:
            return TILE_POINTS[letter]

    def score(self, x: int, y: int, direction: int, word: str, wild_cards: set = set()):
        letters_played = ''
        primary_score = 0
        primary_score_multiplier = 1
        secondary_score = 0
        dx, dy = (1, 0) if direction == DIR_HORIZ else (0, 1)
        for i in range(len(word)):
            px, py = x - i * dx, y - i * dy
            tile_score = self._score_tile(px, py, word[-i - 1], wild_cards)

            if not self._is_empty_square(px, py):
                primary_score += self._score_tile(px, py, self.get_tile(px, py), wild_cards)
                continue
            else:
                if (px, py) in wild_cards:
                    letters_played += '*'
                else:
                    letters_played += word[-i - 1]

            neighbour_score = self._score_dfs(px - dy, py - dx, -dy, -dx) + self._score_dfs(px + dy, py + dx, dy, dx)
            if neighbour_score != 0:
                if (px, py) in TL_INDICES:
                    neighbour_score += 3 * tile_score
                elif (px, py) in DL_INDICES:
                    neighbour_score += 2 * tile_score
                else:
                    neighbour_score += tile_score

            if (px, py) in TW_INDICES:
                primary_score_multiplier *= 3
                neighbour_score *= 3
            elif (px, py) in DW_INDICES:
                primary_score_multiplier *= 2
                neighbour_score *= 2

            if (px, py) in TL_INDICES:
                primary_score += 3 * tile_score
            elif (px, py) in DL_INDICES:
                primary_score += 2 * tile_score
            else:
                primary_score += 1 * tile_score

            secondary_score += neighbour_score

        if len(letters_played) == 7:
            secondary_score += 50

        return primary_score * primary_score_multiplier + secondary_score, letters_played

    def display(self, display_axis: bool = False):
        """Simple text display of the board."""
        if display_axis:
            print("\n   ", " ".join(f"{i:<2}" for i in range(BOARD_SIZE)))
        print(f"{'   ' if display_axis else ''}", "-" * (BOARD_SIZE * 3 - 1))
        for y in range(BOARD_SIZE):
            if display_axis:
                print(f"{y:<2}|", end="")
            else:
                print("|", end="")
            for x in range(BOARD_SIZE):
                tile = self.get_tile(x, y) # Use get_tile for safety
                if tile == EMPTY_CHAR:
                    if display_axis:
                        tile = '.'
                    else:
                        tile = ' '
                print(f" {tile} ", end="")
            print("|")
        print(f"{'   ' if display_axis else ''}", "-" * (BOARD_SIZE * 3 - 1))

    def display_debug(self, mode: str = 'tiles', tag: int = 7):
        print("\n   ", " ".join(f"{i:<2}" for i in range(BOARD_SIZE)))
        print("   ", "-" * (BOARD_SIZE * 3 - 1))
        for y in range(BOARD_SIZE):
            print(f"{y:<2}|", end="")
            for x in range(BOARD_SIZE):
                tile = '.'
                if mode == 'tiles':
                    if (x,y) in TW_INDICES:
                        tile = 'T'
                    elif (x,y) in DW_INDICES:
                        tile = 'D'
                    elif (x,y) in TL_INDICES:
                        tile = 't'
                    elif (x,y) in DL_INDICES:
                        tile = 'd'
                if mode == 'plays':
                    if (x, y) in self.anchor_points:
                        tile = '+'
                    elif not self._is_empty_square(x, y):
                        tile = ' '

                print(f" {tile} ", end="")
            print("|")
        print("   ", "-" * (BOARD_SIZE * 3 - 1))

    def to_gcp(self) -> str:
        output = ""
        for j in range(BOARD_SIZE):
            count = 0
            for i in range(BOARD_SIZE):
                tile = self.get_tile(i, j)
                if tile == EMPTY_CHAR:
                    count += 1
                else:
                    if count > 0:
                        output += str(count)
                    output += str(tile)
                    count = 0
            if count == 15:
                output += "15"
            if j < BOARD_SIZE - 1:
                if count > 0 and count < 15:
                    output += str(count)
                output += '/'
        return output
    
    def from_gcp(self, gcp: str, force: bool = True):
        row_index = 0
        col_index = 0
        i = 0
        while i < len(gcp):
            if gcp[i] == '/':
                row_index += 1
                col_index = 0
                i += 1
                continue

            if gcp[i].isdigit():
                if i < len(gcp) - 1 and gcp[i + 1].isdigit():
                    count = int(gcp[i:i + 2])
                    i += 1
                else:
                    count = int(gcp[i])
                for _ in range(count):
                    self.place_tile(col_index, row_index, EMPTY_CHAR, force=force)
                    col_index += 1
            else:
                self.place_tile(col_index, row_index, gcp[i], force=force)
                col_index += 1
            i += 1

class ScrabbleBag:
    def __init__(self):
        self.tiles = list(START_TILES)

    def __bool__(self):
        return len(self.tiles) != 0

    def pick(self, size: int = 7):
        hand = ''
        for _ in range(size):
            if len(self.tiles) == 0:
                break
            c = random.choice(self.tiles)
            self.tiles.remove(c)
            hand += c
        return hand

class Rack:

    def __init__(self, bag: ScrabbleBag, tiles: str | None = None) -> None:
        self.bag = bag
        if tiles is None:
            self.tiles = self.bag.pick(7)
        else:
            self.tiles = tiles

    def __repr__(self) -> str:
        """Returns a representation showing the tiles in the rack."""
        return f"Rack(tiles='{self.tiles}')"

    def __bool__(self) -> bool:
        return len(self.tiles) > 0

    def __iter__(self):
        for t in set(self.tiles):
            yield t

    def __len__(self):
        return len(self.tiles)

    def __in__(self, other):
        if isinstance(other, str):
            return other in self.tiles
        else:
            raise TypeError(f"Excepted str not {type(other)} in Rack.__in__")

    def __sub__(self, other):
        if isinstance(other, str):
            tiles = list(self.tiles)
            for letter in other:
                if letter in tiles:
                    tiles.remove(letter)
            return Rack(self.bag, tiles=''.join(tiles))

        else:
            raise TypeError(f"Excepted str not {type(other)} in Rack.__sub__")

    def __add__(self, other):
        if isinstance(other, str):
            tiles = self.tiles + other
            return Rack(self.bag, tiles=tiles)
        else:
            raise TypeError(f"Excepted str not {type(other)} in Rack.__sub__")

    def diff(self, other):
        if isinstance(other, Rack):
            tmp = self.tiles
            for char in other.tiles:
                tmp = tmp.replace(char, '')

            return tmp
        else:
            raise TypeError(f"Excepted str not {type(other)} in Rack.diff")

    def copy(self):
        return Rack(self.bag, self.tiles)

    def to_gcp(self) -> str:
        return self.tiles

def valid_placement(board: ScrabbleBoard, x: int, y: int, letter: str) -> bool:
    return True

class Solver:

    def __init__(self, board: ScrabbleBoard, root: Node, rack: Rack):
        self.board = board
        self.root = root 
        self.rack = rack
        self.moves = []

    def find_moves(self):
        for (x, y) in self.board.anchor_points:
            for d in [DIR_HORIZ, DIR_VERT]:
                self.x = x
                self.y = y
                self.direction = d
                self.gen(0, '', self.rack.copy(), self.root)
                # self.dfs(0, '', self.rack.copy(), self.root)
                # self._gen(0, '', self.rack, self.root)

        return pl.from_dicts(self.moves, schema={
            'x': pl.Int32,
            'y': pl.Int32,
            'direction': pl.Int32,
            'word': pl.String,
            'score': pl.Int32,
            'letters': pl.String,
            'wild_cards': pl.List(pl.List(pl.Int32))
        }).sort('score', descending=True)

    
    def _convert_pos(self, pos: int):
        # optimise remove check
        if self.direction == DIR_HORIZ:
            return self.x + pos, self.y
        elif self.direction == DIR_VERT:
            return self.x, self.y + pos
        else:
            raise ValueError(f"Unkown direction {self.direction}")

    def _dfs_single(self, node: Node, x: int, y: int, dx: int, dy: int):
        if not self.board._is_valid(x + dx, y + dy):
            # edge of board
            return node.is_terminal
        if self.board._is_empty_square(x + dx, y + dy):
            # end of word
            return node.is_terminal
        next_letter = self.board.get_tile(x + dx, y + dy)
        if next_letter not in node.children:
            return False

        return self._dfs_single(node.children[next_letter], x + dx, y + dy, dx, dy)

    def _dfs_dual(self, node: Node, ax: int, ay: int, x: int, y: int, dx: int, dy: int, can_end: bool = False):
        if not self.board._is_valid(ax + x + dx, ay + y + dy) or self.board._is_empty_square(ax + x + dx, ay + y + dy):
            if can_end:
                return node.is_terminal
            if DELIMITER not in node.children:
                return False
            return self._dfs_dual(node.children[DELIMITER], ax, ay, 0, 0, -dx, -dy, can_end=True)

        next_letter = self.board.get_tile(ax + x + dx, ay + y + dy)
        if next_letter not in node.children:
            return False
        return self._dfs_dual(node.children[next_letter], ax ,ay, x + dx, y + dy, dx, dy, can_end=can_end)
        
    def _is_cross_valid(self, x: int, y: int, letter: str) -> bool:
        if letter == DELIMITER:
            return False
        if not self.board._is_empty_square(x, y):
            return False
        if letter not in self.root.children:
            return False

        dx, dy = (1, 0) if self.direction == DIR_VERT else (0, 1)

        # check adjacent squares
        prefix = self.board.get_tile(x - dx, y - dy)
        prefix_present = prefix is not None and prefix != EMPTY_CHAR

        suffix = self.board.get_tile(x + dx, y + dy)
        suffix_present = suffix is not None and suffix != EMPTY_CHAR

        if prefix_present and suffix_present:
            return self._dfs_dual(self.root.children[letter], x, y, 0, 0, -dx, -dy, can_end=False)
        if prefix_present:
            return self._dfs_single(self.root.children[letter], x, y, -dx, -dy)
        if suffix_present:
            if DELIMITER not in self.root.children[letter].children:
                return False
            return self._dfs_single(self.root.children[letter].children[DELIMITER], x, y, dx, dy)

        # both suffix and prefix are empty any word is valid
        return True

    def gen(self, pos: int, word: str, rack: Rack, root: Node, wild_cards: set = set()):
        logger.debug(f"{pos, word, rack, root}")
        x, y = self._convert_pos(pos)

        if not self.board._is_valid(x, y):
            return

        tile = self.board.get_tile(x, y)
        if tile is not None and tile != EMPTY_CHAR:
            logger.debug(f"{x, y}| [{tile}] present")
            # tile present
            if tile in root.children:
                # in word
                if pos > 0:
                    logger.debug(f"contining right {tile} {word}")
                    # checking forward
                    self.go_on(pos, tile, word, rack, root.children[tile], wild_cards)
                elif pos <= 0:
                    logger.debug(f"contining left {tile} {word}")
                    self.go_on(pos, tile, word, rack, root.children[tile], wild_cards)
            else:
                # don't continue
                logger.debug(f"not a valid word {word} {tile} {pos}")
                pass
        else:
            # tile is valid and empty
            # choose letter
            for letter in rack:
                if letter in root.children:
                    if self._is_cross_valid(x, y, letter):
                        logger.debug(f"Letter[{letter}] Valid at {x, y} - {word} {pos}")
                        self.go_on(pos, letter, word, rack - letter, root.children[letter], wild_cards)
            if '*' in rack:
                for letter in root.children:
                    if self._is_cross_valid(x, y, letter):
                        logger.debug(f"Blank Letter[{letter}] Valid at {x, y} - {word}")
                        wild_cards.add((x, y))
                        self.go_on(pos, letter, word, rack - '*', root.children[letter], wild_cards)
                        wild_cards.remove((x, y))


    def go_on(self, pos: int, letter: str, word: str, rack: Rack, root: Node, wild_cards: set):
        logger.debug(f"{pos, letter, word, rack, root}")
        x, y = self._convert_pos(pos)
        left_pos = self._convert_pos(pos - 1)
        right_pos = self._convert_pos(pos + 1)
        right_side = self._convert_pos(1)

        directly_left_playable = self.board._is_valid(*left_pos)
        directly_left_tile = self.board.get_tile(*left_pos)
        directly_right_playable = self.board._is_valid(*right_pos)
        directly_right_tile = self.board.get_tile(*right_pos)
        right_side_playable = self.board._is_valid(*right_side)
        right_side_tile = self.board.get_tile(*right_side)

        if pos <= 0:
            word = letter + word
            logger.debug(f"{x, y}| moving left {word}")
            if root.is_terminal and (not directly_left_playable or directly_left_tile == EMPTY_CHAR) and (not right_side_playable or right_side_tile == EMPTY_CHAR):
                self._record_play(pos, word, rack, wild_cards)

            if DELIMITER in root.children and right_side_playable and (not directly_left_playable or directly_left_tile == EMPTY_CHAR):
                self.gen(1, word, rack, root.children[DELIMITER], wild_cards)

            if directly_left_playable:
                self.gen(pos - 1, word, rack, root, wild_cards)

        else:
            word = word + letter
            logger.debug(f"{x, y}| moving right {word}")
            if root.is_terminal and (not directly_right_playable or directly_right_tile == EMPTY_CHAR):
                self._record_play(pos, word, rack, wild_cards)

            self.gen(pos + 1, word, rack, root, wild_cards)

    def _record_play(self, pos: int, word: str, rack: Rack, wild_cards: set = set()):
        if len(word) == 0:
            return

        if pos <= 0:
            x, y = self.x, self.y
        else:
            x, y = self._convert_pos(pos)

        score, letters_played = self.board.score(x, y, self.direction, word, wild_cards)

        logger.info(f"{x, y, word, score, letters_played, wild_cards}")
        self.moves.append({
            'x': x,
            'y': y,
            'direction': self.direction,
            'word': word,
            'score': score,
            'letters': letters_played,
            'wild_cards': [list(p) for p in wild_cards]
        })


class ScrabbleGame:

    def __init__(self, number_of_players: int = 2, path: str = 'dictionary.txt'):
        self.gaddag = GADDAG(path)
        self.number_of_players = number_of_players
        self.dictionary_path = path
        self.game_id = -1
        self.reset()

        self.analytics = {
            'possible_moves': [],
            'moves': []
        }

    def reset(self, ):
        self.game_id += 1
        self.board = ScrabbleBoard()
        self.bag = ScrabbleBag()
        self.scores = [0] * self.number_of_players
        self.racks = [Rack(self.bag) for _ in range(self.number_of_players)]

    def _analytics_add_moves(self, play_index: int, moves_df: pl.DataFrame):
        self.analytics['possible_moves'].append(moves_df.with_columns(player=pl.lit(play_index)).drop('wild_cards'))

    def _analytics_add_play(self, turn_index: int, play_index: int, x: int, y: int, direction: int, word: str, score: int, letters: str, wild_cards: list):
        start_x, start_y = (x - len(word) + 1, y) if direction == DIR_HORIZ else (x, y - len(word) + 1)
        self.analytics['moves'].append({
            'game_id': self.game_id,
            'turn': turn_index,
            'player': play_index,
            'start_x': start_x,
            'start_y': start_y,
            'end_x': x,
            'end_y': y,
            'direction': direction,
            'word': word,
            'score': score,
            'letters': letters,
        })

    def play_turn(self, turn_index: int, display: bool = False):
        player_index = turn_index % self.number_of_players
        if display:
            print(f"Player[{player_index}] rack: {self.racks[player_index]}")
        solver = Solver(self.board, self.gaddag.root, self.racks[player_index])
        best_moves_df = solver.find_moves()
        self._analytics_add_moves(player_index, best_moves_df)
        if len(best_moves_df) == 0:
            return
        
        x, y, direction, word, score, letters, wild_cards = best_moves_df[0].to_dicts()[0].values()
        self._analytics_add_play(turn_index, player_index, x, y, direction, word, score, letters, wild_cards)
        self.racks[player_index] -= letters
        self.racks[player_index] += self.bag.pick(len(letters))
        self.scores[player_index] += score
        self.board.place_word(x, y, direction, word, wild_cards, reverse=True)

        if display:
            print(f"Player[{player_index}] played {word} for {score} points")

    def play_game(self, display: bool = True):
        turn_index = 0

        while all(self.racks) and turn_index < 100:
            if display:
                self.board.display(display_axis=True)
            self.play_turn(turn_index, display=display)
            turn_index += 1

        end_player_index = (turn_index - 1) % 2

        for i in range(self.number_of_players):
            points_left = score_letters(self.racks[i].tiles)
            self.scores[i] -= points_left
            self.scores[end_player_index] += points_left

        print(self.scores)

    def to_gcp(self) -> str:
        board = self.board.to_gcp()
        rack = "/".join([self.racks[i].to_gcp() for i in range(self.number_of_players)])
        scores = "/".join([str(self.scores[i]) for i in range(self.number_of_players)])
        return f"{board} {rack} {scores}"

    def from_gcp(self, gcp: str):
        board, rack, scores = gcp.split(' ')
        self.board.from_gcp(board)
        self.racks = [Rack(self.bag, tiles=tiles) for tiles in rack.split('/')]
        self.scores = [int(s) for s in scores.split('/')]



