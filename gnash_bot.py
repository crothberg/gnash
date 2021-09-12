import random
import os
from chess import D2, D3
from reconchess import *
from reconchess.utilities import capture_square_of_move
from game.BeliefState import BeliefState
from strategy.select_sense import select_sense
from strategy.select_move import get_move_dist, select_move
from helper_bot import HelperBot
import chess.engine
from collections import defaultdict
from utils.util import *
import types
import time

##TODO: Handle en passant
##TODO: Handle promotion/captures?
class GnashBot(Player):

    def __init__(self):
        self.color = None
        self.board = None
        self.beliefState = None
        self.firstTurn = True
        self.moveStartTime = None
        self.helperBot = HelperBot()
        self.useHelperBot = False
        self.useHelperBotTime = 250
        self.turn = 0
        self.whiteStartingMoves = [chess.Move(chess.D2, chess.D3), chess.Move(chess.C1, chess.D2), chess.Move(chess.G1, chess.F3), chess.Move.null()] #chess.Move(chess.C2, chess.C4), chess.Move(chess.B1, chess.C3)]
        self.blackStartingMoves = [chess.Move(chess.D7, chess.D6), chess.Move(chess.C8, chess.D7), chess.Move(chess.G8, chess.F6)] #chess.Move(chess.C7, chess.C5), chess.Move(chess.B8, chess.C6)]
        self.playFromStartingMoves = True
        #opponent_move_result, sense_result, move_result
        #for every turn
        self.history = defaultdict(list)

    def handle_game_start(self, color: Color, board: chess.Board, opponent_name: str):
        self.color = color
        self.board = board
        self.opponent_name = opponent_name
        print('Game has started.')
        self.beliefState = BeliefState(color, board.fen())
        self.gameEndTime = time.time() + 900
        self.playFromStartingMoves = True

    def handle_opponent_move_result(self, captured_my_piece: bool, capture_square: Optional[Square], original=True):
        if (not self.useHelperBot) and self.gameEndTime - time.time() < self.useHelperBotTime:
            print("Helper bot taking over to speed things up...")
            self.useHelperBot = True
            mostLikelyBoard = max(self.beliefState.myBoardDist, key=self.beliefState.myBoardDist.get)
            self.helperBot.handle_game_start(self.color, chess.Board(mostLikelyBoard), self.opponent_name)
        if original:
            self.history[self.turn].append((captured_my_piece, capture_square, False))
        if captured_my_piece:
            self.playFromStartingMoves = False
        t0 = time.time()
        if self.useHelperBot:
            self.helperBot.handle_opponent_move_result(captured_my_piece, capture_square)
            return
        self.moveStartTime = time.time()
        if self.firstTurn and self.color:
            self.firstTurn = False
            return
        if original: print('\nOpponent moved, handling result...')
        try:
            self.beliefState.opp_move_result_update(captured_my_piece, capture_square, maxTime=3 if original else 1)
        except ValueError:
            self._expand_stashed_boards(phase="handle_opponent_move_result")
        if original: print(f"Handled opponent move result in {time.time()-t0} seconds.")

    def choose_sense(self, sense_actions: List[Square], move_actions: List[chess.Move], seconds_left: float) -> \
            Optional[Square]:
        self.gameEndTime = time.time() + seconds_left
        if (not self.useHelperBot) and self.gameEndTime - time.time() < self.useHelperBotTime:
            print("Helper bot taking over to speed things up...")
            self.useHelperBot = True
            mostLikelyBoard = max(self.beliefState.myBoardDist, key=self.beliefState.myBoardDist.get)
            self.helperBot.handle_game_start(self.color, chess.Board(mostLikelyBoard), self.opponent_name)
        t0 = time.time()
        if self.useHelperBot:
            return self.helperBot.choose_sense(sense_actions, move_actions, seconds_left)
        print('\nSensing now...')
        sense_move = select_sense(self.beliefState.myBoardDist)
        print('\nSensing move is', sense_move)
        print(f"Chose a sensing action in {time.time()-t0} seconds.")
        return sense_move

    def handle_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]], original=True):
        if (not self.useHelperBot) and self.gameEndTime - time.time() < self.useHelperBotTime:
            print("Helper bot taking over to speed things up...")
            self.useHelperBot = True
            mostLikelyBoard = max(self.beliefState.myBoardDist, key=self.beliefState.myBoardDist.get)
            self.helperBot.handle_game_start(self.color, chess.Board(mostLikelyBoard), self.opponent_name)
        if original:
            self.history[self.turn].append((sense_result, False))
        t0 = time.time()
        if self.useHelperBot:
            self.helperBot.handle_sense_result(sense_result)
            return
        # print('\nSense result is', sense_result)
        if original: print('Updating belief state after sense result...')
        try:
            self.beliefState.sense_update(sense_result)
        except ValueError:
            self._expand_stashed_boards(phase="handle_sense_result")
        if original: print('Our updated belief dist is now as follows:')
        if original: self.beliefState.display()
        bestKey = max(self.beliefState.myBoardDist, key=self.beliefState.myBoardDist.get)
        if original: print(bestKey, self.beliefState.myBoardDist[bestKey])
        if original: print(f"Handled sense result in {time.time()-t0} seconds.")

    def choose_move(self, move_actions: List[chess.Move], seconds_left: float) -> Optional[chess.Move]:
        self.gameEndTime = time.time() + seconds_left
        if (not self.useHelperBot) and self.gameEndTime - time.time() < self.useHelperBotTime:
            print("Helper bot taking over to speed things up...")
            self.useHelperBot = True
            mostLikelyBoard = max(self.beliefState.myBoardDist, key=self.beliefState.myBoardDist.get)
            self.helperBot.handle_game_start(self.color, chess.Board(mostLikelyBoard), self.opponent_name)
        t0 = time.time()
        if self.useHelperBot:
            return self.helperBot.choose_move(move_actions, seconds_left)
        print("Choosing move...")
        if self.playFromStartingMoves:
            if self.color:
                if len(self.whiteStartingMoves) > self.turn:
                    move = self.whiteStartingMoves[self.turn]
                else:
                    self.playFromStartingMoves = False
            else:
                if len(self.blackStartingMoves) > self.turn:
                    move = self.blackStartingMoves[self.turn]
                else:
                    self.playFromStartingMoves = False
        if not self.playFromStartingMoves:
            # move = select_move(self.beliefState, maxTime=6)
            moveDist = get_move_dist(self.beliefState.myBoardDist, maxTime=5)
            topMoves = sorted(moveDist, key=moveDist.get, reverse=True)[:5]
            print([(move, moveDist[move]) for move in topMoves])
            # move = sample(moveDist)
            move = topMoves[0]
            # while move not in topMoves:
            #     move = sample(moveDist)
            print(moveDist[move])
        print("MOVE:", move)
        if move == chess.Move.null():
            return None
        print(f"Chose a move in {time.time()-t0} seconds.")
        return move

    def handle_move_result(self, requested_move: Optional[chess.Move], taken_move: Optional[chess.Move],
                           captured_opponent_piece: bool, capture_square: Optional[Square], original=True):
        if (not self.useHelperBot) and self.gameEndTime - time.time() < self.useHelperBotTime:
            print("Helper bot taking over to speed things up...")
            self.useHelperBot = True
            mostLikelyBoard = max(self.beliefState.myBoardDist, key=self.beliefState.myBoardDist.get)
            self.helperBot.handle_game_start(self.color, chess.Board(mostLikelyBoard), self.opponent_name)
        if original:
            self.history[self.turn].append((requested_move, taken_move, captured_opponent_piece, capture_square, False))
        t0 = time.time()
        if self.useHelperBot:
            self.helperBot.handle_move_result(requested_move, taken_move, captured_opponent_piece, capture_square)
            return
        if captured_opponent_piece:
            self.playFromStartingMoves = False
        if original: print('\nRequested move', requested_move, ', took move', taken_move)
        if original: print('Updating belief state...')
        try:
            self.beliefState.our_move_result_update(requested_move, taken_move, captured_opponent_piece, capture_square, maxTime=2 if original else .7)
        except ValueError:
            self._expand_stashed_boards(phase="handle_move-result")
        if original: print(f"Handled our move result in {time.time()-t0} seconds.")
        t1 = time.time()
        if original: print('\nAnticipating opponent sense...')
        try:
            self.beliefState.opp_sense_result_update()
        except ValueError:
            self._expand_stashed_boards(phase="handle_move_result")
        if original: print(f"Handled anticipated opponent sensing action in {time.time()-t1} seconds.")
        # if original: print(self.history[self.turn])
        if original: self.turn += 1
        if original: self._stash_boards(45)
        if original: print("Waiting for opponent...")

    def handle_game_end(self, winner_color: Optional[Color], win_reason: Optional[WinReason],
                        game_history: GameHistory):
        game_history.save('games/game.json')
        print(f"{winner_color} won by {win_reason}!")

    def _stash_boards(self, maxToKeep):
        # self.beliefState.display()
        print(f"{len(self.beliefState.myBoardDist.keys())} boards, stashing boards...")
        # input()
        mostLikelyBoards = list(sorted(self.beliefState.myBoardDist, key=self.beliefState.myBoardDist.get, reverse=True))[:maxToKeep]
        self.beliefState.stashedBoards[self.turn] = set(self.beliefState.myBoardDist.keys()).difference(mostLikelyBoards)
        newMyBoardDist = {board: self.beliefState.myBoardDist[board] for board in mostLikelyBoards}
        # if sum(newMyBoardDist.values())>0:
        #     newestMyBoardDist = dict()
        #     for fen, prob in newMyBoardDist.items():
        #         if prob == 0:
        #         # if random.randint(1,3)%2==1 and len(newMyBoardDist.keys())>0:
        #             self.beliefState.stashedBoards[self.turn].add(fen)
        #         else:
        #             newestMyBoardDist[fen] = self.beliefState.myBoardDist[fen]
        #             # newOppBoardDists[fen] = self.beliefState.oppBoardDists[fen]
        #     newMyBoardDist = newestMyBoardDist
        self.beliefState.myBoardDist = normalize(newMyBoardDist)
        # self.beliefState.oppBoardDists = newOppBoardDists
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
        print(f"Ran out of boards, taking from stash in phase: {phase}...", flush=True)
        # input()
        turn = self.turn
        while len(self.beliefState.stashedBoards[turn])==0:
            turn-=1

        print(f"Found {len(self.beliefState.stashedBoards[turn])} stashed boards at turn {turn}, currently turn {self.turn}", flush=True)
        stashedBoards = self.beliefState.stashedBoards[turn]
        self.beliefState.myBoardDist = {fen: 1/len(stashedBoards) for fen in stashedBoards}
        del self.beliefState.stashedBoards[turn]
        self.beliefState.oppBoardDists = {fen: {fen: 1.0} for fen in self.beliefState.myBoardDist}
        # print(f"Starting on turn {turn}")
        # print("History is:")
        # print(self.history)
        # input()
        while len(self.history[turn])>0:
            print(f"Found {len(self.history[turn])}/3 pieces of history at turn {turn}")
            assert len(self.history[turn][0]) == 3, self.history[turn]
            # oppMoveResult, senseResult, moveResult = self.history[turn]
            try:
                self.handle_opponent_move_result(*self.history[turn][0])
            except:
                return
            print("handled opponent move result,")
            if len(self.history[turn]) == 1:
                break
            assert len(self.history[turn][1]) == 2, self.history[turn]
            try:
                self.handle_sense_result(*self.history[turn][1])
            except:
                return
            print("handled sense result,")
            if len(self.history[turn]) == 2:
                break
            # print(turn, self.turn, self.history[turn])
            assert len(self.history[turn][2]) == 5, self.history[turn]
            moveResult = self.history[turn][2]
            try:
                self.handle_move_result(*moveResult)
            except:
                return
            print("and handled move result.")
            turn += 1
        print(f"Restored {len(self.beliefState.myBoardDist.keys())} boards")
        if not self.useHelperBot and len(self.beliefState.myBoardDist) == 0:
            self._expand_stashed_boards(phase=phase)
        # self.beliefState.display()
        # input()
        