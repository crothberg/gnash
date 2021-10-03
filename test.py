from chess import *
import chess.engine
from utils.types import *
import json
import re
import time
from gnash_bot import GnashBot

from game.BeliefState import BeliefState
from strategy.select_move import get_move_dist

tests = [
    # "adjacent_kings.txt",
    "take_rook.txt",
    # "take_knight.txt",
    # "test.txt",
    # "test2.txt",
    # "trying_to_lose.txt",
    # "trying_to_lose2.txt",
    # "two_knight_threat.txt",
    # "winning_play_safe.txt"
]

for testFilePath in tests:
    with open(f"tests/{testFilePath}") as infile:
        color = True if (infile.readline().strip())[0] in {"w", "W"} else False
        json_string = re.sub(r'\n', ', "', infile.read().strip())
        json_string = '{"' + re.sub(r' +probability: ', '": ', json_string) + '}'
    print(json_string)
    board_dist = json.loads(json_string, strict=False)

    print(board_dist)

    gnash = GnashBot()
    gnash.handle_game_start(color, chess.Board(), 'senseFinder')
    gnash.beliefState = BeliefState(gnash.color)
    gnash.beliefState.myBoardDist = board_dist
    gnash.beliefState.oppBoardDists = {fen: {fen : 1.0} for fen in gnash.beliefState.myBoardDist}
    sense = gnash.choose_sense([], [], 500)
    print(f"Chose sense: {sense}")

    gnash = GnashBot()
    gnash.handle_game_start(color, chess.Board(), 'moveFinder')
    gnash.beliefState = BeliefState(gnash.color)
    gnash.beliefState.myBoardDist = board_dist
    gnash.beliefState.oppBoardDists = {fen: {fen : 1.0} for fen in gnash.beliefState.myBoardDist}
    move = gnash.choose_move([], 500)
    print(f"Chose move: {move}")

    input()
    # board_dist_orig = board_dist
    # gnash.handle_move_result(requested_move=chess.Move.from_uci('b6b4'), taken_move=chess.Move.from_uci('b6b4'), captured_opponent_piece=False, capture_square=None)
    # board_dist_moved = gnash.beliefState.myBoardDist
    # gnash.beliefState.display()
    # print('MOVE DIST')
    # print(get_move_dist(gnash.beliefState.myBoardDist, .1))
    # gnash.handle_opponent_move_result(captured_my_piece=False, capture_square=None)
    # board_dist_opp_moved = gnash.beliefState.myBoardDist



# os.environ['STOCKFISH_EXECUTABLE'] = os.path.dirname(os.path.realpath(__file__)) + '/stockfish/stockfish_14_x64_avx2.exe'
# STOCKFISH_ENV_VAR = 'STOCKFISH_EXECUTABLE'

# # make sure stockfish environment variable exists
# if STOCKFISH_ENV_VAR not in os.environ:
#     raise KeyError(
#         'Gnash requires an environment variable called "{}" pointing to the Stockfish executable'.format(
#             STOCKFISH_ENV_VAR))

# # make sure there is actually a file
# stockfish_path = os.environ[STOCKFISH_ENV_VAR]
# if not os.path.exists(stockfish_path):
#     raise ValueError('No stockfish executable found at "{}"'.format(stockfish_path))

# # initialize the stockfish engine
# print('setting up engine...')
# engine = chess.engine.SimpleEngine.popen_uci(stockfish_path, setpgrp=True)
# print('engine setup complete!')