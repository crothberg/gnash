from chess import *
import chess.engine
from utils.types import *
from utils.util import *
from reconchess.utilities import revise_move
import math
import time

import gevent

##TODO: Always promote to queen or knight
def select_move(beliefState, maxTime) -> Move:
    if len(beliefState.myBoardDist) == 1:
        board = chess.Board(list(beliefState.myBoardDist.keys())[0])
        enemy_king_square = board.king(not board.turn)
        if enemy_king_square:
            # if there are any ally pieces that can take king, execute one of those moves
            enemy_king_attackers = board.attackers(board.turn, enemy_king_square)
            if enemy_king_attackers:
                attacker_square = enemy_king_attackers.pop()
                return chess.Move(attacker_square, enemy_king_square)
        return okayJustOneMore.play(board, chess.engine.Limit(time=min(maxTime, 1.0))).move
    moveDist = get_move_dist(beliefState.myBoardDist, maxTime=maxTime, actuallyUs=True)
    topMoves = sorted(moveDist, key=moveDist.get, reverse=True)[:5]
    print([(move, moveDist[move]) for move in topMoves])
    move = topMoves[0]
    print(moveDist[move])
    if move != None and move.promotion != None and move.promotion != chess.KNIGHT:
        move.promotion = chess.QUEEN
    return move
    # return select_move_from_dist(beliefState.myBoardDist, maxTime)

# def select_move_from_dist(boardDist, maxTime):
#     move = sample(get_move_dist(boardDist, maxTime))
#     return move

def get_move_dist_helper(move, sampleFen, legalMoveScores, engine, count, actuallyUs=False):
    sampleBoard = chess.Board(sampleFen)
    assert move in get_all_moves(sampleBoard)
    timesSampled, avgScore = legalMoveScores[move]
    totalScore = timesSampled*avgScore
    revisedMove = revise_move(sampleBoard, move) if move != chess.Move.null() else chess.Move.null()
    revisedMove = revisedMove or chess.Move.null()
    isCapture = chess.Board.is_capture(sampleBoard, revisedMove) if revisedMove is not None else False
    sampleBoard.push(revisedMove if revisedMove is not None else chess.Move.null())
    sampleBoard.halfmove_clock = 0
    newBoardScore = evaluate_board(sampleBoard, engine, time=(.025 if count == 0 else .05))
    if newBoardScore == None:
        newBoardScore = max(0, min(1, legalMoveScores[move][1] + random.random()))
    #Minor penalty for taking a piece (and revealing information)
    if isCapture and actuallyUs:
        newBoardScore = max(0, newBoardScore - .05)
    if sampleBoard.is_check() and not isCapture and not sampleBoard.attackers(sampleBoard.turn, sampleBoard.king(not sampleBoard.turn)):
        newBoardScore = min(1.15, newBoardScore + (.4 if not actuallyUs else .05))
    if not sampleBoard.king(sampleBoard.turn):
        newBoardScore += .75
    #Major penalty for moving our king past the second rank
    if actuallyUs and (2 <= chess.square_rank(sampleBoard.king(not sampleBoard.turn)) <= 5):
        newBoardScore = min(0, newBoardScore - .6)
    legalMoveScores[move][0] += 1
    #Massive penalty for moving/leaving king in check on any board
    if sampleBoard.attackers(sampleBoard.turn, sampleBoard.king(not sampleBoard.turn)) and actuallyUs:
        legalMoveScores[move][0] = 100
        legalMoveScores[move][1] = 0
    else:
        legalMoveScores[move][1] = (totalScore + newBoardScore)/legalMoveScores[move][0]
