from time import time
from random import randint
from json import dumps as jdumps, loads as jloads
import sqlite3
from zlib import compress as zcompress, decompress as zdecompress
from codecs import decode as cdecode
import lightbulb, hikari
import os
import chess

with open("./config.json") as f:
    config = jloads(f.read())

db = sqlite3.connect(config["dburi"])

setting_defaults = {"dm_notifications": True}

dev = False
if os.name == "nt":
    dev = True
else:
    import uvloop

    uvloop.install()

if dev:
    default_guilds = config["debugguilds"]
    token = config["debugbottoken"]
else:
    default_guilds = []
    token = config["bottoken"]

readable = {
    "TicTacToe": "Tic Tac Toe",
    "UltTicTacToe": "Ultimate Tic Tac Toe",
    "ConnectFour": "Connect Four",
    "Battleship": "Battleship",
    "Chess": "Chess",
}


def get_options(user, option):
    cur = db.cursor()
    response = cur.execute(
        f"SELECT setting FROM {option} WHERE user_id = {user}"
    ).fetchone()
    cur.close()
    if response is None:
        return setting_defaults[option]
    return response[0]


def set_options(user, option, setting):

    print(f"INSERT OR IGNORE INTO {option} (user_id) VALUES ({user})")
    print(f"UPDATE {option} SET setting = {setting} WHERE user_id = {user}")

    cur = db.cursor()
    cur.execute(f"INSERT OR IGNORE INTO {option} (user_id) VALUES ({user})")
    cur.execute(f"UPDATE {option} SET setting = {setting} WHERE user_id = {user}")
    cur.close()
    db.commit()


class TicTacToe:
    def __init__(
        self,
        players,
        guild_id,
        turn=randint(0, 1),
        board=[[None, None, None], [None, None, None], [None, None, None]],
    ):
        self.players = players
        self.guild_id = guild_id
        self.turn = turn
        self.board = board
        self.emojis = ["🇽", "🇴"]
        self.styles = [
            hikari.ButtonStyle.DANGER,
            hikari.ButtonStyle.PRIMARY,
            hikari.ButtonStyle.SECONDARY,
        ]
        self.winner = None

    def get_moves(self):
        moves = []
        for (y, m) in enumerate(self.board):
            for (x, n) in enumerate(m):
                if n is None:
                    moves.append(f"{x}|{y}")
        return moves

    def make_move(self, move):
        if move in self.get_moves():
            movep = move.split("|")
            self.board[int(movep[1])][int(movep[0])] = self.turn
            self.checkwin()
            if self.winner is None:
                self.turn = (self.turn + 1) % 2
                return True
        return False

    def get_data(self):
        return {
            "players": self.players,
            "turn": self.turn,
            "board": self.board,
            "type": "TicTacToe",
            "guild_id": self.guild_id,
        }

    def build_components(self):
        components = []
        for (y, n) in enumerate(self.board):
            components.append(bot.rest.build_action_row())
            for (x, m) in enumerate(n):
                if self.winner is not None:
                    winnerstyle = self.styles[self.winner]
                    self.styles = [winnerstyle, winnerstyle, winnerstyle]
                if m is not None:
                    b = components[y].add_button(self.styles[m], f"{x}|{y}")
                    b.set_is_disabled(True)
                    b.set_emoji(self.emojis[m])
                else:
                    b = components[y].add_button(self.styles[2], f"{x}|{y}")
                    if self.winner is not None:
                        b.set_is_disabled(True)
                    b.set_emoji("⬛")
                b.add_to_container()

        return components

    def build_message(self):
        if self.winner is None:
            return {
                "text": f"```{encode(self.get_data())}\n[{readable['TicTacToe']}]```{self.emojis[self.turn]} <@{self.players[self.turn]}>'s turn!",
                "components": self.build_components(),
            }
        else:
            if self.winner == 2:
                return {
                    "text": f"```{encode(self.get_data())}\n[{readable['TicTacToe']}]```🚮 TIE!",
                    "components": self.build_components(),
                }
            else:
                return {
                    "text": f"```{encode(self.get_data())}\n[{readable['TicTacToe']}]```{self.emojis[self.turn]} <@{self.players[self.turn]}> is the WINNER!",
                    "components": self.build_components(),
                }

    def checkwin(self):
        if len(self.get_moves()) == 0:
            self.winner = 2
        for i in range(0, 3):
            if self.board[i][0] == self.board[i][1] == self.board[i][2] and (
                self.board[i][0] is not None
            ):
                self.winner = self.board[i][0]
                return
            if self.board[0][i] == self.board[1][i] == self.board[2][i] and (
                self.board[0][i] is not None
            ):
                self.winner = self.board[0][i]
                return
        if self.board[0][0] == self.board[1][1] == self.board[2][2] and (
            self.board[0][0] is not None
        ):
            self.winner = self.board[0][0]
            return
        if self.board[0][2] == self.board[1][1] == self.board[2][0] and (
            self.board[0][2] is not None
        ):
            self.winner = self.board[0][2]
            return

    @staticmethod
    def load_data(data):
        return TicTacToe(data["players"], data["guild_id"], data["turn"], data["board"])


