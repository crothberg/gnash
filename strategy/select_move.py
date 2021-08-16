import os
from chess import *
import chess.engine
from utils.types import *
from utils.util import *
from reconchess.utilities import revise_move
import math

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
engine = chess.engine.SimpleEngine.popen_uci(stockfish_path, setpgrp=True)

def select_move(beliefState) -> Move:
    return select_move_from_dist(beliefState.myBoardDist)

def select_move_from_dist(boardDist):
    move = sample(get_move_dist(boardDist, maxSamples = 500))
    return move

def get_move_dist(boardDist, maxSamples):
    exampleFen = list(boardDist.keys())[0]
    legalMoves = get_all_moves(chess.Board(exampleFen))
    legalMoveScores = {move: [0, 0] for move in legalMoves} #[tries, averageScore]
    totalTriesSoFar = 0
    while totalTriesSoFar < maxSamples:
        sampleFen = sample(boardDist)
        if totalTriesSoFar == 0:
            testMoves = legalMoves
        else:
            testMoves = choose_n_moves(legalMoveScores, 10, 1, totalTriesSoFar)
            stockfishMove = get_stockfish_move(sampleFen)
            if stockfishMove not in testMoves:
                testMoves += [stockfishMove]
        for move in testMoves:
            sampleBoard = chess.Board(sampleFen)
            timesSampled, avgScore = legalMoveScores[move]
            totalScore = timesSampled*avgScore
            revisedMove = revise_move(sampleBoard, move) 
            sampleBoard.push(revisedMove if revisedMove is not None else chess.Move.null())
            newBoardScore = evaluate_board(sampleBoard)
            legalMoveScores[move][0] += 1
            legalMoveScores[move][1] = (totalScore + newBoardScore)/legalMoveScores[move][0]
            totalTriesSoFar += 1
    probs = {move: legalMoveScores[move][0] for move in legalMoves}
    return normalize(probs)

def choose_n_moves(moveScores, n, c, totalTriesSoFar):
    sorted_moves = sorted(moveScores, key=lambda move: moveScores[move][1] + c*(math.log(totalTriesSoFar)/moveScores[move][0])**.5, reverse=True)
    return sorted_moves[:n]

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

#return score in [-1, 1]
def evaluate_board(board: chess.Board):
    if board.one_king:
        return 1
    return engine.analyse(board, chess.engine.Limit(time=0.1))['score'].pov.wdl().expectation()