import chess
import chess.engine
import random
from reconchess.history import Turn
from reconchess.utilities import *
import os
import gevent
import time

os.environ['STOCKFISH_EXECUTABLE'] = os.path.dirname(os.path.realpath(__file__)) + '/../stockfish/stockfish_14_x64_avx2.exe'
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
NUM_ENGINES=5
moving_engines = [chess.engine.SimpleEngine.popen_uci(stockfish_path, setpgrp=True) for _ in range(NUM_ENGINES)]
analysis_engines = [chess.engine.SimpleEngine.popen_uci(stockfish_path, setpgrp=True) for _ in range(NUM_ENGINES)]
extra_engines = [chess.engine.SimpleEngine.popen_uci(stockfish_path, setpgrp=True) for _ in range(NUM_ENGINES)]
oneMoreEngine = chess.engine.SimpleEngine.popen_uci(stockfish_path, setpgrp=True)
print('Stockfish engines initialized..')

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def normalize(dist, adjust = False, giveToZeros=.10):
    if len(dist) == 0:
        raise(ValueError)
    total = sum(dist.values())
    if adjust and total == 0:
        total = len(dist)
        for e in dist:
            dist[e] = 1/total
    elif adjust and giveToZeros > 0 and len(dist)>1:
        assert giveToZeros < 1
        if giveToZeros:
            zeroThreshold = giveToZeros/(len(dist)-1)
            numZeros = sum([1 for x in dist.values() if x <= zeroThreshold])
            total = sum([x for x in dist.values() if x > zeroThreshold])
            if numZeros == len(dist):
                for e in dist:
                    dist[e] = 1/len(dist)
                return dist
            elif numZeros/len(dist) < giveToZeros:
                total = sum(dist.values())
                for e in dist:
                    dist[e] /= total
                return dist
            for e in dist:
                if dist[e] <= zeroThreshold:
                    dist[e] = (1/numZeros) * giveToZeros
                else:
                    dist[e] = (dist[e]/total) * (1-giveToZeros)
    else:
        for e in dist:
            dist[e] /= total
    return dist

def normalize_board_dist_helper(fen, dist, engine):
    try:
        dist[fen] = (1 - evaluate_board_to_play(chess.Board(fen), engine, time=.03))**7
    except:
        dist[fen] = random.random()
def normalize_board_dist(dist):
    a = list(dist.values())[0]
    #If all boards have the same value...
    if len(dist) > 1 and all(x == a for x in dist.values()):
    # if True:
        # print(dist)
        print(f"adjusting dist of size {len(dist)}...")
        t0 = time.time()
        # input("Here. Hit any key to continue")
        for chunk in chunks(list(dist.keys()), NUM_ENGINES):
            gevent.joinall([gevent.spawn(normalize_board_dist_helper, fen, dist, engine) for fen, engine in zip(chunk, extra_engines)])
        # print(dist)
        print(f"Completed after {time.time()-t0} seconds")
        # input("Completed. Hit any key to continue.")
    return normalize(dist, adjust=True)

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

GOOD_SENSING_SQUARES = [i*8 + j for i in range(1,7) for j in range(1,7)]

##TODO: Find a better way to avoid leaving our king in check
# Score of the person who just played
# return score [.1, .9] if not lost, 0 if lost, 1 if won
def evaluate_board(board: chess.Board, engine):
    color = board.turn
    board.clear_stack()
    board.turn = color
    if board.king(board.turn) == None:
        return 1
    if (board.attackers(board.turn, board.king(not board.turn))):
        return 0
    baseScore = engine.analyse(board, chess.engine.Limit(time=0.05))['score'].pov(not board.turn).score(mate_score=153)
    score = max(-.8, min(.8, baseScore/153))
    score += (1-score)/2
    return score
#Score from the position of the person whose turn it is
def evaluate_board_to_play(board: chess.Board, engine, time=0.05):
    color = board.turn
    board.clear_stack()
    board.turn = color
    if (board.attackers(board.turn, board.king(not board.turn))):
        return 1
    baseScore = engine.analyse(board, chess.engine.Limit(time))['score'].pov(board.turn).score(mate_score=153)
    # if (not color): baseScore *= -1
    score = max(-1, min(1, baseScore/153))
    score += (1-score)/2
    if (board.attackers(not board.turn, board.king(board.turn))):
        score = max(0, score-.3)
    return score

def without_pieces(board: chess.Board, color) -> chess.Board:
    """Returns a copy of `board` with the opponent's pieces removed."""
    mine = board.occupied_co[not color]
    return board.transform(lambda bb: bb & mine)