class UltTicTacToe:
    def __init__(
        self,
        players,
        guild_id,
        turn=randint(0, 1),
        board=[
            [[[None for _ in range(3)] for _ in range(3)] for _ in range(3)]
            for _ in range(3)
        ],
        boardwinners=[[None, None, None], [None, None, None], [None, None, None]],
        currentboard=[None, None],
    ):
        self.players = players
        self.guild_id = guild_id
        self.turn = turn
        self.board = board
        self.emojis = ["🇽", "🇴"]
        self.formatted = ["x", "o", "t"]
        self.styles = [
            hikari.ButtonStyle.DANGER,
            hikari.ButtonStyle.PRIMARY,
            hikari.ButtonStyle.SECONDARY,
        ]
        self.winner = None
        self.boardwinners = boardwinners
        self.currentboard = currentboard

    def get_data(self):
        return {
            "players": self.players,
            "turn": self.turn,
            "board": self.board,
            "type": "UltTicTacToe",
            "boardwinners": self.boardwinners,
            "currentboard": self.currentboard,
            "guild_id": self.guild_id,
        }

    @staticmethod
    def load_data(data):
        return UltTicTacToe(
            data["players"],
            data["guild_id"],
            data["turn"],
            data["board"],
            data["boardwinners"],
            data["currentboard"],
        )

    def get_moves(self, meta=False):
        moves = []
        board = self.boardwinners
        if self.currentboard[0] is not None and not meta:
            board = self.board[self.currentboard[1]][self.currentboard[0]]
        for (y, m) in enumerate(board):
            for (x, n) in enumerate(m):
                if n is None:
                    moves.append(f"{x}|{y}")
        return moves

    def make_move(self, move):
        meta = False
        if self.currentboard[0] is None:
            meta = True
        if move in self.get_moves():
            movep = move.split("|")
            if not meta:
                self.board[self.currentboard[1]][self.currentboard[0]][int(movep[1])][
                    int(movep[0])
                ] = self.turn
                self.checkwin()
            self.metacheckwin()
            if self.boardwinners[int(movep[1])][int(movep[0])] is None:
                self.currentboard = [int(movep[1]), int(movep[0])]
            else:
                self.currentboard = [None, None]
            if self.winner is None and not meta:
                self.turn = (self.turn + 1) % 2
                return True
        return False

    def checkwin(self):
        if len(self.get_moves()) == 0:
            self.boardwinners[self.currentboard[0]][self.currentboard[1]] = 2
        for i in range(0, 3):
            if self.board[self.currentboard[1]][self.currentboard[0]][i][
                0
            ] == self.board[self.currentboard[1]][self.currentboard[0]][i][
                1
            ] == self.board[
                self.currentboard[1]
            ][
                self.currentboard[0]
            ][
                i
            ][
                2
            ] and (
                self.board[self.currentboard[1]][self.currentboard[0]][i][0] is not None
            ):
                self.boardwinners[self.currentboard[0]][
                    self.currentboard[1]
                ] = self.board[self.currentboard[1]][self.currentboard[0]][i][0]
                return
            if self.board[self.currentboard[1]][self.currentboard[0]][0][
                i
            ] == self.board[self.currentboard[1]][self.currentboard[0]][1][
                i
            ] == self.board[
                self.currentboard[1]
            ][
                self.currentboard[0]
            ][
                2
            ][
                i
            ] and (
                self.board[self.currentboard[1]][self.currentboard[0]][0][i] is not None
            ):
                self.boardwinners[self.currentboard[0]][
                    self.currentboard[1]
                ] = self.board[self.currentboard[1]][self.currentboard[0]][0][i]
                return
        if self.board[self.currentboard[1]][self.currentboard[0]][0][0] == self.board[
            self.currentboard[1]
        ][self.currentboard[0]][1][1] == self.board[self.currentboard[1]][
            self.currentboard[0]
        ][
            2
        ][
            2
        ] and (
            self.board[self.currentboard[1]][self.currentboard[0]][0][0] is not None
        ):
            self.boardwinners[self.currentboard[0]][self.currentboard[1]] = self.board[
                self.currentboard[1]
            ][self.currentboard[0]][0][0]
            return
        if self.board[self.currentboard[1]][self.currentboard[0]][0][2] == self.board[
            self.currentboard[1]
        ][self.currentboard[0]][1][1] == self.board[self.currentboard[1]][
            self.currentboard[0]
        ][
            2
        ][
            0
        ] and (
            self.board[self.currentboard[1]][self.currentboard[0]][0][2] is not None
        ):
            self.boardwinners[self.currentboard[0]][self.currentboard[1]] = self.board[
                self.currentboard[1]
            ][self.currentboard[0]][0][2]
            return

    def metacheckwin(self):
        if len(self.get_moves(True)) == 0:
            self.winner = 2
        for i in range(0, 3):
            if self.boardwinners[i][0] == self.boardwinners[i][1] == self.boardwinners[
                i
            ][2] and (self.boardwinners[i][0] is not None):
                self.winner = self.boardwinners[i][0]
                return
            if self.boardwinners[0][i] == self.boardwinners[1][i] == self.boardwinners[
                2
            ][i] and (self.boardwinners[0][i] is not None):
                self.winner = self.boardwinners[0][i]
                return
        if self.boardwinners[0][0] == self.boardwinners[1][1] == self.boardwinners[2][
            2
        ] and (self.boardwinners[0][0] is not None):
            self.winner = self.boardwinners[0][0]
            return
        if self.boardwinners[0][2] == self.boardwinners[1][1] == self.boardwinners[2][
            0
        ] and (self.boardwinners[0][2] is not None):
            self.winner = self.boardwinners[0][2]
            return

    def build_components(self):
        components = []
        board = self.boardwinners
        if self.currentboard[0] is not None and self.winner is None:
            board = self.board[self.currentboard[1]][self.currentboard[0]]
        for (y, n) in enumerate(board):
            components.append(bot.rest.build_action_row())
            for (x, m) in enumerate(n):
                if self.winner is not None:
                    winnerstyle = self.styles[self.winner]
                    self.styles = [winnerstyle, winnerstyle, winnerstyle]
                metaboard = False
                if self.currentboard == [y, x] and self.winner is None:
                    metaboard = True
                if m is not None:
                    if metaboard:
                        b = components[y].add_button(
                            hikari.ButtonStyle.SUCCESS, f"{x}|{y}"
                        )
                    else:
                        b = components[y].add_button(self.styles[m], f"{x}|{y}")
                    b.set_is_disabled(True)
                    b.set_emoji(self.emojis[m])
                else:
                    if metaboard:
                        b = components[y].add_button(
                            hikari.ButtonStyle.SUCCESS, f"{x}|{y}"
                        )
                    else:
                        b = components[y].add_button(self.styles[2], f"{x}|{y}")
                    if self.winner is not None:
                        b.set_is_disabled(True)
                    b.set_emoji("⬛")
                b.add_to_container()
        r = bot.rest.build_action_row()
        r.add_button(
            hikari.ButtonStyle.LINK,
            r"https://en.wikipedia.org/wiki/Ultimate_tic-tac-toe",
        ).set_label("Wikipedia Article (Rules)").add_to_container()
        components.append(r)
        return components

    def build_message(self):
        meta = False
        if self.currentboard[0] is None:
            meta = True

        bigboard = self.build_big_board()

        if self.winner is None:
            if meta:
                return {
                    "text": f"```{encode(self.get_data())}\n[{readable['UltTicTacToe']}]{bigboard}```{self.emojis[self.turn]} <@{self.players[self.turn]}>'s turn! pick a board!",
                    "components": self.build_components(),
                }
            else:
                return {
                    "text": f"```{encode(self.get_data())}\n[{readable['UltTicTacToe']}]{bigboard}```{self.emojis[self.turn]} <@{self.players[self.turn]}>'s turn!",
                    "components": self.build_components(),
                }
        else:
            if self.winner == 2:
                return {
                    "text": f"```{encode(self.get_data())}\n[{readable['UltTicTacToe']}]{bigboard}```🚮 TIE!",
                    "components": self.build_components(),
                }
            else:
                return {
                    "text": f"```{encode(self.get_data())}\n[{readable['UltTicTacToe']}]{bigboard}```{self.emojis[self.turn]} <@{self.players[self.turn]}> is the WINNER!",
                    "components": self.build_components(),
                }

    def build_big_board(self):
        string = ""
        filter = True
        if self.winner is None:
            filter = False

        for i in range(3):
            for j in range(3):
                string += f"\n{self.get_piece(i, j, 0, 0, filter)}  {self.get_piece(i, j, 0, 1, filter)}  {self.get_piece(i, j, 0, 2, filter)} | {self.get_piece(i, j, 1, 0, filter)}  {self.get_piece(i, j, 1, 1, filter)}  {self.get_piece(i, j, 1, 2, filter)} | {self.get_piece(i, j, 2, 0, filter)}  {self.get_piece(i, j, 2, 1, filter)}  {self.get_piece(i, j, 2, 2, filter)}"
            if i < 2:
                string += "\n--------+---------+--------"

        return string

    def get_piece(self, c, b, a, d, filter):
        if not filter and self.boardwinners[c][a] is not None:
            return self.formatted[self.boardwinners[c][a]]
        else:
            if self.board[a][c][b][d] is not None:
                return self.formatted[self.board[a][c][b][d]]
            else:
                return "_"


