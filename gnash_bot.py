import random
import os
from reconchess import *
from reconchess.utilities import capture_square_of_move
from game.BeliefState import BeliefState
from strategy.select_sense import select_sense
from strategy.select_move import select_move
from helper_bot import HelperBot
import chess.engine
import types
import time

##TODO: Handle en passant
class GnashBot(Player):

    def __init__(self, maxMoveTime=15):
        self.color = None
        self.board = None
        self.beliefState = None
        self.firstTurn = True
        self.moveStartTime = None
        self.maxMoveTime = maxMoveTime
        self.helperBot = HelperBot()
        self.useHelperBot = False

    def handle_game_start(self, color: Color, board: chess.Board, opponent_name: str):
        self.color = color
        self.board = board
        self.opponent_name = opponent_name
        print('Game has started.')
        # print('\nUpdating our belief states...')
        self.beliefState = BeliefState(color, board.fen())
        # print('Our original belief state is as follows:')
        # self.beliefState.display()

    def handle_opponent_move_result(self, captured_my_piece: bool, capture_square: Optional[Square]):
        if self.useHelperBot:
            self.helperBot.handle_opponent_move_result(captured_my_piece, capture_square)
            return
        self.moveStartTime = time.time()
        if self.firstTurn and self.color:
            self.firstTurn = False
            return
        # print('Our updated belief state is now as follows:')
        # self.beliefState.display()
        # print()
        print('\nOpponent moved.')
        # print("Captured my piece:", captured_my_piece)
        if captured_my_piece:
            print('Piece captured!', capture_square)
        else:
            print('No pieces captured.')
        # print('Updating belief state...')
        self.beliefState.opp_move_result_update(captured_my_piece, capture_square, maxTime=self.maxMoveTime*(.4))
        # print('Our updated belief state is now as follows:')
        # self.beliefState.display()
        pass

    def choose_sense(self, sense_actions: List[Square], move_actions: List[chess.Move], seconds_left: float) -> \
            Optional[Square]:
        if self.useHelperBot:
            return self.helperBot.choose_sense(sense_actions, move_actions, seconds_left)
        print('\nSensing now...')
        sense_move = select_sense(self.beliefState.myBoardDist)
        print('\nSensing move is', sense_move)
        return sense_move

    def handle_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]]):
        if self.useHelperBot:
            self.helperBot.handle_sense_result(sense_result)
            return
        print('\nSense result is', sense_result)
        print('Updating belief state...')
        self.beliefState.sense_update(sense_result)
        print('Our updated belief dist is now as follows:')
        self.beliefState.display()
        bestKey = max(self.beliefState.myBoardDist, key=self.beliefState.myBoardDist.get)
        print(bestKey, self.beliefState.myBoardDist[bestKey])

    def choose_move(self, move_actions: List[chess.Move], seconds_left: float) -> Optional[chess.Move]:
        if (len(self.beliefState.myBoardDist) > 5000 or seconds_left<60) and not self.useHelperBot:
            print("Helper bot taking over to speed things up...")
            self.useHelperBot = True
            mostLikelyBoard = max(self.beliefState.myBoardDist, key=self.beliefState.myBoardDist.get)
            self.helperBot.handle_game_start(self.color, chess.Board(mostLikelyBoard), self.opponent_name)
        if self.useHelperBot:
            return self.helperBot.choose_move(move_actions, seconds_left)
        print("Choosing move...")
        move = select_move(self.beliefState, maxTime=self.maxMoveTime*(.6))
        print("MOVE:", move)
        if move == chess.Move.null():
            return None
        return move

    def handle_move_result(self, requested_move: Optional[chess.Move], taken_move: Optional[chess.Move],
                           captured_opponent_piece: bool, capture_square: Optional[Square]):
        if self.useHelperBot:
            self.helperBot.handle_move_result(requested_move, taken_move, captured_opponent_piece, capture_square)
            return
        print('\nRequested move', requested_move, ', took move', taken_move)
        print('\nTime elapsed', time.time() - self.moveStartTime)
        # print('Updating belief state...')
        self.beliefState.our_move_result_update(requested_move, taken_move, captured_opponent_piece, capture_square)
        # print('Our updated belief state is now as follows:')
        # self.beliefState.display()
        print('\nOpponent sensed.')
        # print('Updating belief state...')
        self.beliefState.opp_sense_result_update()

    def handle_game_end(self, winner_color: Optional[Color], win_reason: Optional[WinReason],
                        game_history: GameHistory):
        game_history.save('games/game.json')
        print(f"{winner_color} won by {win_reason}!")