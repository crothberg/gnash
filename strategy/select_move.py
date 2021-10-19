from chess import *
import chess.engine
from utils.types import *
from utils.util import *
import utils.scoring_utils as scorer
import utils.engine_utils as engines
from reconchess.utilities import revise_move
import time
from statistics import *
import threading

def get_move_dist_helper_2(testMoves, sampleFen, sampleFenProb, legalMoveScores, actuallyUs, gambleFactor, movesSeenOnBoard, giveFrivChecks):
    sampleBoard = chess.Board(sampleFen)
    sampleBoard.clear_stack()
    sampleBoard.halfmove_clock = 0
    legalMovesOnBoard = get_pseudo_legal_moves({sampleFen})
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
    ##TODO: Must also take out moves that would leave them in checkmate
    #And get the base scores for the rest:
    baseScores = dict()
    try:
        if (chess.Move.null() in testMoves or chess.Move.null() in revisedMoves.values()) and chess.Move.null() not in intoCheckMoves: 
            # print("Made it here, found chess.Move.null() in either testMoves or revisedMoves")
            sampleBoardCopy = chess.Board(sampleFen)
            sampleBoardCopy.turn = not sampleBoardCopy.turn
            sampleBoardCopy.clear_stack()
            nullScore = scorer.score(sampleBoardCopy, .01, not sampleBoardCopy.turn)
            # if actuallyUs: print(f"Null score for board {sampleFen}: {nullScore}")
            baseScores[chess.Move.null()] = nullScore
    except Exception as e:
        print(str(e))
        print(f"failed to analyze null move with board {sampleFen}, returning...")
        # input()
        return
    lastTriedMove = None
    try:
        for move in psuedoLegalOnly:
            assert move not in intoCheckMoves
            lastTriedMove = move
            boardCopy = chess.Board(sampleFen)
            boardCopy.push(move)
            boardCopy.clear_stack()
            moveScore = scorer.score(boardCopy, .01, not boardCopy.turn)
            baseScores[move] = moveScore
    except Exception as e:
        print(str(e))
        print(psuedoLegalOnly)
        print(lastTriedMove)
        print(f"failed to analyze pseudo-legal move with board {sampleFen}, returning...")
        # input()
        return
    if len(legalTestMoves) > 0:
        wasInCheck = chess.Board(sampleFen).is_check()
        for move in legalTestMoves:
            boardCopy = chess.Board(sampleFen)
            isCapture = real_capture_square_of_move(boardCopy, move) != None
            boardCopy.push(move)
            boardCopy.clear_stack()
            try:
                primaryScore = scorer.score(boardCopy, .01, not boardCopy.turn)
            except:
                print(f"failed in primary analysis with board {sampleFen}, and move {move}, returning...")
                return
            gambleAmount = gambleFactor * .5
            if not isCapture and not wasInCheck and gambleAmount > 0:
                if boardCopy.is_check() and not giveFrivChecks:
                    gambleAmount = .001
                boardCopy.turn = not boardCopy.turn
                boardCopy.ep_square = None
                boardCopy.clear_stack()
                try:
                    secondaryScore = scorer.score(boardCopy, .01, boardCopy.turn)
                except:
                    print(f"failed in secondary analysis with board {boardCopy.fen()}, after move {move}, returning...")
                # print(f"Primary score for move {move} on board {sampleFen}: {primaryScore}")
                # print(f"Secondary score for move {move} on board {sampleFen}: {secondaryScore}")
                baseScores[move] = (1-gambleAmount)*primaryScore + (gambleAmount)*secondaryScore
            else:
                baseScores[move] = primaryScore                    

        if not len(legalTestMoves) <= len(baseScores) <= len(legalTestMoves) + 1 + len(psuedoLegalOnly):
            print(sampleFen)
            print(testMoves)
            print(psuedoLegalOnly)
            print(baseScores, len(baseScores))
            print(legalTestMoves, len(legalTestMoves))
            print(legalTestMoves.difference(baseScores))
        assert len(legalTestMoves) <= len(baseScores) <= len(legalTestMoves) + 1 + len(psuedoLegalOnly)
    standardDev = stdev(baseScores.values()) if len(baseScores) >= 2 else 1
    for move, score in baseScores.items():
        sampleBoard.push(move)
        # #Minor penalty for taking a piece (and revealing information)
        # if isCapture and actuallyUs:
        #     score = max(0, score - .01)
        # if move in silentCheckMoves:
        #     score = min(1, score + (3.5*standardDev if not actuallyUs else 0))
        # if move in queenCheckMoves:
        #     score = min(1, score + (2*standardDev if not actuallyUs else .4*standardDev))
        if not sampleBoard.king(sampleBoard.turn):
            # score += .75
            score = 1
        #Major penalty for moving our king past the second rank
        if actuallyUs and (2 <= chess.square_rank(sampleBoard.king(not sampleBoard.turn)) <= 5):
            score = max(0, score - 2*standardDev)
        #Massive penalty for moving/leaving king in check on any board
        if sampleBoard.attackers(sampleBoard.turn, sampleBoard.king(not sampleBoard.turn)):
            score = -1
        sampleBoard.pop()
        baseScores[move] = score

    for move in intoCheckMoves:
        baseScores[move] = -1
    for move in kingCaptures:
        baseScores[move] = 1
        # legalMoveScores[move][0] = 1
    for move, revisedMove in revisedMoves.items():
        if revisedMove not in baseScores:
            print(baseScores)
            print(intoCheckMoves)
            print(kingCaptures)
            print(sampleFen)
            print(testMoves)
            print(move)
        baseScores[move] = baseScores[revisedMove]
    # sortedMoves = sorted(baseScores, key=baseScores.get)
    # print(sampleFen)
    # print([(move, baseScores[move]) for move in sortedMoves])
    # input()
    # print(sampleFen)
    # print(baseScores)
    # print()
    for move, score in baseScores.items():
        if move in movesSeenOnBoard[sampleFen]:
            continue
        movesSeenOnBoard[sampleFen].add(move)
        if score >= 0:
            if legalMoveScores[move] == 100:
                legalMoveScores[move] = score * (sampleFenProb**3)
            else:
                legalMoveScores[move] += score * (sampleFenProb**3)
        else:
            legalMoveScores[move] = 0
            for board in movesSeenOnBoard:
                movesSeenOnBoard[board].add(move)
        