class ConnectFour:
    def __init__(
        self,
        players,
        guild_id,
        turn=randint(0, 1),
        board=[[None for _ in range(6)] for _ in range(7)],
    ):
        self.players = players
        self.guild_id = guild_id
        self.turn = turn
        self.board = board
        self.winner = None
        self.nummap = {
            0: "1️⃣",
            1: "2️⃣",
            2: "3️⃣",
            3: "4️⃣",
            4: "5️⃣",
            5: "6️⃣",
            6: "7️⃣",
            7: "8️⃣",
            8: "9️⃣",
            9: "🔟",
        }
        self.emojis = [":red_circle:", ":green_circle:"]
        self.winningemojis = [":japanese_goblin:", ":frog:"]
        c = 0
        for (i, j) in enumerate(players):
            if j in config["nerds"]:
                self.emojis[i] = [":nerd:", ":rage:"][c]
                self.winningemojis[i] = [
                    ":lying_face:",
                    ":face_with_symbols_over_mouth:",
                ][c]
                c += 1
        self.winningpieces = [[False for _ in range(6)] for _ in range(7)]
        self.emptyspace = ":small_blue_diamond:"

    def get_moves(self):
        moves = []
        for i in range(len(self.board)):
            if None in self.board[i]:
                moves.append(i)
        return moves

    def make_move(self, move):
        move = int(move)
        if move in self.get_moves():
            for i in range(len(self.board[move])):
                if self.board[move][i] is None:
                    self.board[move][i] = self.turn
                    break
            self.checkwin()
            if self.winner is None:
                self.turn = (self.turn + 1) % 2
                return True
        return False

    def get_data(self):
        return {
            "players": self.players,
            "turn": self.turn,
            "board": self.board,
            "type": "ConnectFour",
            "guild_id": self.guild_id,
        }

    def build_components(self):
        components = []
        if self.winner is not None:
            return components
        moves = self.get_moves()
        for i in range(len(self.board)):
            if (i % 5) == 0:
                if i != 0:
                    components.append(row)
                row = bot.rest.build_action_row()
            disabled = True
            style = hikari.ButtonStyle.SECONDARY
            if i in moves:
                disabled = False
                style = hikari.ButtonStyle.PRIMARY
            b = row.add_button(style, f"{i}")
            b.set_is_disabled(disabled)
            b.set_emoji(self.nummap.get(i, "⛔"))
            # b.set_label(i + 1)
            b.add_to_container()
        components.append(row)
        return components

    def build_message(self):
        gamemap = self.buildmap()
        if self.winner is None:
            return {
                "text": f"```{encode(self.get_data())}\n[{readable['ConnectFour']}]```<@{self.players[self.turn]}>'s turn!\n{gamemap}",
                "components": self.build_components(),
            }
        else:
            if self.winner == 2:
                return {
                    "text": f"```\n[{readable['ConnectFour']}]```TIE!\n{gamemap}",
                    "components": self.build_components(),
                }
            else:
                return {
                    "text": f"```\n[{readable['ConnectFour']}]```<@{self.players[self.turn]}> is the WINNER!\n{gamemap}",
                    "components": self.build_components(),
                }

    def buildmap(self):
        gamemap = ""
        for i in range(len(self.board)):
            gamemap += self.nummap.get(i, ":no_entry:")
        for i in range(len(self.board[0])):
            gamemap += "\n"
            for j in range(len(self.board)):
                if self.board[j][len(self.board[j]) - i - 1] is None:
                    gamemap += self.emptyspace
                else:
                    if self.winningpieces[j][len(self.board[j]) - i - 1]:
                        gamemap += self.winningemojis[
                            self.board[j][len(self.board[j]) - i - 1]
                        ]
                    else:
                        gamemap += self.emojis[
                            self.board[j][len(self.board[j]) - i - 1]
                        ]
        return gamemap

    def checkwin(self):
        for i in range(len(self.board)):
            for j in range(len(self.board[i])):
                if i < (len(self.board) - 3) and j < len(self.board[i]):
                    if (
                        self.board[i][j]
                        == self.board[i + 1][j]
                        == self.board[i + 2][j]
                        == self.board[i + 3][j]
                    ) and self.board[i][j] is not None:
                        for g in range(4):
                            self.winningpieces[i + g][j] = True
                        self.winner = self.board[i][j]
                        return
                if i < (len(self.board)) and j < (len(self.board[i]) - 3):
                    if (
                        self.board[i][j]
                        == self.board[i][j + 1]
                        == self.board[i][j + 2]
                        == self.board[i][j + 3]
                    ) and self.board[i][j] is not None:
                        for g in range(4):
                            self.winningpieces[i][j + g] = True
                        self.winner = self.board[i][j]
                        return
                if i < (len(self.board) - 3) and j < (len(self.board[i]) - 3):
                    if (
                        self.board[i][j]
                        == self.board[i + 1][j + 1]
                        == self.board[i + 2][j + 2]
                        == self.board[i + 3][j + 3]
                    ) and self.board[i][j] is not None:
                        for g in range(4):
                            self.winningpieces[i + g][j + g] = True
                        self.winner = self.board[i][j]
                        return
                if i < (len(self.board) - 3) and j > 2:
                    if (
                        self.board[i][j]
                        == self.board[i + 1][j - 1]
                        == self.board[i + 2][j - 2]
                        == self.board[i + 3][j - 3]
                    ) and self.board[i][j] is not None:
                        for g in range(4):
                            self.winningpieces[i + g][j - g] = True
                        self.winner = self.board[i][j]
                        return
        if len(self.get_moves()) == 0:
            self.winner = 2

    @staticmethod
    def load_data(data):
        return ConnectFour(
            data["players"], data["guild_id"], data["turn"], data["board"]
        )


