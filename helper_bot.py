from utils.engine_utils import quit_on_exceptions
import utils.engine_utils as engines
from utils.util import *
import chess
from reconchess import *
import random
import os

STOCKFISH_ENV_VAR = 'STOCKFISH_EXECUTABLE'
#A fast bot for just in case
##TODO: Improve play when no enemy king is found on board
class HelperBot():
    @quit_on_exceptions
    def __init__(self):
        self.board = None
        self.color = None
        self.my_piece_captured_square = None
        self.requestedMove = None
        self.takenMove = None
        self.movesSinceMoved = 0
    @quit_on_exceptions
    def handle_game_start(self, color: Color, board: chess.Board, opponent_name: str):
        self.color = color
        self.board = board
        self.lastKingSquare = board.king(not self.color)
        self.kingSquare = board.king(not self.color)

        self.searchSquares = [52,50,54,49] if self.color else [12,10,14,9]
        self.searched = 0

    @quit_on_exceptions
    def handle_opponent_move_result(self, captured_my_piece: bool, capture_square: Optional[Square]):
        ##TODO: Improve removal of opponent's pieces that we sensed have moved
        self.board.turn = not self.color
        # if the opponent captured our piece, remove it from our board.
        self.my_piece_captured_square = capture_square
        if captured_my_piece:
            self.board.remove_piece_at(capture_square)
        boardCopy = chess.Board(self.board.fen())
        boardCopy.turn = not self.color
        allOppMoves = get_all_moves(boardCopy)
        for move in allOppMoves:
            revisedMove = revise_move(boardCopy, move) if move != chess.Move.null() else chess.Move.null()
            revisedMove = revisedMove or chess.Move.null()
            if real_capture_square_of_move(boardCopy, revisedMove) != capture_square:
                continue
            boardCopy.push(revisedMove)
            if boardCopy.is_check():
                self.board.set_piece_at(revisedMove.to_square, self.board.piece_at(move.from_square))
                return
            boardCopy.pop()
            
    @quit_on_exceptions
    def choose_sense(self, sense_actions: List[Square], move_actions: List[chess.Move], seconds_left: float) -> \
            Optional[Square]:
        if self.board.king(not self.color) == None:
            sense = random.choice(self.searchSquares)
            print(f"No king on board {self.board.fen()}, chose sense {sense}")
            return sense
        senseActions = GOOD_SENSING_SQUARES[:]
        # print(f"Choosing sense with board: {self.board.fen()}")
        # senseActions = list(filter(lambda x: any(self.lastKingSquare in get_sense_squares(y) for y in get_sense_squares(x)), GOOD_SENSING_SQUARES))
        
        # if self.kingSquare == None:
        #     if self.searched < len(self.searchSquares):
        #         search = self.searchSquares[self.searched]
        #         self.searched += 1
        #         return search
        #     if self.searched == len(self.searchSquares):
        #         self.searched += 1
        #         return self.lastKingSquare
        # checkers = self.board.attackers(not self.color, self.board.king(self.color))
        # if len(checkers) > 0:
        #     senseActions = list(filter(lambda x: any(checkSquare in get_sense_squares(x) for checkSquare in checkers), GOOD_SENSING_SQUARES))
        #     return random.choice(senseActions)

        # if our piece was just captured, sense where it was captured
        if self.my_piece_captured_square:
            if self.my_piece_captured_square in GOOD_SENSING_SQUARES:
                return self.my_piece_captured_square
            senseActions = list(filter(lambda x: self.my_piece_captured_square in get_sense_squares(x), GOOD_SENSING_SQUARES))
            return random.choice(senseActions)

        if self.takenMove != self.requestedMove and self.takenMove == None:
            senseActions = list(filter(lambda x: self.requestedMove.to_square in get_sense_squares(x), GOOD_SENSING_SQUARES))
            return random.choice(senseActions)
        # if we might capture a piece when we move, sense where the capture will occur
        future_move = self.choose_move(move_actions, seconds_left)
        if future_move is not None and self.board.piece_at(future_move.to_square) is not None:
            senseActions = list(filter(lambda x: future_move.to_square in get_sense_squares(x), GOOD_SENSING_SQUARES))            
            return random.choice(senseActions)

        # otherwise, just randomly choose a sense action, but don't sense on a square where our pieces are located
        #Choose a sense that contains lastKingSquare
        for senseSquare in GOOD_SENSING_SQUARES:
            for square in get_sense_squares(senseSquare):
                piece = self.board.piece_at(square)
                if piece != None and piece.color == self.color:
                    senseActions.remove(senseSquare)
                    break
        if len(senseActions) > 0:
            return random.choice(senseActions)
        return random.choice(GOOD_SENSING_SQUARES)

    @quit_on_exceptions
    def handle_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]]):
        ##TODO: Improve removal of opponent's pieces that we sensed have moved
        # add the pieces in the sense result to our board
        senseChoice = sense_result[4][0]
        senseResultAgrees = (simulate_sense(self.board, senseChoice) == sense_result)
        self.board.turn = not self.color
        if not senseResultAgrees and self.board.turn != self.color:
            moves = get_pseudo_legal_moves({self.board.fen()})
            for move in moves:
                if self.my_piece_captured_square != real_capture_square_of_move(self.board, move):
                    continue
                self.board.push(move)
                wouldBeSenseResult = simulate_sense(self.board, senseChoice)
                if wouldBeSenseResult == sense_result:
                    return
                self.board.pop()
        for square, piece in sense_result:
            self.board.set_piece_at(square, piece)
        oppKingSquares = []
        for square in chess.SQUARES:
            pieceAt = self.board.piece_at(square)
            if pieceAt == None:
                continue
            if pieceAt.piece_type == chess.KING and pieceAt.color == (not self.color):
                oppKingSquares.append(square)
        if len(oppKingSquares) == 0:
            self.kingSquare = None
        if len(oppKingSquares) == 1:
            self.kingSquare = oppKingSquares[0]
            self.lastKingSquare = oppKingSquares[0]
            self.searched = 0
        if len(oppKingSquares) > 1:
            assert self.kingSquare in oppKingSquares
            assert len(oppKingSquares) == 2
            oppKingSquares.remove(self.kingSquare)
            self.board.set_piece_at(self.kingSquare, None)
            self.kingSquare = oppKingSquares[0]
            self.lastKingSquare = oppKingSquares[0]
            self.searched = 0
        # enemy_king_square = oppKingSquares[0]

    @quit_on_exceptions
    def choose_move(self, move_actions: List[chess.Move], seconds_left: float) -> Optional[chess.Move]:
        self.board.turn = self.color
        print(self.board.fen())
        self.kingSquare = self.board.king(not self.color)
        # if we might be able to take the king, try to
        if self.kingSquare:
            # if there are any ally pieces that can take king, execute one of those moves
            enemy_king_attackers = self.board.attackers(self.color, self.kingSquare)
            if enemy_king_attackers:
                attacker_square = enemy_king_attackers.pop()
                return chess.Move(attacker_square, self.kingSquare)
        else:
            if self.movesSinceMoved > 8:
                return random.choice(move_actions)
            return None

        # otherwise, try to move with the stockfish chess engine
        try:
            self.board.turn = self.color
            self.board.clear_stack()
            result = engines.play(self.board, .3)
            return result.move
        except chess.engine.EngineTerminatedError:
            print('Stockfish Engine died')
        except chess.engine.EngineError:
            print('Stockfish Engine bad state at "{}"'.format(self.board.fen()))
        print("Waiting for opponent...")
        # if all else fails, pass
        return None

    @quit_on_exceptions
    def handle_move_result(self, requested_move: Optional[chess.Move], taken_move: Optional[chess.Move],
                           captured_opponent_piece: bool, capture_square: Optional[Square]):
        if requested_move == None:
            self.movesSinceMoved += 1
        else:
            self.movesSinceMoved = 0
        self.board.turn = self.color
        # if a move was executed, apply it to our board
        if taken_move is not None:
            self.board.push(taken_move)
        self.board.turn = not self.color

        self.requestedMove = requested_move
        self.takenMove = taken_move