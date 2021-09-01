from chess import *
import chess.engine
from utils.types import *
import json
import re
import time
from gnash_bot import GnashBot

from game.BeliefState import BeliefState
from strategy.select_move import get_move_dist

with open('bd.txt') as infile:
    json_string = re.sub(r'\n {3,}', ', "', infile.read().strip())
    json_string = '{"' + re.sub(r' +probability: ', '": ', json_string) + '}'
board_dist = json.loads(json_string)

gnash = GnashBot()
gnash.color = chess.BLACK
gnash.moveStartTime = time.time()
gnash.beliefState = BeliefState(gnash.color)
gnash.beliefState.myBoardDist = board_dist

board_dist_orig = board_dist
gnash.handle_move_result(requested_move=chess.Move.from_uci('d8c7'), taken_move=chess.Move.from_uci('d8c7'), captured_opponent_piece=False, capture_square=None)
board_dist_moved = gnash.beliefState.myBoardDist
gnash.beliefState.display()
print('MOVE DIST')
print(get_move_dist(gnash.beliefState.myBoardDist, .1))
gnash.handle_opponent_move_result(captured_my_piece=False, capture_square=None)
board_dist_opp_moved = gnash.beliefState.myBoardDist



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