class Battleship:
    def __init__(
        self,
        players,
        guild_id,
        turn=None,
        board=[
            [[None for _ in range(10)] for _ in range(10)],
            [[None for _ in range(10)] for _ in range(10)],
        ],
        setup=True,
        pieces=[[5, 4, 3, 3, 2] for _ in range(2)],
        # pieces=[[2] for _ in range(2)],
        selected=[{}, {}],
        player=None,
        winner=None,
    ):
        self.players = players
        self.guild_id = guild_id
        self.turn = turn
        self.board = board
        self.winner = winner
        self.setup = setup
        self.pieces = pieces
        self.piece = None
        self.meta = None
        self.selected = selected
        self.axisemotes = [
            ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"],
            ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯"],
        ]
        self.diremotes = ["⬆️", "⬇️", "⬅️", "➡️"]
        self.dirmap = [[-1, 0], [1, 0], [0, -1], [0, 1]]
        self.player = player
        self.piecesleft = []
        if self.player is not None:
            for (i, j) in enumerate(self.pieces[self.player]):
                if type(j) == type(0):
                    if self.piece is None:
                        self.piece = i
                    self.piecesleft.append(j)
        self.hit = ""

    def get_moves(self):
        moves = []
        if self.setup:
            for i in range(10):
                moves.append(f"y|{i}")
            for i in range(10):
                moves.append(f"x|{i}")
            moves.append("d|0")
            moves.append("d|1")
            moves.append("d|2")
            moves.append("d|3")
            moves.append("MAP")
        else:
            for i in range(10):
                moves.append(f"y|{i}")
            for i in range(10):
                moves.append(f"x|{i}")
            moves.append("MAP")

        return moves

    def make_move(self, move):
        ping = False
        if move == "MAP":
            self.meta = "map"
            return
        if move in self.get_moves():
            if self.setup:
                # for (i, j) in enumerate(self.pieces[self.player]):
                #     if type(j) == type(0):
                #         self.piece = i
                #         break
                movep = move.split("|")
                if self.piece is None:
                    self.meta = "noneleft"
                    return
                if (
                    self.selected[self.player].get("x", None) is None
                    or self.selected[self.player].get("y", None) is None
                ) and movep[0] == "d":
                    self.meta = "direction"
                    return
                if movep[0] == "d":
                    shiplength = self.pieces[self.player][self.piece]
                    direction = self.dirmap[int(movep[1])]
                    for i in range(shiplength):
                        if (
                            0
                            > (
                                int(self.selected[self.player]["x"])
                                + (direction[0] * i)
                            )
                            or (
                                int(self.selected[self.player]["x"])
                                + (direction[0] * i)
                            )
                            > 9
                        ):
                            self.meta = "offmap"
                            return
                        if (
                            0
                            > (
                                int(self.selected[self.player]["y"])
                                + (direction[1] * i)
                            )
                            or (
                                int(self.selected[self.player]["y"])
                                + (direction[1] * i)
                            )
                            > 9
                        ):
                            self.meta = "offmap"
                            return
                        for ship in self.pieces[self.player]:
                            if not type(ship) == type(0):
                                if [
                                    int(self.selected[self.player]["x"])
                                    + (direction[0] * i),
                                    int(self.selected[self.player]["y"])
                                    + (direction[1] * i),
                                ] in ship:
                                    self.meta = "offmap"
                                    return
                    self.pieces[self.player][self.piece] = []
                    for i in range(shiplength):
                        self.pieces[self.player][self.piece].append(
                            [
                                int(self.selected[self.player]["x"])
                                + (direction[0] * i),
                                int(self.selected[self.player]["y"])
                                + (direction[1] * i),
                            ]
                        )
                    self.selected[self.player] = {}
                else:
                    self.selected[self.player][movep[0]] = movep[1]
            else:
                movep = move.split("|")
                if self.player != self.turn:
                    self.meta = "noturturn"
                    return

                if (
                    movep[0] == "x"
                    and self.selected[self.turn].get("y", None) is not None
                ):
                    if (
                        self.board[self.turn][int(movep[1])][
                            self.selected[self.turn]["y"]
                        ]
                        is not None
                    ):
                        self.meta = "alreadyhit"
                        return
                if (
                    movep[0] == "y"
                    and self.selected[self.turn].get("x", None) is not None
                ):
                    if (
                        self.board[self.turn][self.selected[self.turn]["x"]][
                            int(movep[1])
                        ]
                        is not None
                    ):
                        self.meta = "alreadyhit"
                        return

                self.selected[self.turn][movep[0]] = int(movep[1])

                x = self.selected[self.turn].get("x", None)
                y = self.selected[self.turn].get("y", None)

                if x is not None and y is not None:
                    hit = False
                    for i in self.pieces[(self.turn + 1) % 2]:
                        for j in i:
                            if j == [x, y]:
                                hit = True
                                break
                        if hit:
                            break
                    self.board[self.turn][x][y] = hit
                    if hit:
                        self.hit = ":boom: HIT! "
                    else:
                        self.hit = ":dash: MISS! "
                    self.selected[self.turn] = {}
                else:
                    self.meta = "updateboard"
                    return

            self.checkwin()
            if self.winner is None and not self.setup:
                self.turn = (self.turn + 1) % 2
                ping = True
        return ping

    def get_data(self):
        data = {
            "players": self.players,
            "turn": self.turn,
            "board": self.board,
            "setup": self.setup,
            "type": "Battleship",
            "guild_id": self.guild_id,
            "pieces": self.pieces,
            "selected": self.selected,
            "winner": self.winner,
        }
        return data

    def build_components(self):
        components = []
        if self.winner is None:
            for i in range(10):
                if (i % 5) == 0:
                    if i != 0:
                        components.append(row)
                    row = bot.rest.build_action_row()
                row.add_button(hikari.ButtonStyle.PRIMARY, f"y|{i}").set_emoji(
                    self.axisemotes[0][i]
                ).add_to_container()
            components.append(row)
            row = bot.rest.build_action_row()
            row.add_button(hikari.ButtonStyle.SUCCESS, f"d|0").set_emoji(
                self.diremotes[0]
            ).set_is_disabled(not self.setup).add_to_container()
            row.add_button(hikari.ButtonStyle.SUCCESS, f"d|1").set_emoji(
                self.diremotes[1]
            ).set_is_disabled(not self.setup).add_to_container()
            row.add_button(hikari.ButtonStyle.SECONDARY, f"MAP").set_emoji(
                "🗺️"
            ).add_to_container()
            row.add_button(hikari.ButtonStyle.SUCCESS, f"d|2").set_emoji(
                self.diremotes[2]
            ).set_is_disabled(not self.setup).add_to_container()
            row.add_button(hikari.ButtonStyle.SUCCESS, f"d|3").set_emoji(
                self.diremotes[3]
            ).set_is_disabled(not self.setup).add_to_container()
            components.append(row)
            for i in range(10):
                if (i % 5) == 0:
                    if i != 0:
                        components.append(row)
                    row = bot.rest.build_action_row()
                row.add_button(hikari.ButtonStyle.PRIMARY, f"x|{i}").set_emoji(
                    self.axisemotes[1][i]
                ).add_to_container()
            components.append(row)
        else:
            pass
            # row = bot.rest.build_action_row()
            # row.add_button(hikari.ButtonStyle.SECONDARY, f"MAP").set_emoji(
            #     "🗺️"
            # ).add_to_container()
            # components.append(row)
        return components

    def build_map(self, secret=False, player=None):
        gamemap = ""
        if self.winner is None:
            if self.setup:
                seamap = self.board[self.player]
                ships = self.pieces[self.player]
                selected = []
                selected.append(self.selected[self.player].get("x", None))
                selected.append(self.selected[self.player].get("y", None))
                selected.append(self.selected[self.player].get("d", None))

                for i in range(len(selected)):
                    if selected[i] is not None:
                        selected[i] = int(selected[i])

                for i in ships:
                    if not (type(i) == type(0)):
                        for j in i:
                            seamap[j[0]][j[1]] = "filled"
                topbar = ""
                if selected[2] is None:
                    topbar += ":black_large_square:"
                else:
                    topbar += self.diremotes[selected[2]]
                for i in range(10):
                    topbar += self.axisemotes[0][i]
                if self.piece == None:
                    gamemap += (
                        f"```\nAll pieces selected, waiting on other player!```{topbar}"
                    )
                else:
                    gamemap += f"```\nselecting space for a {self.pieces[self.player][self.piece]} tile long ship\nShips left:\n{str(self.piecesleft).replace('[', '').replace(']', '')}```{topbar}"
                for i in range(len(seamap)):
                    gamemap += f"\n{self.axisemotes[1][i]}"
                    for j in range(len(seamap[0])):
                        if seamap[i][j] is None:
                            if selected[0] is not None and selected[1] is None:
                                if i == selected[0]:
                                    gamemap += ":traffic_light:"
                                else:
                                    gamemap += ":ocean:"
                            elif selected[0] is None and selected[1] is not None:
                                if j == selected[1]:
                                    gamemap += ":vertical_traffic_light:"
                                else:
                                    gamemap += ":ocean:"
                            elif selected[0] is not None and selected[1] is not None:
                                if i == selected[0] and j == selected[1]:
                                    gamemap += ":negative_squared_cross_mark:"
                                else:
                                    gamemap += ":ocean:"
                            else:
                                gamemap += ":ocean:"
                        else:
                            gamemap += ":ship:"
            else:
                if secret:
                    player = self.player
                    seamap = [[None for _ in range(10)] for _ in range(10)]
                    ships = self.pieces[player]
                    for i in ships:
                        if not (type(i) == type(0)):
                            for j in i:
                                seamap[j[0]][j[1]] = "filled"
                    gamemap += ":black_large_square:"
                    for i in range(10):
                        gamemap += self.axisemotes[0][i]
                    for i in range(len(seamap)):
                        gamemap += f"\n{self.axisemotes[1][i]}"
                        for j in range(len(seamap[0])):
                            if seamap[i][j] is None:
                                gamemap += ":ocean:"
                            else:
                                gamemap += ":ship:"
                else:
                    player = (self.turn + 1) % 2
                    shipmap = [[None for _ in range(10)] for _ in range(10)]
                    ships = self.pieces[player]
                    for i in ships:
                        if not (type(i) == type(0)):
                            for j in i:
                                shipmap[j[0]][j[1]] = "filled"
                    seamap = self.board[self.turn]
                    selected = []
                    selected.append(self.selected[self.turn].get("x", None))
                    selected.append(self.selected[self.turn].get("y", None))
                    for i in range(len(selected)):
                        if selected[i] is not None:
                            selected[i] = int(selected[i])
                    gamemap += ":black_large_square:"
                    for i in range(10):
                        gamemap += self.axisemotes[0][i]
                    for i in range(len(seamap)):
                        gamemap += f"\n{self.axisemotes[1][i]}"
                        for j in range(len(seamap[0])):
                            if seamap[i][j] is None:
                                if selected[0] is not None and selected[1] is None:
                                    if i == selected[0]:
                                        gamemap += ":traffic_light:"
                                    else:
                                        gamemap += ":ocean:"
                                elif selected[0] is None and selected[1] is not None:
                                    if j == selected[1]:
                                        gamemap += ":vertical_traffic_light:"
                                    else:
                                        gamemap += ":ocean:"
                                else:
                                    gamemap += ":ocean:"
                            else:
                                if shipmap[i][j] is None:
                                    gamemap += ":dash:"
                                else:
                                    gamemap += ":boom:"
        else:
            if player is None:
                player = self.player
            seamap = self.board[(player + 1) % 2]
            shipmap = [[None for _ in range(10)] for _ in range(10)]
            ships = self.pieces[player]
            for i in ships:
                if not (type(i) == type(0)):
                    for j in i:
                        shipmap[j[0]][j[1]] = "filled"
            gamemap += ":black_large_square:"
            for i in range(10):
                gamemap += self.axisemotes[0][i]
            for i in range(len(seamap)):
                gamemap += f"\n{self.axisemotes[1][i]}"
                for j in range(len(seamap[0])):
                    if seamap[i][j] is None:
                        if shipmap[i][j] is None:
                            gamemap += ":ocean:"
                        else:
                            gamemap += ":ship:"
                    else:
                        if shipmap[i][j] is None:
                            gamemap += ":dash:"
                        else:
                            gamemap += ":boom:"
        return gamemap

    def build_message(self):
        if self.winner is None:
            if self.setup:
                if self.player is None:
                    return {
                        "text": f"```{encode(self.get_data())}\n[{readable['Battleship']}]```SETUP!",
                        "components": self.build_components(),
                    }
                else:
                    if self.meta == "map":
                        return {
                            "responsetype": hikari.ResponseType.MESSAGE_CREATE,
                            "text": f"{self.build_map()}",
                            "flags": hikari.MessageFlag.EPHEMERAL,
                        }
                    if self.meta == "direction":
                        return {
                            "responsetype": hikari.ResponseType.MESSAGE_CREATE,
                            "text": f"Select the ship direction last, this will confirm the ship placement\n(note: one of your inputs probably got eaten, here is your current grid)\n{self.build_map()}",
                            "flags": hikari.MessageFlag.EPHEMERAL,
                        }
                    if self.meta == "offmap":
                        return {
                            "responsetype": hikari.ResponseType.MESSAGE_CREATE,
                            "text": f"Ship placement invalid, ship either overlaps another ship or ends up off the edge of the map\n try another direction or change ship placement",
                            "flags": hikari.MessageFlag.EPHEMERAL,
                        }
                    if self.meta == "noneleft":
                        return {
                            "responsetype": hikari.ResponseType.MESSAGE_CREATE,
                            "text": f"You dont have any pieces left you little goober, wait for your opponent to finish their selections!",
                            "flags": hikari.MessageFlag.EPHEMERAL,
                        }
                    else:
                        return {
                            "text": f"```{encode(self.get_data())}\n[{readable['Battleship']}]```SETUP!",
                            "components": self.build_components(),
                        }
            else:
                if self.meta == "map":
                    return {
                        "responsetype": hikari.ResponseType.MESSAGE_CREATE,
                        "text": f"{self.build_map(True)}",
                        "flags": hikari.MessageFlag.EPHEMERAL,
                    }
                if self.meta == "alreadyhit":
                    return {
                        "responsetype": hikari.ResponseType.MESSAGE_CREATE,
                        "text": f"You've already fired there, silly, thatd be a waste of a turn!",
                        "flags": hikari.MessageFlag.EPHEMERAL,
                    }
                if self.meta == "noturturn":
                    return {
                        "responsetype": hikari.ResponseType.MESSAGE_CREATE,
                        "text": f"You can only check your map when it isnt your turn!",
                        "flags": hikari.MessageFlag.EPHEMERAL,
                    }

                return {
                    "text": f"```{encode(self.get_data())}\n[{readable['Battleship']}]```{self.hit}<@{self.players[self.turn]}>'s turn!\n{self.build_map()}",
                    "components": self.build_components(),
                }
        else:
            # if self.meta == "map":
            #     return {
            #         "responsetype": hikari.ResponseType.MESSAGE_CREATE,
            #         "text": f"{self.build_map()}",
            #         "flags": hikari.MessageFlag.EPHEMERAL,
            #     }
            embeds = []
            for i in range(2):
                embeds.append(
                    hikari.Embed(
                        title=f"Player {i}", description=self.build_map(player=i)
                    )
                )
            return {
                "text": f"```\n[{readable['Battleship']}]```<@{self.players[self.turn]}> (player {self.turn}) is the WINNER!",
                "embeds": embeds,
                "components": self.build_components(),
            }

    def checkwin(self):
        if self.setup:
            totalleft = 0
            for i in self.pieces[0]:
                if type(i) == type(1):
                    totalleft += 1
            for i in self.pieces[1]:
                if type(i) == type(1):
                    totalleft += 1
            if totalleft == 0:
                self.setup = False
                self.turn = randint(0, 1)
        else:
            hitcount = 0
            for i in self.board[self.turn]:
                for j in i:
                    if j == True:
                        hitcount += 1
            if hitcount == 17:
                self.winner = self.turn

    @staticmethod
    def load_data(data, player=None):
        if player is not None:
            for (i, j) in enumerate(data["players"]):
                if player == j:
                    player = i
                    break
        return Battleship(
            data["players"],
            data["guild_id"],
            data["turn"],
            data["board"],
            data["setup"],
            data["pieces"],
            data["selected"],
            player,
            data["winner"],
        )

    @staticmethod
    def handlemsg():
        return True


