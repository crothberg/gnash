import sys
import chess
from reconchess import *
from game.BeliefState import *
from game.Stash import Stash
from strategy.select_sense import select_sense
from helper_bot import HelperBot
import chess.engine
from utils.exceptions import EmptyBoardDist
from utils.util import *
from utils.history_utils import *
import utils.engine_utils as engines
from utils.engine_utils import quit_on_exceptions
import time
import datetime
import requests

##TODO: To play quickly, add "quick_handle_opp_move":
#          get n stockfish moves for likely boards and (for opp) check! moves for unlikely boards
##TODO: Fix bug where we took their king (but weren't sure we would), and unstash boards after we capture it
##TODO: Combine oppMoveResultUpdate and senseUpdate?
##TODO: Add boardDist evaluation
##TODO: extra points for lots of possible moves, keep good pieces in different sensing zones?
##Something to try: use attack-bot moves until a capture on the first two rows?
##TODO: Add MoveSelector class that can be instantiated (one for us, one for them (in beliefState))
class GnashBot(Player):

    def __init__(self, isTest = False):
        self.color = None
        self.board = None
        self.beliefState = None
        self.firstTurn = True
        self.moveStartTime = None
        self.isTest = isTest
        self.helperBot = HelperBot()
        self.useHelperBot = False
        self.useHelperBotTime = 90
        self.turn = 0
        self.useLocal = True
        self.useService = False

    @quit_on_exceptions
    def handle_game_start(self, color: Color, board: chess.Board, opponent_name: str):
        self.color, self.board, self.opponent_name = color, board, opponent_name
        print(f"PLAYING {opponent_name} AS {'WHITE' if color else 'BLACK'}! Let's go!")

        now = datetime.datetime.now()
        gameTimeStr = f"{now.date()}_{now.hour}_{now.minute}_{now.second}"
        if not self.isTest and opponent_name not in {"moveFinder", "senseFinder"}:
            outFile = open(f"gameLogs/{opponent_name}_{gameTimeStr}.txt","w")
            sys.stdout = outFile
            sys.stderr = outFile

        if not self.useService:
            self.stash = Stash(self.color)
            self.stash.start_background_processor()
        else:
            self.baseurl = "http://127.0.0.1:5000/" if self.useLocal else "https://gnash-3ndl4yawkq-uc.a.run.app"
            self.gameId = hash(gameTimeStr)

            requests.post(f"{self.baseurl}/start/{self.gameId}", json={"color":self.color})

        self.gameEndTime = time.time() + 900

        self.set_gear(0)
        profiles = {
            #us and them
            "oracle": (.02, 0.001),
            "random": (1.0, None),
            "RandomBot": (1.0, None),
            "attacker": (.3, 1.5),
            "AttackBot": (.3, 1.5),
            "penumbra": (.02, .85),
            "Fianchetto": (.02, .6),
            "StrangeFish2": (.2, .05),
            "trout": (.3, .1),
            "TroutBot": (.3, .1),
        }
        gUs, gThem = profiles[self.opponent_name] if self.opponent_name in profiles else (None, None)
        gUs = gUs or .03
        gThem = gThem or .1
        self.moveSelector = MoveSelector(actuallyUs=True, gambleFactor=gUs, timePerMove=self.chooseMoveMaxTime)
        oppMoveSelector = MoveSelector(actuallyUs=False, gambleFactor=gThem, timePerMove=None)

        self.beliefState = BeliefState(color, board.fen(), self.moveSelector, oppMoveSelector)

        if opponent_name in {"random", "RandomBot"}:
            self.set_gear(4 if not self.isTest else 0)
        else:
            self.set_gear(0)

    def set_gear(self, gear):
        self.gear = gear
        if gear == 0:
            self.handleOppMoveMaxTime = 12
            self.handleSenseMaxTime = 5
            self.handleMoveMaxTime = 3
            self.chooseMoveMaxTime = 5
            self.maxInDist = 100
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
            self.maxInDist = 2
        if gear == 4:
            self.maxInDist = 1
            print("Helper bot taking over to speed things up...")
            self.useHelperBot = True
            mostLikelyBoard = max(self.beliefState.myBoardDist, key=self.beliefState.myBoardDist.get)
            self.helperBot.handle_game_start(self.color, chess.Board(mostLikelyBoard), self.opponent_name)

    @quit_on_exceptions
    def updateSpeed(self):
        timeLeft = self.gameEndTime - time.time()
        if timeLeft <= self.useHelperBotTime and self.gear < 4:
            self.set_gear(4)

    @quit_on_exceptions
    def stash_and_add_history(self, phase : Phase, turn : int, history : tuple):
        if self.useHelperBot: return
        boardsToKeep = list(sorted(self.beliefState.myBoardDist, key = self.beliefState.myBoardDist.get, reverse=True))[:self.maxInDist]
        bestBoard = boardsToKeep[0]
        boardsToStash = set(self.beliefState.myBoardDist).difference(boardsToKeep)
        for board in boardsToStash:
            self.beliefState.oppBoardDists.pop(board)
            self.beliefState.myBoardDist.pop(board)
        normalize(self.beliefState.myBoardDist, adjust=True, giveToZeros=0)
        print("Sending new boards...")
        requests.post(f"{self.baseurl}/stash-boards/{self.gameId}/{turn}/{phase.value}", json = {"boardsToStash": list(boardsToStash), "bestBoard": bestBoard})
        print("Sending new boards completed.")

        print("Sending new history...")
        if phase == Phase.OPP_MOVE_RESULT:
            json={"capMyPiece":history[0], "capSquare":history[1]}
            requests.post(f"{self.baseurl}/add-opp-move-result/{self.gameId}/{turn}/{phase.value}", json=json)
        if phase == Phase.SENSE_RESULT:
            senseResults = history
            json={"squares":[x[0] for x in senseResults], "pieces":[x[1].symbol() if x[1] is not None else None for x in senseResults]}
            requests.post(f"{self.baseurl}/add-sense-result/{self.gameId}/{turn}/{phase.value}", json=json)
        if phase == Phase.OUR_MOVE_RESULT:
            json={"reqMove": history[0].uci() if history[0] is not None else None, "takMove": history[1].uci() if history[1] is not None else None, "capOppPiece":history[2], "capSquare":history[3]}
            requests.post(f"{self.baseurl}/add-our-move-result/{self.gameId}/{turn}/{phase.value}", json=json)
        print("Sending new history completed.")

    @quit_on_exceptions
    def get_new_boards(self, urgent=True):
        if self.useHelperBot: return
        extraTime = (self.gameEndTime - time.time()) - self.useHelperBotTime
        if not self.useService:
            print(f"Requesting new boards (urgent = {urgent})...")
            originalNumBoards = len(self.beliefState.myBoardDist)
            t0 = time.time()
            rescueBoard = self.stash.add_possible_boards(self.beliefState, self.maxInDist, urgent=urgent, timeRemaining=extraTime)
            if rescueBoard != None:
                self.useHelperBot = True
                helperBotBoard = chess.Board(rescueBoard)
                print(f"Helper bot invoked with board {helperBotBoard.fen()}")
                self.helperBot.handle_game_start(self.color, helperBotBoard, self.opponent_name)
            if urgent: print(f"Received {len(self.beliefState.myBoardDist)} boards after {time.time()-t0} seconds.")
            else:
                if len(self.beliefState.myBoardDist) > originalNumBoards:
                    print(f"Received {len(self.beliefState.myBoardDist) - originalNumBoards} supplementary boards in just {time.time()-t0} seconds.")
                else:
                    print("Didn't find anything new in the stash...")
            return
        print("Sending request for new boards...") 
        result = requests.post(f"{self.baseurl}/get-possible-boards/{self.gameId}", json={"numBoards":self.maxInDist, "extraTime":extraTime}).json()
        if result["useHelperBot"]:
            helperBotBoard = chess.Board(result["helperBotFen"])
            print(f"Helper bot invoked with board {helperBotBoard.fen()}")
            self.useHelperBot = True
            self.helperBot.handle_game_start(self.color, helperBotBoard, self.opponent_name)
        else:
            boards = result["fens"]
            self.beliefState.myBoardDist = {b: 1/len(boards) for b in boards}
            self.beliefState.oppBoardDists = {b: {b:1.0} for b in boards}
            print(f"Received {len(boards)} boards in response")
            self.beliefState._check_invariants()

    @quit_on_exceptions
    def handle_opponent_move_result(self, captured_my_piece: bool, capture_square: Optional[Square]):
        self.updateSpeed() 
        
        phase, turn = Phase.OPP_MOVE_RESULT, self.turn
        if self.useService:
            self.stash_and_add_history(phase, turn, (captured_my_piece, capture_square))
        else:                
            self.stash.stash_boards(phase, turn, self.beliefState, self.maxInDist)
            self.stash.add_history(turn, phase, (captured_my_piece, capture_square))

        if self.firstTurn and self.color: self.firstTurn = False; return

        print('\nOpponent moved, handling result...')
        if captured_my_piece: print(f"They captured a piece on {str(capture_square)}!")

        t0 = time.time()
        if self.useHelperBot: self.helperBot.handle_opponent_move_result(captured_my_piece, capture_square); return
        self.beliefState._check_invariants()
        try:
            self.beliefState.opp_move_result_update(captured_my_piece, capture_square, maxTime=self.handleOppMoveMaxTime)
        except EmptyBoardDist:
            self.get_new_boards()
        self.get_new_boards(urgent=False)
        self.beliefState._check_invariants()
        print(f"Handled opponent move result in {time.time() - t0} seconds.")

    @quit_on_exceptions
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

    @quit_on_exceptions
    def handle_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]]):
        self.updateSpeed()

        phase, turn = Phase.SENSE_RESULT, self.turn
        if self.useService:
            self.stash_and_add_history(phase, turn, (sense_result))
        else:
            self.stash.stash_boards(phase, turn, self.beliefState, self.maxInDist)
            self.stash.add_history(turn, phase, (sense_result))

        print('Updating belief state after sense result...')
        t0 = time.time()
        if self.useHelperBot:
            self.helperBot.handle_sense_result(sense_result)
            return
        try:
            self.beliefState.sense_update(sense_result, maxTime = self.handleSenseMaxTime)
        except EmptyBoardDist:
            self.get_new_boards()
        self.get_new_boards(urgent=False)
        # print('Our updated belief dist is now as follows:')
        if not self.useHelperBot:
            if self.useService:
                self.beliefState.display()
            if not self.useService:
                self.beliefState.display(self.stash)
            bestKey = max(self.beliefState.myBoardDist, key=self.beliefState.myBoardDist.get)
            print(bestKey, self.beliefState.myBoardDist[bestKey])
            print(f"Handled sense result in {time.time()-t0} seconds.")

    @quit_on_exceptions
    def choose_move(self, move_actions: List[chess.Move], seconds_left: float) -> Optional[chess.Move]:
        self.gameEndTime = time.time() + seconds_left
        self.updateSpeed()
        t0 = time.time()
        if self.useHelperBot:
            print("Choosing move with helper bot!")
            move = self.helperBot.choose_move(move_actions, seconds_left)
            print(f"Helper bot chose move {move}")
            return move
        print(f"Choosing move with {self.gameEndTime - time.time()} seconds remaining...")
        move = self.moveSelector.select_move(self.beliefState)
        print("MOVE:", move)
        if move == chess.Move.null():
            return None
        print(f"Chose a move in {time.time()-t0} seconds.")
        return move

    @quit_on_exceptions
    def handle_move_result(self, requested_move: Optional[chess.Move], taken_move: Optional[chess.Move],
                           captured_opponent_piece: bool, capture_square: Optional[Square]):
        phase, turn = Phase.OUR_MOVE_RESULT, self.turn
        if self.useService:
            self.stash_and_add_history(phase, turn, (requested_move, taken_move, captured_opponent_piece, capture_square))
        else:
            self.stash.stash_boards(phase, turn, self.beliefState, self.maxInDist)
            self.stash.add_history(turn, phase, (requested_move, taken_move, captured_opponent_piece, capture_square))

        self.updateSpeed()
        t0 = time.time()
        print('Handling our move result:')
        print('\nRequested move', requested_move, ', took move', taken_move)
        if captured_opponent_piece: print(f"We captured a piece on {str(capture_square)}!")
        if self.useHelperBot:
            self.helperBot.handle_move_result(requested_move, taken_move, captured_opponent_piece, capture_square)
            return
        try:
            result = self.beliefState.our_move_result_update(requested_move, taken_move, captured_opponent_piece, capture_square, maxTime=self.handleMoveMaxTime)
            if result == "won":
                # self.handle_game_end(self.color, WinReason.KING_CAPTURE, None)
                return
        except EmptyBoardDist:
            self.get_new_boards()
        self.get_new_boards(urgent=False)
        print(f"Handled our move result in {time.time()-t0} seconds.")
        
        t1 = time.time()
        print('\nAnticipating opponent sense...')
        self.beliefState.opp_sense_result_update()
        print(f"Handled anticipated opponent sensing action in {time.time()-t1} seconds.")
        self.turn += 1
        print("Waiting for opponent...")

    @quit_on_exceptions
    def handle_game_end(self, winner_color: Optional[Color], win_reason: Optional[WinReason],
                        game_history: GameHistory):
        if (game_history != None): game_history.save('games/game.json')
        if self.useService:
            requests.post(f"{self.baseurl}/game-over/{self.gameId}")
        else:
            self.stash.end_background_processor()
        print(f"{'We' if winner_color == self.color else f'They ({self.opponent_name})'} beat {'us' if winner_color != self.color else self.opponent_name} by {win_reason}!")
        engines.shut_down_engines()
        if self.useHelperBot:
            try:
                self.helperBot.engine.quit()
            except:
                pass