def get_move_dist(boardDist, maxTime, actuallyUs, gambleFactor, giveFrivChecks, movesToConsider = None):
    # print(f"Getting move dist with time {maxTime}")
    # t = time.time()
    legalMoves = set(get_pseudo_legal_moves(boardDist))
    if movesToConsider != None:
        legalMoves = legalMoves.intersection(movesToConsider)
    if maxTime <= .2:
        return get_very_quick_move_dist(boardDist, actuallyUs, legalMoves, movesToConsider)
    if maxTime <= .5:
        return get_quick_move_dist(boardDist, maxTime, movesToConsider = movesToConsider, actuallyUs=actuallyUs)
    legalMoveScores = {move: 100 for move in legalMoves}
    movesSeenOnBoard = {board: set() for board in boardDist}
    def getMovePlayLikelihoods():
        likelihoods = {}
        for move in legalMoveScores:
            totalSeen = sum([boardDist[board]**3 for board in boardDist if move in get_all_moves(chess.Board(board)) and move in movesSeenOnBoard[board]])
            likelihoods[move] = (legalMoveScores[move]/totalSeen) if totalSeen > 0 else 0
        return normalize(likelihoods, adjust=True, giveToZeros=.01, raiseNum=4)
    def getMoveExploreLikelihoods():
        likelihoods = {}
        for move in legalMoveScores:
            totalSeen = sum([boardDist[board]**3 for board in boardDist if move in get_all_moves(chess.Board(board)) and move in movesSeenOnBoard[board]])
            likelihoods[move] = (legalMoveScores[move]/totalSeen) if totalSeen > 0 else 100
        return normalize(likelihoods, adjust=True, giveToZeros=.01)
    def nextBoardAndMoves(n=20):
        moveLikelihoods = getMoveExploreLikelihoods()
        # print(legalMoveScores)
        # print(moveLikelihoods)
        boardExploreScores = {board: 0 for board in boardDist}
        for fen in boardDist:
            percentUnexplored = 0
            b = chess.Board(fen)
            allMoves = set(get_all_moves(b)).intersection(legalMoves)
            for move in allMoves:
                if move not in movesSeenOnBoard[fen]: percentUnexplored += moveLikelihoods[move]
            boardExploreScores[fen] = percentUnexplored*boardDist[fen]
        fenToExplore = max(boardExploreScores, key=boardExploreScores.get)
        if boardExploreScores[fenToExplore] < 0.0000001:
            return None, None, True
        moves = sorted(moveLikelihoods, key=lambda move: -1 if (move in movesSeenOnBoard[fenToExplore] or move not in get_all_moves(chess.Board(fenToExplore))) else moveLikelihoods[move], reverse=True)
        moves = list(move for move in list(moves)[:n] if (move not in movesSeenOnBoard[fenToExplore] and move in get_all_moves(chess.Board(fenToExplore))))
        # print(fenToExplore)
        # print(moves)
        # input()
        return fenToExplore, moves, False

    startTime = time.time()
    count = 0
    lastIterTime = 0
    while (time.time() - startTime) < (maxTime - lastIterTime) or max(legalMoveScores.values())>1:
        # print(max(legalMoveScores.values()))
        iterStartTime = time.time()
        sampleFen, testMoves, terminate = nextBoardAndMoves()
        if terminate:
            break
        # print(f"Exploring sampleFen {sampleFen}")
        # print(f"Exploring moves {testMoves}")
        # if totalTriesSoFar == 0:
        #     testMoves = list(set(get_all_moves(chess.Board(sampleFen))).intersection(legalMoveScores))
        # else:
        #     testMoves = choose_n_moves(legalMoveScores, 5, 1, totalTriesSoFar, sampleFen)
        get_move_dist_helper_2(testMoves, sampleFen, boardDist[sampleFen], legalMoveScores, actuallyUs, gambleFactor, movesSeenOnBoard, giveFrivChecks)
        count += 1
        if count>1: lastIterTime = time.time() - iterStartTime
    # print(legalMoveScores)
    # probs = normalize({move: legalMoveScores[move][1] for move in legalMoves}, adjust=True, raiseNum=5, giveToZeros=.005)
    # probs = normalize({move: legalMoveScores[move] for move in legalMoves}, adjust=True, raiseNum=4, giveToZeros=.005)
    probs = getMovePlayLikelihoods()
    if actuallyUs: 
        for move in list(sorted(probs, key=probs.get))[-7:]:
            print(f"{move}: {probs[move]}")
    #if actually us, enter a tie-breaking process if necessary
    if actuallyUs:
        bestMove = max(probs, key=probs.get)
        bestMoveScore = probs[bestMove]
        topMoves = {bestMove}
        #If all top moves are the same score (e.g. because they're all lost)
        # use the stockfish method
        for move in sorted(probs, key=probs.get, reverse=True):
            if abs(bestMoveScore - probs[move]) <.0000001: #< .05:
                topMoves.add(move)
            else:
                break
        if len(topMoves) > 1:
            print("Breaking tie by using stockfish with the following moves:")
            print(list((move, legalMoveScores[move], probs[move]) for move in topMoves))
            probs = get_quick_move_dist(boardDist, maxTime=min(1.0, maxTime/2), movesToConsider = topMoves, actuallyUs=True)
            for move in legalMoves:
                if move not in probs:
                    probs[move] = 0
            normalize(probs)
    # print(time.time()-t)
    return probs