class Chess:
    def __init__(self, players, guild_id, board=None, move=None):
        self.guild_id = guild_id
        if board is None:
            self.chess = chess.Board()
            if randint(0, 1) == 0:
                self.players = [players[1], players[0]]
            else:
                self.players = players
        else:
            self.chess = chess.Board(board)
            self.players = players
        self.winner = None
        self.playermap = {chess.WHITE: 0, chess.BLACK: 1}
        self.turn = self.playermap[self.chess.turn]
        self.move = move
        self.emojis = [
            [":white_circle:", ":black_circle:"],
            [
                {
                    chess.WHITE: {
                        chess.KING: "<:wKr:878232501921927188>",
                        chess.QUEEN: "<:wQr:878232501976449085>",
                        chess.BISHOP: "<:wBr:878232501926121503>",
                        chess.KNIGHT: "<:wNr:878232501728968785>",
                        chess.ROOK: "<:wRr:878232501905154108>",
                        chess.PAWN: "<:wPr:878232501603172423>",
                        None: "<:r_:878210060705218601>",
                    },
                    chess.BLACK: {
                        chess.KING: "<:bKr:878232504543359016>",
                        chess.QUEEN: "<:bQr:878232501531869246>",
                        chess.BISHOP: "<:bBr:878232501640917032>",
                        chess.KNIGHT: "<:bNr:878232501909352478>",
                        chess.ROOK: "<:bRr:878232501540257813>",
                        chess.PAWN: "<:bPr:878232501582200833>",
                        None: "<:r_:878210060705218601>",
                    },
                },
                {
                    chess.WHITE: {
                        chess.KING: "<:wKb:878236200480170044>",
                        chess.QUEEN: "<:wQb:878236200362709043>",
                        chess.BISHOP: "<:wBb:878236735060975626>",
                        chess.KNIGHT: "<:wNb:878236200274628658>",
                        chess.ROOK: "<:wRb:878236200417230858>",
                        chess.PAWN: "<:wPb:878236200450801714>",
                        None: "<:bl:878210060843630602>",
                    },
                    chess.BLACK: {
                        chess.KING: "<:bKb:878236200228503552>",
                        chess.QUEEN: "<:bQb:878236200249458708>",
                        chess.BISHOP: "<:bBb:878236200304005121>",
                        chess.KNIGHT: "<:bNb:878236200173989958>",
                        chess.ROOK: "<:bRb:878236200136216576>",
                        chess.PAWN: "<:bPb:878236200165580910>",
                        None: "<:bl:878210060843630602>",
                    },
                },
            ],
            [
                "<:1_:878210060814262293>",
                "<:2_:878210061007204352>",
                "<:3_:878210060977840128>",
                "<:4_:878210061019791406>",
                "<:5_:878210060558401547>",
                "<:6_:878210060818464779>",
                "<:7_:878210060826869760>",
                "<:8_:878210060856229938>",
            ],
        ]
        self.names = ["", "Pawn", "Knight", "Bishop", "Rook", "Queen", "King"]

    def get_moves(self):
        moves = [[[], []], [[], []]]
        for move in self.chess.legal_moves:
            movestr = move.uci()
            if movestr[:2] not in moves[0][0]:
                moves[0][0].append(movestr[:2])
                moves[1][0].append(
                    self.names[
                        int(f"{self.chess.piece_at(move.from_square).piece_type}")
                    ]
                )
            if self.move is not None:
                if self.move == movestr[:2] and movestr[2:] not in moves[0][1]:
                    moves[0][1].append(movestr)
                    piece = self.chess.piece_at(move.to_square)
                    if piece is not None:
                        moves[1][1].append(
                            f"capture {self.names[int(f'{piece.piece_type}')]}"
                        )
                    else:
                        moves[1][1].append("move")
        return moves

    def make_move(self, move):
        moves = self.get_moves()
        if move in moves[0][0]:
            self.move = move
        elif move in moves[0][1]:
            self.chess.push(chess.Move.from_uci(move))
            self.move = None
            self.checkwin()
            if self.winner is None:
                self.turn = (self.turn + 1) % 2
                return True
        return False

    def get_data(self):
        return {
            "players": self.players,
            "board": self.chess.fen(),
            "type": "Chess",
            "guild_id": self.guild_id,
            "move": self.move,
        }

    def build_components(self):
        components = []
        moves = self.get_moves()
        row = bot.rest.build_action_row()
        s = row.add_select_menu("select|-2")
        # s.add_option("select piece to move", "ignore").set_is_default(True).add_to_menu()
        for (i, move) in enumerate(moves[0][0]):
            default = False
            if move == self.move:
                default = True
            s.add_option(f"{move}".upper(), move).set_description(
                moves[1][0][i]
            ).set_is_default(default).add_to_menu()
        s.add_to_container()
        components.append(row)
        row = bot.rest.build_action_row()
        s = row.add_select_menu("select|-1")
        s.add_option("select move to make", "ignore").set_is_default(True).add_to_menu()
        if self.move is None:
            s.set_is_disabled(True)
        else:
            for (i, move) in enumerate(moves[0][1]):
                if (i % 20) == 0:
                    if i != 0:
                        s.add_to_container()
                        components.append(row)
                        row = bot.rest.build_action_row()
                        s = row.add_select_menu(f"select|{i}")
                        s.add_option("select move to make", "ignore").set_is_default(
                            True
                        ).add_to_menu()
                s.add_option(f"{move}".upper(), move).set_description(
                    moves[1][1][i]
                ).add_to_menu()
        s.add_to_container()
        components.append(row)
        return components

    def build_board(self):
        board = "<:quiggle:897058047137030184><:a_:878071110481117205><:b_:878071110544003114><:c_:878071110862766120><:d_:878071110455939104><:e_:878071110749532171><:f_:878071110510465106><:g_:878071110996987935><:h_:878071110892146728>"
        for rank in range(8):
            board += f"\n{self.emojis[2][rank]}"
            for file in range(8):
                piece = self.chess.piece_at(chess.square(file, rank))
                if piece is None:
                    board += self.emojis[1][(file + rank) % 2][chess.WHITE][None]
                else:
                    board += self.emojis[1][(file + rank) % 2][piece.color][
                        piece.piece_type
                    ]
        return board

    def build_message(self):
        bn = ""
        if dev:
            bn = "\n"
        check = ""
        if self.chess.is_check():
            check = " Check!"
        embed = hikari.Embed(
            title=f"{self.emojis[0][self.playermap[self.chess.turn]]}{check}",
            description=self.build_board(),
        )
        if self.winner is None:
            return {
                "text": f"```{bn}{encode(self.get_data())}\n[{readable['Chess']}]```<@{self.players[self.playermap[self.chess.turn]]}>",
                "embed": embed,
                "components": self.build_components(),
            }
        else:
            embed.title = (
                f"{self.emojis[0][self.playermap[self.chess.turn]]} is the WINNER!"
            )
            return {
                "text": f"```{bn}{encode(self.get_data())}\n[{readable['Chess']}]```<@{self.players[self.playermap[self.chess.turn]]}>",
                "embed": embed,
                # "components": self.build_components(),
            }

    def checkwin(self):
        if self.chess.is_checkmate():
            self.winner = self.playermap[self.chess.turn]

    @staticmethod
    def load_data(data):
        return Chess(data["players"], data["guild_id"], data["board"], data["move"])


