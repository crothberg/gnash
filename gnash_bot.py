import random
import os
from reconchess import *
from reconchess.utilities import capture_square_of_move
from game.BeliefState import BeliefState
from strategy.select_sense import select_sense
from strategy.select_move import select_move
from helper_bot import HelperBot
import chess.engine
from collections import defaultdict
from utils.util import *
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
        self.turn = 0
        #opponent_move_result, sense_result, move_result
        #for every turn
        self.history = defaultdict(list)

    def handle_game_start(self, color: Color, board: chess.Board, opponent_name: str):
        self.color = color
        self.board = board
        self.opponent_name = opponent_name
        print('Game has started.')
        self.beliefState = BeliefState(color, board.fen())

    def handle_opponent_move_result(self, captured_my_piece: bool, capture_square: Optional[Square]):
        self.history[self.turn].append((captured_my_piece, capture_square))
        t0 = time.time()
        if self.useHelperBot:
            self.helperBot.handle_opponent_move_result(captured_my_piece, capture_square)
            return
        self.moveStartTime = time.time()
        if self.firstTurn and self.color:
            self.firstTurn = False
            return
        print('\nOpponent moved, handling result...')
        try:
            self.beliefState.opp_move_result_update(captured_my_piece, capture_square, maxTime=3)
        except ValueError:
            self._expand_stashed_boards(phase="handle_opponent_move_result")
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
        self.history[self.turn].append(sense_result)
        t0 = time.time()
        if self.useHelperBot:
            self.helperBot.handle_sense_result(sense_result)
            return
        # print('\nSense result is', sense_result)
        print('Updating belief state after sense result...')
        try:
            self.beliefState.sense_update(sense_result)
        except ValueError:
            self._expand_stashed_boards(phase="handle_sense_result")
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
        self.history[self.turn].append((requested_move, taken_move, captured_opponent_piece, capture_square))
        t0 = time.time()
        if self.useHelperBot:
            self.helperBot.handle_move_result(requested_move, taken_move, captured_opponent_piece, capture_square)
            return
        print('\nRequested move', requested_move, ', took move', taken_move)
        print('Updating belief state...')
        try:
            self.beliefState.our_move_result_update(requested_move, taken_move, captured_opponent_piece, capture_square, maxTime=2)
        except ValueError:
            self._expand_stashed_boards(phase="handle_move-result")
        print(f"Handled our move result in {time.time()-t0} seconds.")
        t1 = time.time()
        print('\nAnticipating opponent sense...')
        try:
            self.beliefState.opp_sense_result_update()
        except ValueError:
            self._expand_stashed_boards(phase="handle_move_result")
        print(f"Handled anticipated opponent sensing action in {time.time()-t1} seconds.")
        self.turn += 1
        self._stash_boards()

    def handle_game_end(self, winner_color: Optional[Color], win_reason: Optional[WinReason],
                        game_history: GameHistory):
        game_history.save('games/game.json')
        print(f"{winner_color} won by {win_reason}!")

    def _stash_boards(self):
        # self.beliefState.display()
        print(f"{len(self.beliefState.myBoardDist.keys())} boards, stashing boards...")
        # input()
        newMyBoardDist = dict()
        newOppBoardDists = dict()
        for fen, prob in self.beliefState.myBoardDist.items():
            if prob < .05:
            # if random.randint(1,3)%2==1 and len(newMyBoardDist.keys())>0:
                self.beliefState.stashedBoards[self.turn].add(fen)
            else:
                newMyBoardDist[fen] = self.beliefState.myBoardDist[fen]
                newOppBoardDists[fen] = self.beliefState.oppBoardDists[fen]
        self.beliefState.myBoardDist = normalize(newMyBoardDist)
        self.beliefState.oppBoardDists = newOppBoardDists
        # self.beliefState.display()
        print(f"Now there are {len(self.beliefState.myBoardDist.keys())} boards")
        # input()
        # print("And this is the new stash:")
        # print(self.beliefState.stashedBoards)
        # input()
    
    #If myBoardDist is empty, restock with possible boards
    def _expand_stashed_boards(self, phase):
        assert len(self.beliefState.myBoardDist.keys()) == 0, "stashed boards cannot be expanded when there are still boards in the distribution"
        # print(self.beliefState.stashedBoards)
        print(f"Ran out of boards, taking from stash in phase: {phase}...")
        # input()
        turn = self.turn
        while turn not in self.beliefState.stashedBoards and turn > 0:
            turn-=1
        stashedBoards = self.beliefState.stashedBoards[turn]
        self.beliefState.myBoardDist = {fen: 1/len(stashedBoards) for fen in stashedBoards}
        del self.beliefState.stashedBoards[turn]
        self.beliefState.oppBoardDists = {fen: {fen: 1.0} for fen in self.beliefState.myBoardDist}
        # print(f"Starting on turn {turn}")
        # print("History is:")
        # print(self.history)
        # input()
        while turn <= self.turn:
            # oppMoveResult, senseResult, moveResult = self.history[turn]
            self.handle_opponent_move_result(*self.history[turn][0])
            # print("handled opponent move result,")
            if phase == "handle_opponent_move_result" and turn == self.turn:
                break
            self.handle_sense_result(self.history[turn][1])
            # print("handled sense result,")
            if phase == "handle_sense_result" and turn == self.turn:
                break
            moveResult = self.history[turn][2]
            if len(moveResult) < 4:
                print(self.history)
                print(phase)
                input()
            self.handle_move_result(*moveResult)
            # print("and handled move result.")
            turn += 1
        if len(self.beliefState.myBoardDist) == 0:
            self._expand_stashed_boards()
        # self.beliefState.display()
        print(f"Restored {len(self.beliefState.myBoardDist.keys())} boards")
        # input()
        