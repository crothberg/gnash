from chess import *
import chess.engine
from utils.types import *
from utils.util import *
from reconchess.utilities import revise_move
import math
import time

# import gevent

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

def get_move_dist_helper_2(testMoves, sampleFen, legalMoveScores, actuallyUs):
    sampleBoard = chess.Board(sampleFen)
    sampleBoard.clear_stack()
    sampleBoard.halfmove_clock = 0
    legalMovesOnBoard = set(sampleBoard.pseudo_legal_moves)
    #Take all the selected moves that are legal...
    legalTestMoves = set(testMoves).intersection(legalMovesOnBoard)
    #And all the revised moves from the rest...
    revisedMoves = dict()
    for move in set(testMoves).difference(legalMovesOnBoard):
        revisedMove = revise_move(sampleBoard, move) if move != chess.Move.null() else chess.Move.null()
        revisedMove = revisedMove or chess.Move.null()
        revisedMoves[move] = revisedMove
    legalTestMoves = legalTestMoves.union(revisedMoves.values())
    #Remove the null move (since we analyze it separately)
    if chess.Move.null() in legalTestMoves: legalTestMoves.remove(chess.Move.null())
    #Save the ones that would take the king for later...
    kingCaptures = king_capture_moves(sampleBoard)
    legalTestMoves = legalTestMoves.difference(kingCaptures)
    #As well as the ones that would leave the king in check...
    intoCheckMoves = into_check_moves(sampleBoard)
    legalTestMoves = legalTestMoves.difference(intoCheckMoves)
    #Remove the moves that are only pseudo-legal (since we analyze those separately)
    psuedoLegalOnly = legalTestMoves.difference(sampleBoard.legal_moves)
    legalTestMoves = legalTestMoves.difference(psuedoLegalOnly)
    #And get the base scores for the rest:
    baseScores = dict()
    try:
        if (chess.Move.null() in testMoves or chess.Move.null() in revisedMoves.values()) and chess.Move.null() not in intoCheckMoves: 
            # print("Made it here, found chess.Move.null() in either testMoves or revisedMoves")
            sampleBoardCopy = chess.Board(sampleFen)
            sampleBoardCopy.turn = not sampleBoardCopy.turn
            baseScores[chess.Move.null()] = analysisEngine.analyse(sampleBoardCopy, chess.engine.Limit(.05))['score'].pov(not sampleBoardCopy.turn).score(mate_score=153)
            assert baseScores[chess.Move.null()] != None
    except Exception as e:
        print(str(e))
        print(f"failed to analyze null move with board {sampleFen}, returning...")
        # input()
        return
    try:
        for move in psuedoLegalOnly:
            boardCopy = chess.Board(sampleFen)
            boardCopy.push(move)
            boardCopy.clear_stack()
            baseScores[move] = analysisEngine.analyse(boardCopy, chess.engine.Limit(.05))['score'].pov(not boardCopy.turn).score(mate_score=153)
    except Exception as e:
        print(str(e))
        print(f"failed to analyze pseudo-legal move with board {sampleFen}, returning...")
        # input()
        return
    if len(legalTestMoves) > 0:
        try:
            if len(kingCaptures) == 0:
                baseScores.update({x['pv'][0] : x['score'].pov(sampleBoard.turn).score(mate_score=153) for x in analysisEngine.analyse(sampleBoard, chess.engine.Limit(time=.015 * len(legalTestMoves)), multipv = len(legalTestMoves), root_moves = legalTestMoves)})
            else:
                for move in legalTestMoves:
                    boardCopy = chess.Board(sampleFen)
                    boardCopy.push(move)
                    boardCopy.clear_stack()
                    baseScores[move] = analysisEngine.analyse(boardCopy, chess.engine.Limit(.05))['score'].pov(not boardCopy.turn).score(mate_score=153)
        except Exception as e:
            print(str(e))
            print(f"failed in analyses with board {sampleFen}, returning...")
            print(intoCheckMoves)
            print(kingCaptures)
            print(legalTestMoves)
            # input()
            return
        if not len(legalTestMoves) <= len(baseScores) <= len(legalTestMoves) + 1 + len(psuedoLegalOnly):
            print(sampleFen)
            print(testMoves)
            print(baseScores, len(baseScores))
            print(legalTestMoves, len(legalTestMoves))
            print(legalTestMoves.difference(baseScores))
        assert len(legalTestMoves) <= len(baseScores) <= len(legalTestMoves) + 1
    for move, score in baseScores.items():
        isCapture = chess.Board.is_capture(sampleBoard, move)
        sampleBoard.push(move)
        if score == None:
            score = max(0, min(1, legalMoveScores[move][1] + random.random()))
        else:
            score = fix_base_score(score)
        #Minor penalty for taking a piece (and revealing information)
        if isCapture and actuallyUs:
            score = max(0, score - .05)
        if sampleBoard.is_check() and not isCapture and not sampleBoard.attackers(sampleBoard.turn, sampleBoard.king(not sampleBoard.turn)):
            score = min(1.15, score + (.35 if not actuallyUs else .05))
        if not sampleBoard.king(sampleBoard.turn):
            score += .75
        #Major penalty for moving our king past the second rank
        if actuallyUs and (2 <= chess.square_rank(sampleBoard.king(not sampleBoard.turn)) <= 5):
            score = min(0, score - .6)
        #Massive penalty for moving/leaving king in check on any board
        if sampleBoard.attackers(sampleBoard.turn, sampleBoard.king(not sampleBoard.turn)) and actuallyUs:
            score = -1        
        sampleBoard.pop()
        baseScores[move] = score

    for move in intoCheckMoves:
        baseScores[move] = -1
    for move in kingCaptures:
        baseScores[move] = 1
    for move, revisedMove in revisedMoves.items():
        if revisedMove not in baseScores:
            print(baseScores)
            print(intoCheckMoves)
            print(kingCaptures)
            print(sampleFen)
            print(testMoves)
            print(move)
        baseScores[move] = baseScores[revisedMove]
    for move, score in baseScores.items():
        if score >= 0:
            timesSampled, avgScore = legalMoveScores[move]
            totalScore = timesSampled*avgScore
            legalMoveScores[move][0] += 1
            legalMoveScores[move][1] = (totalScore + score)/legalMoveScores[move][0]
        else:
            legalMoveScores[move][0] = 1000
            legalMoveScores[move][1] = 0