class Invite:
    def __init__(self, players, game, guild_id):
        self.players = players
        self.game = game
        self.guild_id = guild_id

    def build_components(self):
        components = bot.rest.build_action_row()
        button = components.add_button(hikari.ButtonStyle.SUCCESS, "yes")
        button.set_label("Yes")
        button.add_to_container()
        button = components.add_button(hikari.ButtonStyle.DANGER, "no")
        button.set_label("No")
        button.add_to_container()
        return [components]

    def build_message(self):
        return {
            "text": f"<@{self.players[1]}> you have been challenged to a game of\n```{encode(self.get_data())}\n[{readable[self.game]}]```by <@{self.players[0]}>, do you accept?",
            "components": self.build_components(),
        }

    def get_data(self):
        return {
            "type": "Invite",
            "players": self.players,
            "game": self.game,
            "guild_id": self.guild_id,
        }


def encode(data: dict):
    return zcompress(bytes(jdumps(data), "utf-8")).hex()


def decode(string: str):
    return jloads(zdecompress(cdecode(string, "hex")).decode("utf-8"))


bot = lightbulb.BotApp(
    token=token,
    prefix=None,
    default_enabled_guilds=default_guilds,
)


def getClass(name):
    return globals()[name]


@bot.command
@lightbulb.option(
    "user", "User you would like to invite!", required=True, type=hikari.OptionType.USER
)
@lightbulb.command("tictactoe", f"Invite a user to play {readable['TicTacToe']}!")
@lightbulb.implements(lightbulb.SlashCommand)
async def TicTacToeCommand(ctx: lightbulb.SlashContext) -> None:
    if ctx.author.is_bot:
        await ctx.respond("Sorry, you're a bot", flags=hikari.MessageFlag.EPHEMERAL)
        return
    if ctx.options.user.is_bot:
        await ctx.respond(
            "You can't play against a bot", flags=hikari.MessageFlag.EPHEMERAL
        )
        return
    if not dev:
        if ctx.author.id == ctx.options.user.id:
            await ctx.respond(
                "You can't play against yourself", flags=hikari.MessageFlag.EPHEMERAL
            )
            return
    message = Invite(
        [ctx.author.id, ctx.options.user.id], "TicTacToe", ctx.guild_id
    ).build_message()

    await ctx.respond(
        message["text"],
        components=message["components"],
        user_mentions=True,
        nonce=str(ctx.guild_id),
    )


