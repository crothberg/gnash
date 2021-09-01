import os
from chess import *
import chess.engine
from utils.types import *
from utils.util import *
from reconchess.utilities import revise_move
import math
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
engine = chess.engine.SimpleEngine.popen_uci(stockfish_path, setpgrp=True)
print('Stockfish engine initialized..')

def select_move(beliefState, maxTime) -> Move:
    return select_move_from_dist(beliefState.myBoardDist, maxTime)

def select_move_from_dist(boardDist, maxTime):
    move = sample(get_move_dist(boardDist, maxTime))
    return move

def get_move_dist(boardDist, maxTime):
    legalMoves = get_pseudo_legal_moves(boardDist)
    if maxTime <= .1:
        return {move: 1/len(legalMoves) for move in legalMoves}
    if maxTime <= .5:
        return get_quick_move_dist(boardDist, maxTime)
    legalMoveScores = {move: [0.001, 0] for move in legalMoves} #[tries, averageScore]
    startTime = time.time()
    totalTriesSoFar = 0
    while time.time() - startTime < maxTime:
        sampleFen = sample(boardDist)
        if totalTriesSoFar == 0:
            testMoves = set(get_all_moves(chess.Board(sampleFen))).intersection(legalMoveScores)
        else:
            testMoves = choose_n_moves(legalMoveScores, 10, 1, totalTriesSoFar, sampleFen)
            time.sleep(.1)
            stockfishMove = get_stockfish_move(sampleFen, maxTime=.1)
            if stockfishMove not in testMoves:
                testMoves += [stockfishMove]
        for move in testMoves:
            sampleBoard = chess.Board(sampleFen)
            assert move in get_all_moves(sampleBoard)
            timesSampled, avgScore = legalMoveScores[move]
            totalScore = timesSampled*avgScore
            revisedMove = revise_move(sampleBoard, move) if move != chess.Move.null() else chess.Move.null()
            revisedMove = revisedMove or chess.Move.null()
            # print('SAMPLE BOARD:\n',sampleBoard)
            # print('MOVE',move)
            # print(move not in {chess.Move.null(), None})
            sampleBoard.push(revisedMove if revisedMove is not None else chess.Move.null())
            newBoardScore = evaluate_board(sampleBoard)
            legalMoveScores[move][0] += 1
            legalMoveScores[move][1] = (totalScore + newBoardScore)/legalMoveScores[move][0]
            totalTriesSoFar += 1
    probs = normalize({move: legalMoveScores[move][1]**8 for move in legalMoves}, adjust=True)
    impossible_move_set = set(probs.keys()).difference(set(move_actions(chess.Board(list(boardDist.keys())[0]))))
    # It should be okay for the opponent to attempt an impossible move, no? Why do we raise this error?
    # if len(impossible_move_set) > 1:# and len(boardDist) < 10:
    #     print('IMPOSSIBLE MOVE SET:', impossible_move_set)
    #     assert False
    return probs

def get_quick_move_dist(boardDist, maxTime):
    legalMoves = get_pseudo_legal_moves(boardDist)
    timePerMove = .1
    numSamples = math.ceil(maxTime/(timePerMove*1.5))
    probs = {move: (numSamples*.3)/len(legalMoves) for move in legalMoves}
    for _ in range(numSamples):
        board = sample(boardDist)
        time.sleep(.05)
        probs[get_stockfish_move(board, timePerMove)] += 1
    return normalize(probs)

def choose_n_moves(moveScores, n, c, totalTriesSoFar, fen):
    board = chess.Board(fen)
    allMoves = get_all_moves(board)
    # moveScores = {k: v for (k, v) in moveScores.items() if k in legalMoves}
    sorted_moves = sorted(moveScores, key=lambda move: -100 if move not in allMoves else (moveScores[move][1] + c*(math.log(totalTriesSoFar)/moveScores[move][0])**.5), reverse=True)
    return sorted_moves[:n]

def get_stockfish_move(fen : str, maxTime) -> Move:
    board = chess.Board(fen)
    enemy_king_square = board.king(not board.turn)
    if enemy_king_square:
        # if there are any ally pieces that can take king, execute one of those moves
        enemy_king_attackers = board.attackers(board.turn, enemy_king_square)
        if enemy_king_attackers:
            attacker_square = enemy_king_attackers.pop()
            return chess.Move(attacker_square, enemy_king_square)
    tries = 0
    while tries<1:
        # try:
        tries += 1
        move = engine.play(board, chess.engine.Limit(time=maxTime)).move
            # print(type(engine))
            # engine.quit()
            # exit()
        # except:
            # print('HERE', type(engine))
            # engine.quit()
            # print("Stockfish broke. Trying again...")
            # engine = chess.engine.SimpleEngine.popen_uci(stockfish_path, setpgrp=True, timeout=1)
    # return chess.Move.null()
    return move

#return score in [0, 1]
def evaluate_board(board: chess.Board):
    board.clear_stack()
    if board.king(board.turn) == None:
        return 1
    baseScore = 0
    try:
        baseScore += engine.analyse(board, chess.engine.Limit(time=0.05))['score'].pov(not board.turn).wdl().expectation()
    except:
        baseScore += random.random()
    if board.is_check():
        baseScore += .2
    return min(1, baseScore)