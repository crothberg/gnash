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
import time
import sys
import datetime



##TODO: Bonus to positions where king has few empty squares next to it
##TODO: To play quickly, add "quick_handle_opp_move":
#          get n stockfish moves for likely boards and (for opp) check! moves for unlikely boards
##TODO: If they could have made a good move but didn't, make that board less likely
##TODO: Fix bug where we took their king (but weren't sure we would), and unstash boards after we capture it
##TODO: Combine oppMoveResultUpdate and senseUpdate?
class GnashBot(Player):

    def __init__(self):
        self.color = None
        self.board = None
        self.beliefState = None
        self.firstTurn = True
        self.moveStartTime = None
        self.helperBot = HelperBot()
        self.useHelperBot = False
        self.useHelperBotTime = 60
        self.turn = 0
        self.whiteStartingMoves = [chess.Move(chess.D2, chess.D3), chess.Move(chess.C1, chess.D2), chess.Move(chess.G1, chess.F3)] #chess.Move(chess.C2, chess.C4), chess.Move(chess.B1, chess.C3)]
        self.blackStartingMoves = [chess.Move(chess.D7, chess.D6), chess.Move(chess.C8, chess.D7), chess.Move(chess.G8, chess.F6)] #chess.Move(chess.C7, chess.C5), chess.Move(chess.B8, chess.C6)]
        #opponent_move_result, sense_result, move_result
        #for every turn
        self.history = defaultdict(list)

    def handle_game_start(self, color: Color, board: chess.Board, opponent_name: str):
        now = datetime.datetime.now()
        gameTimeStr = f"{now.date()}_{now.hour}_{now.minute}_{now.second}"
        if opponent_name not in {"moveFinder", "senseFinder"}:
            sys.stdout=open(f"gameLogs/{opponent_name}_{gameTimeStr}.txt","w")
        print(f"PLAYING {opponent_name} AS {'WHITE' if color else 'BLACK'}! Let's go!")
        self.color = color
        self.board = board
        self.opponent_name = opponent_name
        print('Game has started.')
        self.beliefState = BeliefState(color, board.fen())
        self.gameEndTime = time.time() + 900
        self.playFromStartingMoves = False
        if opponent_name in {"random", "RandomBot"}:
            self.set_gear(4)
        # if opponent_name in {"attacker", "AttackerBot"}:
        # self.set_gear(3)
        #     self.set_gear(0)
        #     # self.set_gear(3)
        #     self.playFromStartingMoves = True
        #     self.whiteStartingMoves = [chess.Move(chess.G2, chess.G3)] + self.whiteStartingMoves
        #     self.blackStartingMoves = [chess.Move(chess.G7, chess.G6)] + self.blackStartingMoves
        else:
            self.set_gear(0)
        # self.set_gear(4)

    def set_gear(self, gear):
        self.gear = gear
        if gear == 0:
            self.handleOppMoveMaxTime = 12
            self.handleSenseMaxTime = 5
            self.handleMoveMaxTime = 3
            self.chooseMoveMaxTime = 5
            self.maxInDist = 130
        if gear == 1:
            print("Picking up speed...")
            self.handleOppMoveMaxTime = 9
            self.handleSenseMaxTime = 3
            self.handleMoveMaxTime = 1
            self.chooseMoveMaxTime = 3
            self.maxInDist = 50
        if gear == 2:
            print("Faster and faster...")
            self.handleOppMoveMaxTime = 6
            self.handleSenseMaxTime = 2
            self.handleMoveMaxTime = .5
            self.chooseMoveMaxTime = 2
            self.maxInDist = 30
        if gear == 3:
            print("Full speed ahead!")
            self.handleOppMoveMaxTime = 4
            self.handleSenseMaxTime = 1
            self.handleMoveMaxTime = .5
            self.chooseMoveMaxTime = 1
            self.maxInDist = 10
        if gear == 4:
            print("Helper bot taking over to speed things up...")
            self.useHelperBot = True
            mostLikelyBoard = max(self.beliefState.myBoardDist, key=self.beliefState.myBoardDist.get)
            self.helperBot.handle_game_start(self.color, chess.Board(mostLikelyBoard), self.opponent_name)

    def updateSpeed(self):
        timeLeft = self.gameEndTime - time.time()
        # if 200 < timeLeft <= 300 and self.gear < 1:
        #     self.set_gear(1)            
        # if 100 < timeLeft <= 200 and self.gear < 2:
        #     self.set_gear(2)
        # if 50 < timeLeft <= 100 and self.gear < 3:
        #     self.set_gear(3)
        if timeLeft <= 120 and self.gear < 4:
            self.set_gear(4)

    def handle_opponent_move_result(self, captured_my_piece: bool, capture_square: Optional[Square], original=True):
        if original and captured_my_piece: print(f"They captured a piece on {str(capture_square)}!")
        self.updateSpeed()           
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
            self.beliefState.opp_move_result_update(captured_my_piece, capture_square, maxTime=self.handleOppMoveMaxTime if original else 0.001)
        except ValueError:
            self._expand_stashed_boards(phase="handle_opponent_move_result")
        if original: print(f"Handled opponent move result in {time.time()-t0} seconds.")

    def choose_sense(self, sense_actions: List[Square], move_actions: List[chess.Move], seconds_left: float) -> \
            Optional[Square]:
        self.gameEndTime = time.time() + seconds_left
        self.updateSpeed()
        t0 = time.time()
        if self.useHelperBot:
            return self.helperBot.choose_sense(sense_actions, move_actions, seconds_left)
        print('\nSensing now...')
        sense_move = select_sense(self.beliefState.myBoardDist, actuallyUs=True)
        print('\nSensing move is', sense_move)
        print(f"Chose a sensing action in {time.time()-t0} seconds.")
        return sense_move

    def handle_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]], original=True):
        self.updateSpeed()
        if original:
            self.history[self.turn].append((sense_result, False))
        t0 = time.time()
        if self.useHelperBot:
            self.helperBot.handle_sense_result(sense_result)
            return
        # print('\nSense result is', sense_result)
        if original: print('Updating belief state after sense result...')
        try:
            self.beliefState.sense_update(sense_result, maxTime = self.handleSenseMaxTime if original else 0.001)
        except ValueError:
            self._expand_stashed_boards(phase="handle_sense_result")
        if original: print('Our updated belief dist is now as follows:')
        if original: self.beliefState.display()
        bestKey = max(self.beliefState.myBoardDist, key=self.beliefState.myBoardDist.get)
        if original: print(bestKey, self.beliefState.myBoardDist[bestKey])
        if original: print(f"Handled sense result in {time.time()-t0} seconds.")

    def choose_move(self, move_actions: List[chess.Move], seconds_left: float) -> Optional[chess.Move]:
        self.gameEndTime = time.time() + seconds_left
        self.updateSpeed()
        t0 = time.time()
        if self.useHelperBot:
            return self.helperBot.choose_move(move_actions, seconds_left)
        print(f"Choosing move with {self.gameEndTime - time.time()} seconds remaining...")
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
            move = select_move(self.beliefState, maxTime=self.chooseMoveMaxTime)
        print("MOVE:", move)
        if move == chess.Move.null():
            return None
        print(f"Chose a move in {time.time()-t0} seconds.")
        return move

    def handle_move_result(self, requested_move: Optional[chess.Move], taken_move: Optional[chess.Move],
                           captured_opponent_piece: bool, capture_square: Optional[Square], original=True):
        if original and captured_opponent_piece: print(f"We captured a piece on {str(capture_square)}!")
        self.updateSpeed()
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
            result = self.beliefState.our_move_result_update(requested_move, taken_move, captured_opponent_piece, capture_square, maxTime=self.handleMoveMaxTime if original else .001)
            if result == "won":
                return
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
        if original: self.turn += 1
        if original: self._stash_boards(self.maxInDist)
        if original: print("Waiting for opponent...")

    def handle_game_end(self, winner_color: Optional[Color], win_reason: Optional[WinReason],
                        game_history: GameHistory):
        game_history.save('games/game.json')
        print(f"{'We' if winner_color == self.color else f'They ({self.opponent_name})'} beat {'us' if winner_color != self.color else self.opponent_name} by {win_reason}!")
        for engine_list in [moving_engines, [analysisEngine], extra_engines, [okayJustOneMore]]:
            for engine in engine_list:
                engine.quit()

    ##TODO: Avoid stashing board where 3 or fewer of their pieces have moved
    def _stash_boards(self, maxToKeep):
        if len(self.beliefState.myBoardDist.keys()) > self.maxInDist:
            print(f"{len(self.beliefState.myBoardDist.keys())} boards, stashing boards...")
        sortedFens = list(sorted(self.beliefState.myBoardDist, key=self.beliefState.myBoardDist.get, reverse=True))
        mostLikelyBoards = sortedFens[:maxToKeep]
        unlikelyBoards = sortedFens[maxToKeep:]
        self.beliefState.stashedBoards[self.turn] = unlikelyBoards
        for board in self.beliefState.stashedBoards[self.turn]:
            del self.beliefState.oppBoardDists[board]
        newMyBoardDist = {board: self.beliefState.myBoardDist[board] for board in mostLikelyBoards}
        self.beliefState.myBoardDist = normalize(newMyBoardDist)
        print(f"Now there are {len(self.beliefState.myBoardDist.keys())} boards")
    
    #If myBoardDist is empty, restock with possible boards
    def _expand_stashed_boards(self, phase):
        assert len(self.beliefState.myBoardDist.keys()) == 0, "stashed boards cannot be expanded when there are still boards in the distribution"
        print(f"Ran out of boards, taking from stash in phase: {phase}...", flush=True)
        turn = self.turn
        while len(self.beliefState.stashedBoards[turn])==0 and turn >=0:
            turn-=1
        assert turn>0, f"{self.beliefState.stashedBoards} should not be empty"
        # if all([len(self.beliefState.stashedBoards[t]) == 0 for t in range(turn)]):
        #   print("No more reserve, using helper bot with possible board while we still can...")
        #   self.useHelperBot = True
        #   possibleBoard = self.beliefState.stashedBoards[turn].pop()
        #   self.helperBot.handle_game_start(self.color, chess.Board(possibleBoard), self.opponent_name)


        print(f"Found {len(self.beliefState.stashedBoards[turn])} stashed boards at turn {turn}, currently turn {self.turn}", flush=True)
        selected = self.beliefState.stashedBoards[turn][:self.maxInDist]
        self.beliefState.stashedBoards[turn] = self.beliefState.stashedBoards[turn][self.maxInDist:]
        self.beliefState.myBoardDist = {fen: 1/len(selected) for fen in selected}
        self.beliefState.oppBoardDists = {fen: {fen: 1.0} for fen in self.beliefState.myBoardDist}
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
        