def get_move_dist(boardDist, maxTime, movesToConsider = None, actuallyUs = False):
    legalMoves = set(get_pseudo_legal_moves(boardDist))
    if movesToConsider != None:
        legalMoves = legalMoves.intersection(movesToConsider)
    if maxTime <= .2:
        checkMoves = get_check_moves_dist(boardDist)
        if movesToConsider != None:
            checkMoves = checkMoves.intersection(movesToConsider)
        threatenMateMoves = get_threaten_mate_moves_dist(boardDist) if not actuallyUs else set()
        if movesToConsider != None:
            threatenMateMoves = threatenMateMoves.intersection(movesToConsider)
        numCheck = len(checkMoves.difference(threatenMateMoves))
        numThreatenMate = len(threatenMateMoves)
        numHarmless = len(legalMoves) - numCheck - numThreatenMate
        if numThreatenMate == 0 and numCheck > 0:
            return {move: (1/numCheck)*.6 if move in checkMoves else (1/numHarmless)*.4 for move in legalMoves}
        if numThreatenMate > 0 and numCheck == 0:
            return {move: (1/numThreatenMate)*.7 if move in threatenMateMoves else (1/numHarmless)*.3 for move in legalMoves}
        if numThreatenMate > 0 and numCheck > 0:
            probs = dict()
            for move in legalMoves:
                if move in threatenMateMoves: probs[move] = (1/numThreatenMate)*.4
                elif move in checkMoves: probs[move] = (1/numCheck)*.3
                else: probs[move] = (1/numHarmless)*.3
            assert abs(sum(probs.values()) - 1) < .001
            return probs
        return {move: 1/len(legalMoves) for move in legalMoves}
    if maxTime <= .7:
        return get_quick_move_dist(boardDist, maxTime, movesToConsider = movesToConsider, actuallyUs=actuallyUs)
    legalMoveScores = {move: [0.001, 0] for move in legalMoves} #[tries, averageScore]
    threatenMateMoves = get_threaten_mate_moves_dist(boardDist) if not actuallyUs else set()
    if movesToConsider != None:
        threatenMateMoves = threatenMateMoves.intersection(movesToConsider)
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
            testMoves = choose_n_moves(legalMoveScores, 5, 1, totalTriesSoFar, sampleFen)
            # time.sleep(.05)
            # if stockfishMove not in testMoves:
            #     testMoves += [stockfishMove]
        get_move_dist_helper_2(testMoves, sampleFen, legalMoveScores, actuallyUs)
        # allChunks = chunks(testMoves, NUM_ENGINES)
        # for moves in allChunks:
            # get_move_dist_helper(move, sampleFen, legalMoveScores, analysis_engines[i%len(analysis_engines)], actuallyUs)
            # gevent.joinall([gevent.spawn(get_move_dist_helper, move, sampleFen, legalMoveScores, engine, count, actuallyUs) for (move, engine) in zip(moves, analysis_engines)])
            # if len(list(allChunks))>1:
            #     time.sleep(.1)
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
    bestMove = max(probs, key=probs.get)
    bestMoveScore = probs[bestMove]
    topMoves = {bestMove}
    #If all top moves are the same score (e.g. because they're all lost)
    # use the stockfish method
    for move in sorted(probs, key=probs.get, reverse=True):
        if abs(bestMoveScore - probs[move]) < .05:
            topMoves.add(move)
        else:
            break
    if len(topMoves) > 1:
        probs = get_quick_move_dist(boardDist, maxTime=min(1.0, maxTime/2), movesToConsider = topMoves, actuallyUs=True)
        for move in legalMoves:
            if move not in probs:
                probs[move] = 0
        normalize(probs)
    # impossible_move_set = set(probs.keys()).difference(set(move_actions(chess.Board(list(boardDist.keys())[0]))))
    # It should be okay for the opponent to attempt an impossible move, no? Why do we raise this error?
    # if len(impossible_move_set) > 1:# and len(boardDist) < 10:
    #     print('IMPOSSIBLE MOVE SET:', impossible_move_set)
    #     assert False
    # print(probs)
    # print(f"Time after iters was {time.time()-t}")
    # print(actuallyUs, probs)
    return probs

