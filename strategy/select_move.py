from chess import *
import chess.engine
from utils.types import *
from utils.util import *
from reconchess.utilities import revise_move
import math
import time

import gevent

def select_move(beliefState, maxTime) -> Move:
    if len(beliefState.myBoardDist) == 1:
        return moving_engines[0].play(chess.Board(list(beliefState.myBoardDist.keys())[0]), chess.engine.Limit(time=min(maxTime, 1.0))).move
    moveDist = get_move_dist(beliefState.myBoardDist, maxTime=5)
    topMoves = sorted(moveDist, key=moveDist.get, reverse=True)[:5]
    print([(move, moveDist[move]) for move in topMoves])
    move = topMoves[0]
    print(moveDist[move])
    return move
    # return select_move_from_dist(beliefState.myBoardDist, maxTime)

def select_move_from_dist(boardDist, maxTime):
    move = sample(get_move_dist(boardDist, maxTime))
    return move

def get_move_dist_helper(move, sampleFen, legalMoveScores, engine):
    sampleBoard = chess.Board(sampleFen)
    assert move in get_all_moves(sampleBoard)
    timesSampled, avgScore = legalMoveScores[move]
    totalScore = timesSampled*avgScore
    revisedMove = revise_move(sampleBoard, move) if move != chess.Move.null() else chess.Move.null()
    revisedMove = revisedMove or chess.Move.null()
    isCapture = chess.Board.is_capture(sampleBoard, revisedMove) if revisedMove is not None else False
    sampleBoard.push(revisedMove if revisedMove is not None else chess.Move.null())
    sampleBoard.halfmove_clock = 0
    newBoardScore = evaluate_board(sampleBoard, engine)
    #Minor penalty for taking a piece (and revealing information)
    if isCapture:
        newBoardScore = max(0, newBoardScore - .05)
    if sampleBoard.is_check() and not isCapture and not sampleBoard.attackers(sampleBoard.turn, sampleBoard.king(not sampleBoard.turn)):
        newBoardScore = min(1.15, newBoardScore + .4)
    if not sampleBoard.king(sampleBoard.turn):
        newBoardScore += .75
    legalMoveScores[move][0] += 1
    legalMoveScores[move][1] = (totalScore + newBoardScore)/legalMoveScores[move][0]
def get_move_dist(boardDist, maxTime):
    legalMoves = get_pseudo_legal_moves(boardDist)
    if maxTime <= .05:
        return {move: 1/len(legalMoves) for move in legalMoves}
    if maxTime <= .25:
        return get_quick_move_dist(boardDist, maxTime)
    legalMoveScores = {move: [0.001, 0] for move in legalMoves} #[tries, averageScore]
    startTime = time.time()
    totalTriesSoFar = 0
    while time.time() - startTime < maxTime:
        sampleFen = sample(boardDist)
        if totalTriesSoFar == 0:
            testMoves = set(get_all_moves(chess.Board(sampleFen))).intersection(legalMoveScores)
        else:
            testMoves = choose_n_moves(legalMoveScores, NUM_ENGINES, 1, totalTriesSoFar, sampleFen)
            # time.sleep(.05)
            # stockfishMove = get_stockfish_move(sampleFen, maxTime=.1, engine=oneMoreEngine)
            # if stockfishMove not in testMoves:
            #     testMoves += [stockfishMove]
        gevent.joinall([gevent.spawn(get_move_dist_helper, move, sampleFen, legalMoveScores, engine) for (move, engine) in zip(testMoves, analysis_engines)])
        totalTriesSoFar += len(testMoves)
    # print(totalTriesSoFar, totalTriesSoFar/(time.time()-startTime), time.time()-startTime)
    # print("Raw scores:")
    # print(legalMoveScores)
    probs = normalize({move: legalMoveScores[move][1]**8 for move in legalMoves}, adjust=True)
    topMoves = sorted(probs, key=probs.get, reverse=True)[:5]
    #If all boards are the same score (e.g. because they're all lost)
    # use the stockfish method
    if all(abs(probs[topMoves[0]] - probs[move]) < .01 for move in topMoves):
        # print(legalMoveScores)
        # print(probs)
        return get_quick_move_dist(boardDist, maxTime=maxTime/2)
    # impossible_move_set = set(probs.keys()).difference(set(move_actions(chess.Board(list(boardDist.keys())[0]))))
    # It should be okay for the opponent to attempt an impossible move, no? Why do we raise this error?
    # if len(impossible_move_set) > 1:# and len(boardDist) < 10:
    #     print('IMPOSSIBLE MOVE SET:', impossible_move_set)
    #     assert False
    # print(probs)
    return probs

def get_quick_move_dist(boardDist, maxTime):
    legalMoves = get_pseudo_legal_moves(boardDist)
    timePerMove = .1
    probs = {move: (.2*(maxTime/timePerMove))/len(legalMoves) for move in legalMoves}

    def update_probs(board, engine):
        probs[get_stockfish_move(board, timePerMove, engine)] += 1
    startTime = time.time()
    while time.time()-startTime < maxTime:
        sampleBoards = sample(boardDist, NUM_ENGINES)
        gevent.joinall([gevent.spawn(update_probs, board, engine) for board, engine in zip(sampleBoards, moving_engines)])
    # print(time.time()-startTime, numSamples)
    return normalize(probs, adjust=True)

def choose_n_moves(moveScores, n, c, totalTriesSoFar, fen):
    board = chess.Board(fen)
    allMoves = get_all_moves(board)
    # moveScores = {k: v for (k, v) in moveScores.items() if k in legalMoves}
    sorted_moves = sorted(moveScores, key=lambda move: -100 if move not in allMoves else (moveScores[move][1] + c*(math.log(totalTriesSoFar)/moveScores[move][0])**.5), reverse=True)
    return sorted_moves[:n]

def get_stockfish_move(fen : str, maxTime, engine) -> Move:
    board = chess.Board(fen)
    enemy_king_square = board.king(not board.turn)
    if enemy_king_square:
        # if there are any ally pieces that can take king, execute one of those moves
        enemy_king_attackers = board.attackers(board.turn, enemy_king_square)
        if enemy_king_attackers:
            attacker_square = enemy_king_attackers.pop()
            return chess.Move(attacker_square, enemy_king_square)
    move = engine.play(board, chess.engine.Limit(time=maxTime)).move
    return move