def get_quick_move_dist(boardDist, maxTime, movesToConsider = None, actuallyUs = False):
    startTime = time.time()
    legalMoves = get_pseudo_legal_moves(boardDist)
    if movesToConsider != None:
        legalMoves = legalMoves.intersection(movesToConsider)
    timePerMove = .1
    probs = {move: (.2*(maxTime/timePerMove))/len(legalMoves) for move in legalMoves}

    if movesToConsider == None:
        checkMoves, _ = get_check_and_queenCheck_moves_dist(boardDist) if not actuallyUs else get_silent_check_and_queenCheck_moves_dist(boardDist)
        for move in checkMoves:
            probs[move] += (1 if not actuallyUs else .05)
        # for move in queenCheckMoves:
        #     probs[move] += (.5 if not actuallyUs else .1)

        threatenMateMoves = get_threaten_mate_moves_dist(boardDist)
        for move in threatenMateMoves:
            probs[move] += (1 if not actuallyUs else .3)

    def update_probs(board):
        move = get_stockfish_move(board, timePerMove, movesToConsider=legalMoves, actuallyUs=actuallyUs)
        if move is not None:
            if move not in probs:
                print(board)
                print(probs)
                print(move)
                if actuallyUs: 
                    probs[move] = 2 #this is a king capture
                return
            probs[move] += 1
    while time.time()-startTime < maxTime - timePerMove:
        sampleBoard = sample(boardDist)
        update_probs(sampleBoard)
    return normalize(probs, adjust=True)

