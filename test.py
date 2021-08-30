import os
from chess import *
import chess.engine
import random
from utils.types import *
import time
import json

from strategy.select_move import get_move_dist
from strategy.select_move import select_move_from_dist
from utils.util import get_all_moves, get_pseudo_legal_moves

os.environ['STOCKFISH_EXECUTABLE'] = os.path.dirname(os.path.realpath(__file__)) + '/stockfish/stockfish_14_x64_avx2.exe'
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
print('setting up engine...')
engine = chess.engine.SimpleEngine.popen_uci(stockfish_path, setpgrp=True)
print('engine setup complete!')

board_dist = json.load(open('crash.json'))
# board_dist = {'r1bk3r/1pq2p2/p1nbpnBp/2pp2p1/1P4P1/3P4/P1PNPP1P/R1BQK1NR b - - 4 14': 1}
# print('getting all moves')
# all_moves = get_all_moves(chess.Board(list(board_dist.keys())[0]))
# print('all moves:', all_moves)
# print('getting pseudo-legal moves:')
# pseudo_legal_moves = get_pseudo_legal_moves(set(board_dist.keys()))
# print('pseudo-legal moves:', pseudo_legal_moves)
print('getting move dist...')
move_dist = get_move_dist(board_dist, 9)
print('MOVE DIST:', [d for d in move_dist])
print('Done!')
engine.quit()
print('Engine has quit.')

# scores = set()

# startTime = time.time()
# totalTriesSoFar = 0
# while time.time() - startTime < 5:
#     fen = random.choice(list(fens))
#     moves = random.choices(list(chess.Board(fen).legal_moves), k=10)
#     for move in moves:
#         board = chess.Board(fen)
#         board.push(move)
#         score = engine.analyse(board, chess.engine.Limit(time=0.05))['score'].pov(not board.turn).wdl().expectation()
#         print('\tone!', end='', flush=True)
#     print('\nmove set!', flush=True)
# while time.time() - startTime < 5:
#     fen = random.choice(list(fens))
#     moves = random.choices(list(chess.Board(fen).legal_moves), k=10)
#     for move in moves:
#         board = chess.Board(fen)
#         board.push(move)
#         score = engine.analyse(board, chess.engine.Limit(time=0.05))['score'].pov(not board.turn).wdl().expectation()
#         print('\ttwo!', end='', flush=True)
#     print('\nmove set!', flush=True)
# # print(scores)
# print('Done!')
# engine.quit()