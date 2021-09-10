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

    def __init__(self):
        self.color = None
        self.board = None
        self.beliefState = None
        self.firstTurn = True
        self.moveStartTime = None
        self.helperBot = HelperBot()
        self.useHelperBot = False

    def handle_game_start(self, color: Color, board: chess.Board, opponent_name: str):
        self.color = color
        self.board = board
        self.opponent_name = opponent_name
        print('Game has started.')
        self.beliefState = BeliefState(color, board.fen())

    def handle_opponent_move_result(self, captured_my_piece: bool, capture_square: Optional[Square]):
        t0 = time.time()
        if self.useHelperBot:
            self.helperBot.handle_opponent_move_result(captured_my_piece, capture_square)
            return
        self.moveStartTime = time.time()
        if self.firstTurn and self.color:
            self.firstTurn = False
            return
        print('\nOpponent moved, handling result...')
        self.beliefState.opp_move_result_update(captured_my_piece, capture_square, maxTime=3)
        print(f"Handled opponent move result in {time.time()-t0} seconds.")

    def choose_sense(self, sense_actions: List[Square], move_actions: List[chess.Move], seconds_left: float) -> \
            Optional[Square]:
        t0 = time.time()
        if self.useHelperBot:
            return self.helperBot.choose_sense(sense_actions, move_actions, seconds_left)
        print('\nSensing now...')
        sense_move = select_sense(self.beliefState.myBoardDist)
        print('\nSensing move is', sense_move)
        print(f"Chose a sensing action in {time.time()-t0} seconds.")
        return sense_move

    def handle_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]]):
        t0 = time.time()
        if self.useHelperBot:
            self.helperBot.handle_sense_result(sense_result)
            return
        # print('\nSense result is', sense_result)
        print('Updating belief state after sense result...')
        self.beliefState.sense_update(sense_result)
        print('Our updated belief dist is now as follows:')
        self.beliefState.display()
        bestKey = max(self.beliefState.myBoardDist, key=self.beliefState.myBoardDist.get)
        print(bestKey, self.beliefState.myBoardDist[bestKey])
        print(f"Handled sense result in {time.time()-t0} seconds.")

    def choose_move(self, move_actions: List[chess.Move], seconds_left: float) -> Optional[chess.Move]:
        t0 = time.time()
        if (len(self.beliefState.myBoardDist) > 5000 or seconds_left<180) and not self.useHelperBot:
            print("Helper bot taking over to speed things up...")
            self.useHelperBot = True
            mostLikelyBoard = max(self.beliefState.myBoardDist, key=self.beliefState.myBoardDist.get)
            self.helperBot.handle_game_start(self.color, chess.Board(mostLikelyBoard), self.opponent_name)
        if self.useHelperBot:
            return self.helperBot.choose_move(move_actions, seconds_left)
        print("Choosing move...")
        move = select_move(self.beliefState, maxTime=4)
        print("MOVE:", move)
        if move == chess.Move.null():
            return None
        print(f"Chose a move in {time.time()-t0} seconds.")
        return move

    def handle_move_result(self, requested_move: Optional[chess.Move], taken_move: Optional[chess.Move],
                           captured_opponent_piece: bool, capture_square: Optional[Square]):
        t0 = time.time()
        if self.useHelperBot:
            self.helperBot.handle_move_result(requested_move, taken_move, captured_opponent_piece, capture_square)
            return
        print('\nRequested move', requested_move, ', took move', taken_move)
        print('Updating belief state...')
        self.beliefState.our_move_result_update(requested_move, taken_move, captured_opponent_piece, capture_square, maxTime=3)
        print(f"Handled our move result in {time.time()-t0} seconds.")
        t1 = time.time()
        print('\nAnticipating opponent sense...')
        self.beliefState.opp_sense_result_update()
        print(f"Handled anticipated opponent sensing action in {time.time()-t1} seconds.")

    def handle_game_end(self, winner_color: Optional[Color], win_reason: Optional[WinReason],
                        game_history: GameHistory):
        game_history.save('games/game.json')
        print(f"{winner_color} won by {win_reason}!")