def get_quick_move_dist(boardDist, maxTime, movesToConsider = None, actuallyUs = False):
    startTime = time.time()
    legalMoves = get_pseudo_legal_moves(boardDist)
    if movesToConsider != None:
        legalMoves = legalMoves.intersection(movesToConsider)
    timePerMove = .1
    probs = {move: (.2*(maxTime/timePerMove))/len(legalMoves) for move in legalMoves}

    if movesToConsider == None:
        checkMoves = get_check_moves_dist(boardDist) if not actuallyUs else get_silent_check_moves_dist(boardDist)
        for move in checkMoves:
            probs[move] += (1.5 if not actuallyUs else .05)

        threatenMateMoves = get_threaten_mate_moves_dist(boardDist)
        for move in threatenMateMoves:
            probs[move] += (2 if not actuallyUs else .3)

    def update_probs(board, engine):
        move = get_stockfish_move(board, timePerMove, engine, movesToConsider=legalMoves, actuallyUs=actuallyUs)
        if move is not None:
            if move not in probs:
                print(board)
                print(probs)
                print(move)
                probs[move] = 3 #this is a checkmate
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

def get_stockfish_move(fen : str, maxTime, engine, movesToConsider=None, actuallyUs=False) -> Move:
    board = chess.Board(fen)
    if actuallyUs:
        enemy_king_square = board.king(not board.turn)
        if enemy_king_square:
            # if there are any ally pieces that can take king, execute one of those moves
            enemy_king_attackers = board.attackers(board.turn, enemy_king_square)
            if enemy_king_attackers:
                attacker_square = enemy_king_attackers.pop()
                return chess.Move(attacker_square, enemy_king_square)
    if movesToConsider != None:
        move = engine.play(board, chess.engine.Limit(time=maxTime), root_moves = movesToConsider).move
    else:
        move = engine.play(board, chess.engine.Limit(time=maxTime)).move
    return move