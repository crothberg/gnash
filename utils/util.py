import chess
import random
from reconchess.utilities import *

##TODO: Add a way to make the zeros nonzero
def normalize(dist, adjust = False):
    total = sum(dist.values())
    if adjust and total == 0:
        total = len(dist)
        for e in dist:
            dist[e] = 1/total
    else:
        for e in dist:
            dist[e] /= total
    return dist

def sample(dist, k=1):
    if k==1:
        return random.choices(list(dist.keys()), weights=list(dist.values()), k=1)[0]
    else:
        return random.choices(list(dist.keys()), weights=list(dist.values()), k=k)

# Produce a sense result from a hypothetical true board and a sense square
def simulate_sense(board, square):  # copied (with modifications) from LocalGame
    if square is None:
        # don't sense anything
        senseResult = []
    else:
        if square not in list(chess.SQUARES):
            raise ValueError('LocalGame::sense({}): {} is not a valid square.'.format(square, square))
        senseResult = []
        senseSquares = get_sense_squares(square)
        for senseSquare in senseSquares:
            senseResult.append((senseSquare, board.piece_at(senseSquare)))
    return tuple(senseResult)

def get_sense_squares(square):
    rank, file = chess.square_rank(square), chess.square_file(square)
    senseSquares = set()
    for delta_rank in [1, 0, -1]:
            for delta_file in [-1, 0, 1]:
                if 0 <= rank + delta_rank <= 7 and 0 <= file + delta_file <= 7:
                    senseSquares.add(chess.square(file + delta_file, rank + delta_rank))
    return senseSquares

#Gets all moves that are reconchess-legal on a chess board
def get_all_moves(board : chess.Board):
    return move_actions(board) + [chess.Move.null()]

#Gets all moves that are actually legal (plus null) on at least one chessboard in fens
def get_pseudo_legal_moves(fens):
    legalMoves = set()
    legalMoves.add(chess.Move.null())
    for fen in fens:
        board = chess.Board(fen)
        legalMoves = legalMoves.union(board.pseudo_legal_moves)
    return legalMoves

GOOD_SENSING_SQUARES = [i*8 + j for i in range(1,6) for j in range(1,6)]