from reconchess.bots.trout_bot import TroutBot
import chess
from reconchess import *
import random

#A fast bot for just in case
##TODO: Improve this bot (maybe a better version of trout?)
class HelperBot():
    def __init__(self):
        self.bot = TroutBot()

    def handle_game_start(self, color: Color, board: chess.Board, opponent_name: str):
        self.color = color
        self.opponent_name = opponent_name
        self.bot.handle_game_start(color, board, opponent_name)

    def handle_opponent_move_result(self, captured_my_piece: bool, capture_square: Optional[Square]):
        self.bot.handle_opponent_move_result(captured_my_piece, capture_square)

    def choose_sense(self, sense_actions: List[Square], move_actions: List[chess.Move], seconds_left: float) -> \
            Optional[Square]:
        return self.bot.choose_sense(sense_actions, move_actions, seconds_left)

    def handle_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]]):
        self.bot.handle_sense_result(sense_result)

    def choose_move(self, move_actions: List[chess.Move], seconds_left: float) -> Optional[chess.Move]:
        #Restart occasionally in case the engine dies
        if random.randint(1,3) == 1:
            board = self.bot.board
            self.bot = TroutBot()
            self.bot.handle_game_start(self.color, board, self.opponent_name)
        return self.bot.choose_move(move_actions, seconds_left)

    def handle_move_result(self, requested_move: Optional[chess.Move], taken_move: Optional[chess.Move],
                           captured_opponent_piece: bool, capture_square: Optional[Square]):
        self.bot.handle_move_result(requested_move, taken_move, captured_opponent_piece, capture_square)