@bot.command
@lightbulb.option(
    "user", "User you would like to invite!", required=True, type=hikari.OptionType.USER
)
@lightbulb.command("ulttictactoe", f"Invite a user to play {readable['UltTicTacToe']}!")
@lightbulb.implements(lightbulb.SlashCommand)
async def UltTicTacToeCommand(ctx: lightbulb.SlashContext) -> None:
    if ctx.author.is_bot:
        await ctx.respond("Sorry, you're a bot", flags=hikari.MessageFlag.EPHEMERAL)
        return
    if ctx.options.user.is_bot:
        await ctx.respond(
            "You can't play against a bot", flags=hikari.MessageFlag.EPHEMERAL
        )
        return
    if not dev:
        if ctx.author.id == ctx.options.user.id:
            await ctx.respond(
                "You can't play against yourself", flags=hikari.MessageFlag.EPHEMERAL
            )
            return
    message = Invite(
        [ctx.author.id, ctx.options.user.id], "UltTicTacToe", ctx.guild_id
    ).build_message()

    await ctx.respond(
        message["text"],
        components=message["components"],
        user_mentions=True,
        nonce=str(ctx.guild_id),
    )


@bot.command
@lightbulb.option(
    "user", "User you would like to invite!", required=True, type=hikari.OptionType.USER
)
@lightbulb.command("connectfour", f"Invite a user to play {readable['ConnectFour']}!")
@lightbulb.implements(lightbulb.SlashCommand)
async def ConnectFourCommand(ctx: lightbulb.SlashContext) -> None:
    if ctx.author.is_bot:
        await ctx.respond("Sorry, you're a bot", flags=hikari.MessageFlag.EPHEMERAL)
        return
    if ctx.options.user.is_bot:
        await ctx.respond(
            "You can't play against a bot", flags=hikari.MessageFlag.EPHEMERAL
        )
        return
    if not dev:
        if ctx.author.id == ctx.options.user.id:
            await ctx.respond(
                "You can't play against yourself", flags=hikari.MessageFlag.EPHEMERAL
            )
            return
    message = Invite(
        [ctx.author.id, ctx.options.user.id], "ConnectFour", ctx.guild_id
    ).build_message()

    await ctx.respond(
        message["text"],
        components=message["components"],
        user_mentions=True,
        nonce=str(ctx.guild_id),
    )


@bot.command
@lightbulb.option(
    "user", "User you would like to invite!", required=True, type=hikari.OptionType.USER
)
@lightbulb.command("battleship", f"Invite a user to play {readable['Battleship']}!")
@lightbulb.implements(lightbulb.SlashCommand)
async def BattleshipCommand(ctx: lightbulb.SlashContext) -> None:
    if ctx.author.is_bot:
        await ctx.respond("Sorry, you're a bot", flags=hikari.MessageFlag.EPHEMERAL)
        return
    if ctx.options.user.is_bot:
        await ctx.respond(
            "You can't play against a bot", flags=hikari.MessageFlag.EPHEMERAL
        )
        return
    if not dev:
        if ctx.author.id == ctx.options.user.id:
            await ctx.respond(
                "You can't play against yourself", flags=hikari.MessageFlag.EPHEMERAL
            )
            return
    message = Invite(
        [ctx.author.id, ctx.options.user.id], "Battleship", ctx.guild_id
    ).build_message()

    await ctx.respond(
        message["text"],
        components=message["components"],
        user_mentions=True,
        nonce=str(ctx.guild_id),
    )


