from utils.util import *
import chess
from reconchess import *
import random
import os

STOCKFISH_ENV_VAR = 'STOCKFISH_EXECUTABLE'
#A fast bot for just in case
##TODO: Improve play when no enemy king is found on board
class HelperBot():
    def __init__(self):
        self.board = None
        self.color = None
        self.my_piece_captured_square = None

        # make sure stockfish environment variable exists
        if STOCKFISH_ENV_VAR not in os.environ:
            raise KeyError(
                'TroutBot requires an environment variable called "{}" pointing to the Stockfish executable'.format(
                    STOCKFISH_ENV_VAR))

        # make sure there is actually a file
        self.stockfish_path = os.environ[STOCKFISH_ENV_VAR]
        if not os.path.exists(self.stockfish_path):
            raise ValueError('No stockfish executable found at "{}"'.format(self.stockfish_path))
        

    def handle_game_start(self, color: Color, board: chess.Board, opponent_name: str):
        self.color = color
        self.board = board
        # initialize the stockfish engine
        self.engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path, setpgrp=True)
        self.lastKingSquare = board.king(not self.color)
        self.kingSquare = board.king(not self.color)

        self.searchSquares = [52,50,54,49] if self.color else [12,10,14,9]
        self.searched = 0

    def handle_opponent_move_result(self, captured_my_piece: bool, capture_square: Optional[Square]):
        # if the opponent captured our piece, remove it from our board.
        self.my_piece_captured_square = capture_square
        if captured_my_piece:
            self.board.remove_piece_at(capture_square)
        boardCopy = chess.Board(self.board.fen())
        boardCopy.turn = not self.color
        allOppMoves = get_all_moves(boardCopy)
        for move in allOppMoves:
            if capture_square_of_move(boardCopy, move) != capture_square:
                continue
            revisedMove = revise_move(boardCopy, move) if move != chess.Move.null() else chess.Move.null()
            revisedMove = revisedMove or chess.Move.null()
            boardCopy.push(revisedMove)
            if boardCopy.is_check():
                self.board.set_piece_at(revisedMove.to_square, self.board.piece_at(move.from_square))
                return
            boardCopy.pop()
            

    def choose_sense(self, sense_actions: List[Square], move_actions: List[chess.Move], seconds_left: float) -> \
            Optional[Square]:
        print(f"Choosing sense with board: {self.board.fen()}")
        senseActions = list(filter(lambda x: any(self.lastKingSquare in get_sense_squares(y) for y in get_sense_squares(x)), GOOD_SENSING_SQUARES))
        
        if self.kingSquare == None:
            if self.searched < len(self.searchSquares):
                search = self.searchSquares[self.searched]
                self.searched += 1
                return search
            if self.searched == len(self.searchSquares):
                self.searched += 1
                return self.lastKingSquare
        checkers = self.board.attackers(not self.color, self.board.king(self.color))
        if len(checkers) > 0:
            senseActions = list(filter(lambda x: any(checkSquare in get_sense_squares(x) for checkSquare in checkers), GOOD_SENSING_SQUARES))
            return random.choice(senseActions)

        # if our piece was just captured, sense where it was captured
        if self.my_piece_captured_square:
            return self.my_piece_captured_square

        # if we might capture a piece when we move, sense where the capture will occur
        future_move = self.choose_move(move_actions, seconds_left)
        if future_move is not None and self.board.piece_at(future_move.to_square) is not None:
            return future_move.to_square

        # # otherwise, just randomly choose a sense action, but don't sense on a square where our pieces are located
        # #Choose a sense that contains lastKingSquare
        # for square, piece in self.board.piece_map().items():
        #     if piece.color == self.color and square in sense_actions:
        #         sense_actions.remove(square)
        return random.choice(senseActions)

    def handle_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]]):
        # add the pieces in the sense result to our board
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


    def choose_move(self, move_actions: List[chess.Move], seconds_left: float) -> Optional[chess.Move]:
        print(self.board.fen())
        # if we might be able to take the king, try to
        if self.kingSquare:
            # if there are any ally pieces that can take king, execute one of those moves
            enemy_king_attackers = self.board.attackers(self.color, self.kingSquare)
            if enemy_king_attackers:
                attacker_square = enemy_king_attackers.pop()
                return chess.Move(attacker_square, self.kingSquare)
        else:
            return None

        # otherwise, try to move with the stockfish chess engine
        try:
            self.board.turn = self.color
            self.board.clear_stack()
            result = self.engine.play(self.board, chess.engine.Limit(time=0.5))
            return result.move
        except chess.engine.EngineTerminatedError:
            print('Stockfish Engine died')
        except chess.engine.EngineError:
            print('Stockfish Engine bad state at "{}"'.format(self.board.fen()))
        print("Waiting for opponent...")
        # if all else fails, pass
        return None

    def handle_move_result(self, requested_move: Optional[chess.Move], taken_move: Optional[chess.Move],
                           captured_opponent_piece: bool, capture_square: Optional[Square]):
        # if a move was executed, apply it to our board
        if taken_move is not None:
            self.board.push(taken_move)