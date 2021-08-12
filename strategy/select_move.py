import os
from chess import *
import chess.engine
from utils.types import *
from utils.util import *

STOCKFISH_ENV_VAR = 'STOCKFISH_EXECUTABLE'

# make sure stockfish environment variable exists
if STOCKFISH_ENV_VAR not in os.environ:
    raise KeyError(
        'Gnash requires an environment variable called "{}" pointing to the Stockfish executable'.format(
            STOCKFISH_ENV_VAR))

# make sure there is actually a file
stockfish_path = os.environ[STOCKFISH_ENV_VAR]
if not os.path.exists(stockfish_path):
    raise ValueError('No stockfish executable found at "{}"'.format(stockfish_path))

# initialize the stockfish engine
engine = chess.engine.SimpleEngine.popen_uci(stockfish_path, setpgrp=True)

def select_move(beliefState) -> Move:
    return select_move_from_dist(beliefState.myBoardDist)

def select_move_from_dist(boardDist):
    move = sample(get_move_dist(boardDist))
    return move

def get_move_dist(boardDist, numSamples=100):
    sampleBoard = list(boardDist.keys())[0]
    legalMoves = get_all_moves(chess.Board(sampleBoard))
    probs = {move: (numSamples*.3)/len(legalMoves) for move in legalMoves}
    for _ in range(numSamples):
        board = sample(boardDist)
        probs[get_stockfish_move(board)] += 1
    return normalize(probs)

def get_stockfish_move(fen : str) -> Move:
    board = chess.Board(fen)
    enemy_king_square = board.king(not board.turn)
    if enemy_king_square:
        # if there are any ally pieces that can take king, execute one of those moves
        enemy_king_attackers = board.attackers(board.turn, enemy_king_square)
        if enemy_king_attackers:
            attacker_square = enemy_king_attackers.pop()
            return chess.Move(attacker_square, enemy_king_square)
    move = engine.play(board, chess.engine.Limit(time=0.1)).move
    return move