@bot.command
@lightbulb.option(
    "user", "User you would like to invite!", required=True, type=hikari.OptionType.USER
)
@lightbulb.command("chess", f"Invite a user to play {readable['Chess']}!")
@lightbulb.implements(lightbulb.SlashCommand)
async def ChessCommand(ctx: lightbulb.SlashContext) -> None:
    if ctx.author.is_bot:
        await ctx.respond("Sorry, you're a bot", flags=hikari.MessageFlag.EPHEMERAL)
        return
    if ctx.options.user.is_bot:
        await ctx.respond(
            "You can't play against a bot", flags=hikari.MessageFlag.EPHEMERAL
        )
        return
    if not dev:
        if ctx.author.id == ctx.options.user.id:
            await ctx.respond(
                "You can't play against yourself", flags=hikari.MessageFlag.EPHEMERAL
            )
            return
    message = Invite(
        [ctx.author.id, ctx.options.user.id], "Chess", ctx.guild_id
    ).build_message()

    await ctx.respond(
        message["text"],
        components=message["components"],
        user_mentions=True,
        nonce=str(ctx.guild_id),
    )


if dev:

    @bot.command
    @lightbulb.option("gamedatastring", "data string to load game for", required=True)
    @lightbulb.command("loadgame", f"load a game from a string")
    @lightbulb.implements(lightbulb.SlashCommand)
    async def LoadMessageCommand(ctx: lightbulb.SlashContext) -> None:
        if dev:
            try:
                data = decode(ctx.options.gamedatastring.strip())
                gameclass = getClass(data["type"])
                game = gameclass.load_data(data)
                message = game.build_message()
                await ctx.respond(
                    message["text"],
                    components=message.get("components", []),
                )
            except Exception as e:
                await ctx.respond(e, flags=hikari.MessageFlag.EPHEMERAL)
        else:
            await ctx.respond(
                "bot not in development mode lololol",
                flags=hikari.MessageFlag.EPHEMERAL,
            )


@bot.listen(hikari.InteractionCreateEvent)
async def on_component_interaction(event: hikari.InteractionCreateEvent) -> None:
    if not isinstance(event.interaction, hikari.ComponentInteraction):
        return

    data = decode(
        event.interaction.message.content.split("```")[1].split("[")[0].strip()
    )
    if event.interaction.user.id in data["players"]:
        ping = False
        if data.get("type") == "Invite":
            if event.interaction.user.id == data["players"][1]:
                if event.interaction.custom_id == "yes":
                    gameclass = getClass(data["game"])
                    if not hasattr(gameclass, "handlemsg"):
                        ping = True
                    game = gameclass(data["players"], data["guild_id"])
                else:
                    await event.interaction.message.delete()
                    return
            else:
                await event.interaction.create_initial_response(
                    hikari.ResponseType.MESSAGE_CREATE,
                    "You're the inviter, silly!",
                    flags=hikari.MessageFlag.EPHEMERAL,
                )
                return
        else:
            gameclass = getClass(data["type"])
            if hasattr(gameclass, "handlemsg"):
                game = gameclass.load_data(data, event.interaction.user.id)
                ping = game.make_move(event.interaction.custom_id)
            else:
                game = gameclass.load_data(data)
                if event.interaction.user.id == game.players[game.turn]:
                    if "select" in event.interaction.custom_id:
                        ping = game.make_move(event.interaction.values[0])
                    else:
                        ping = game.make_move(event.interaction.custom_id)
                else:
                    await event.interaction.create_initial_response(
                        hikari.ResponseType.MESSAGE_CREATE,
                        "It isnt your turn!",
                        flags=hikari.MessageFlag.EPHEMERAL,
                    )
                    return
        message = game.build_message()
        if dev:
            print(len(message["text"]))
        await event.interaction.create_initial_response(
            message.get("responsetype", hikari.ResponseType.MESSAGE_UPDATE),
            message["text"],
            embed=message.get("embed", hikari.UNDEFINED),
            embeds=message.get("embeds", hikari.UNDEFINED),
            flags=message.get("flags", hikari.MessageFlag.EPHEMERAL),
            components=message.get("components", []),
        )
        if ping:
            if get_options(game.players[game.turn], "dm_notifications"):
                components = bot.rest.build_action_row()
                l = components.add_button(
                    hikari.ButtonStyle.LINK,
                    event.interaction.message.make_link(int(data["guild_id"])),
                )
                l.set_label("Jump to game!")
                l.add_to_container()
                # await bot.rest.get_guild(int(data["guild_id"])).get_member(int(game.players[game.turn])).user.fetch_dm_channel().send(
                await (await bot.rest.fetch_user(int(game.players[game.turn]))).send(
                    f"It's your turn in {(await bot.rest.fetch_guild(int(data['guild_id']))).name}!\n`psst, dont like the dms? turn off dms with /dmsettings`",
                    components=[components],
                )
            # await sleep(0.5)
            # ping = await event.interaction.get_channel().send(f"<@{game.players[game.turn]}>", user_mentions=True)
            # await sleep(0.5)
            # await ping.delete()
            pass
    else:
        await event.interaction.create_initial_response(
            hikari.ResponseType.MESSAGE_CREATE,
            "You are not in this game!",
            flags=hikari.MessageFlag.EPHEMERAL,
        )


choices = []
for i in setting_defaults.keys():
    choices.append(i)


@bot.command
@lightbulb.option(
    "value", "value to set this setting to", type=hikari.OptionType.BOOLEAN
)
@lightbulb.option("type", "setting to change", choices=choices)
@lightbulb.command("boolsettings", "change boolean (true or false) quiggle settings")
@lightbulb.implements(lightbulb.SlashCommand)
async def setsetting(ctx: lightbulb.SlashContext):
    set_options(ctx.author.id, ctx.options.type, ctx.options.value)
    await ctx.respond(
        f"Setting updated!\n`{ctx.options.type}: {ctx.options.value}`",
        flags=hikari.MessageFlag.EPHEMERAL,
    )


@bot.command
@lightbulb.command("invite", "recieve a link to invite the bot to your server!")
@lightbulb.implements(lightbulb.SlashCommand)
async def invitecommand(ctx: lightbulb.SlashContext) -> None:
    components = []
    r = bot.rest.build_action_row()
    r.add_button(
        hikari.ButtonStyle.LINK,
        rf"{config['invite_link']}",
    ).set_label("Invite me!").add_to_container()
    components.append(r)
    await ctx.author.send(components=components)
    await ctx.respond("sent!", flags=hikari.MessageFlag.EPHEMERAL)


@bot.listen(hikari.events.ExceptionEvent)
async def on_exception(event: hikari.ExceptionEvent):

    set_options(time(), "LOG", f'"{event.exception}"')


bot.run()