def get_very_quick_move_dist(boardDist, actuallyUs, legalMoves, movesToConsider):
    # return {move: 1/len(legalMoves) for move in legalMoves}
    checkMoves, _ = get_silent_check_and_queenCheck_moves_dist(boardDist)
    if movesToConsider != None:
        checkMoves = checkMoves.intersection(movesToConsider)
    threatenMateMoves = get_threaten_mate_moves_dist(boardDist) if not actuallyUs else set()
    if movesToConsider != None:
        threatenMateMoves = threatenMateMoves.intersection(movesToConsider)
    numCheck = len(checkMoves.difference(threatenMateMoves))
    numThreatenMate = len(threatenMateMoves)
    numHarmless = len(legalMoves) - numCheck - numThreatenMate
    if numThreatenMate == 0 and numCheck > 0:
        return {move: (1/numCheck)*.4 if move in checkMoves else (1/numHarmless)*.6 for move in legalMoves}
    if numThreatenMate > 0 and numCheck == 0:
        return {move: (1/numThreatenMate)*.5 if move in threatenMateMoves else (1/numHarmless)*.5 for move in legalMoves}
    if numThreatenMate > 0 and numCheck > 0:
        probs = dict()
        for move in legalMoves:
            if move in threatenMateMoves: probs[move] = (1/numThreatenMate)*.25
            elif move in checkMoves: probs[move] = (1/numCheck)*.25
            else: probs[move] = (1/numHarmless)*.5
        assert abs(sum(probs.values()) - 1) < .001
        # print(time.time()-t)
        return probs
    # print(time.time()-t)
    return {move: 1/len(legalMoves) for move in legalMoves}

def get_stockfish_move(fen : str, maxTime, movesToConsider=None, actuallyUs=False) -> Move:
    board = chess.Board(fen)
    # if actuallyUs:
    enemy_king_square = board.king(not board.turn)
    if enemy_king_square:
        # if there are any ally pieces that can take king, execute one of those moves
        enemy_king_attackers = board.attackers(board.turn, enemy_king_square)
        if enemy_king_attackers:
            attacker_square = enemy_king_attackers.pop()
            return chess.Move(attacker_square, enemy_king_square)
    else:
        return None
    move = None
    if movesToConsider != None:
        try:
            move = engines.play(board, maxTime, movesToConsider).move
        except Exception as e:
            print(e)
            print(f"ERROR GETTING MOVE FOR BOARD {board.fen()}")
            print(actuallyUs)
            print(f"MovesToConsider: {movesToConsider}")
    else:
        try:
            move = engines.play(board, maxTime).move
        except Exception as e:
            print(e)
            print(f"ERROR GETTING MOVE FOR BOARD {board.fen()}")
            print(actuallyUs)
            print(f"MovesToConsider: {movesToConsider}")
    return move