def get_move_dist(boardDist, maxTime, actuallyUs = False):
    legalMoves = get_pseudo_legal_moves(boardDist)
    if maxTime <= .2:
        checkMoves = get_check_moves_dist(boardDist)
        threatenMateMoves = get_threaten_mate_moves_dist(boardDist) if not actuallyUs else set()
        numCheck = len(checkMoves.difference(threatenMateMoves))
        numThreatenMate = len(threatenMateMoves)
        numHarmless = len(legalMoves) - numCheck - numThreatenMate
        if numThreatenMate == 0 and numCheck > 0:
            return {move: (1/numCheck)*.8 if move in checkMoves else (1/numHarmless)*.2 for move in legalMoves}
        if numThreatenMate > 0 and numCheck == 0:
            return {move: (1/numThreatenMate)*.8 if move in threatenMateMoves else (1/numHarmless)*.2 for move in legalMoves}
        if numThreatenMate > 0 and numCheck > 0:
            probs = dict()
            for move in legalMoves:
                if move in threatenMateMoves: probs[move] = (1/numThreatenMate)*.5
                elif move in checkMoves: probs[move] = (1/numCheck)*.4
                else: probs[move] = (1/numHarmless)*.1
            assert abs(sum(probs.values()) - 1) < .001
            return probs
        return {move: 1/len(legalMoves) for move in legalMoves}
    if maxTime <= .7:
        return get_quick_move_dist(boardDist, maxTime, actuallyUs=actuallyUs)
    legalMoveScores = {move: [0.001, 0] for move in legalMoves} #[tries, averageScore]
    threatenMateMoves = get_threaten_mate_moves_dist(boardDist) if not actuallyUs else set()
    for move in threatenMateMoves:
        legalMoveScores[move][1] = 1
    fenCounts = {fen: 1 for fen in boardDist}
    startTime = time.time()
    totalTriesSoFar = 0
    count = 0
    lastIterTime = 0
    while (time.time() - startTime) < (maxTime - lastIterTime):
        # print(time.time()-startTime, maxTime - lastIterTime)
        iterStartTime = time.time()
        sampleFen = choose_1_board(fenCounts, boardDist)
        # print(f"Sampled board {sampleFen}")
        if totalTriesSoFar == 0:
            testMoves = list(set(get_all_moves(chess.Board(sampleFen))).intersection(legalMoveScores))
        else:
            testMoves = choose_n_moves(legalMoveScores, NUM_ENGINES, 1, totalTriesSoFar, sampleFen)
            # time.sleep(.05)
            # stockfishMove = get_stockfish_move(sampleFen, maxTime=.1, engine=oneMoreEngine)
            # if stockfishMove not in testMoves:
            #     testMoves += [stockfishMove]
        allChunks = chunks(testMoves, NUM_ENGINES)
        for moves in allChunks:
            # get_move_dist_helper(move, sampleFen, legalMoveScores, analysis_engines[i%len(analysis_engines)], actuallyUs)
            gevent.joinall([gevent.spawn(get_move_dist_helper, move, sampleFen, legalMoveScores, engine, count, actuallyUs) for (move, engine) in zip(moves, analysis_engines)])
            if len(list(allChunks))>1:
                time.sleep(.1)
        totalTriesSoFar += len(testMoves)
        # if count == 1: print(f"First iter took {time.time() - iterStartTime} seconds with maxTime {maxTime}")
        count += 1
        if count>1: lastIterTime = time.time() - iterStartTime
        # print(lastIterTime if count>1 else time.time()-iterStartTime)
    # print(f"Did {count} iterations in getMoveDist with {maxTime} seconds")
    # print(totalTriesSoFar, totalTriesSoFar/(time.time()-startTime), time.time()-startTime)
    # print("Raw scores:")
    # print(legalMoveScores)
    t = time.time()
    probs = normalize({move: legalMoveScores[move][1]**8 for move in legalMoves}, adjust=True)
    # print(probs)
    topMoves = sorted(probs, key=probs.get, reverse=True)[:5]
    #If all top moves are the same score (e.g. because they're all lost)
    # use the stockfish method
    if all(abs(probs[topMoves[0]] - probs[move]) < .03 for move in topMoves):
        # print("Using extra time for get_quick_move_dist...")
        # print(legalMoveScores)
        # print(probs)
        probs = get_quick_move_dist(boardDist, maxTime=min(1.0, maxTime/2), actuallyUs=True)
    # impossible_move_set = set(probs.keys()).difference(set(move_actions(chess.Board(list(boardDist.keys())[0]))))
    # It should be okay for the opponent to attempt an impossible move, no? Why do we raise this error?
    # if len(impossible_move_set) > 1:# and len(boardDist) < 10:
    #     print('IMPOSSIBLE MOVE SET:', impossible_move_set)
    #     assert False
    # print(probs)
    # print(f"Time after iters was {time.time()-t}")
    return probs

def get_quick_move_dist(boardDist, maxTime, actuallyUs = False):
    startTime = time.time()
    legalMoves = get_pseudo_legal_moves(boardDist)
    timePerMove = .1
    probs = {move: (.2*(maxTime/timePerMove))/len(legalMoves) for move in legalMoves}

    checkMoves = get_check_moves_dist(boardDist) if not actuallyUs else get_silent_check_moves_dist(boardDist)
    for move in checkMoves:
        probs[move] += (2.5 if not actuallyUs else .05)

    threatenMateMoves = get_threaten_mate_moves_dist(boardDist)
    for move in threatenMateMoves:
        probs[move] += (3.5 if not actuallyUs else .3)

    def update_probs(board, engine):
        move = get_stockfish_move(board, timePerMove, engine)
        if move is not None:
            probs[move] += 1
    movingEngineIndex = 0
    while time.time()-startTime < maxTime - timePerMove:
        sampleBoard = sample(boardDist)
        update_probs(sampleBoard, moving_engines[movingEngineIndex])
        movingEngineIndex = (movingEngineIndex + 1) % len(moving_engines)
        # gevent.joinall([gevent.spawn(update_probs, board, engine) for board, engine in zip(sampleBoards, moving_engines)])
    # print(time.time()-startTime, numSamples)
    return normalize(probs, adjust=True)

def choose_n_moves(moveScores, n, c, totalTriesSoFar, fen):
    board = chess.Board(fen)
    allMoves = get_all_moves(board)
    # moveScores = {k: v for (k, v) in moveScores.items() if k in legalMoves}
    sorted_moves = sorted(moveScores, key=lambda move: -100 if move not in allMoves else (moveScores[move][1] + c*(math.log(totalTriesSoFar)/moveScores[move][0])**.5), reverse=True)
    return sorted_moves[:n]

def choose_1_board(fenCounts, dist):
    fen = max(dist, key=lambda x: dist[x]/(fenCounts[x]**1.5))
    fenCounts[fen] += 1
    # print(f"sampled board {fen}")
    return fen

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