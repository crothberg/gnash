from collections import defaultdict
from utils.types import *
from utils.util import *
import chess

def boardDist_to_squareDist(boardDist: BoardDist) -> SquareDist:
    ''' Convert distribution of boards to a representation of the
    probability, at each square, of each piece being on that square '''
    squareDist = defaultdict(lambda: defaultdict(int))
    for fen, prob in boardDist.items():
        board = chess.Board(fen)
        for square in chess.SQUARES:           
            squareDist[square][board.piece_at(square)] += prob    
    return squareDist

##TODO: Parallelize this
def select_sense(boardDist: BoardDist, actuallyUs = False) -> SenseMove:
    if actuallyUs: checkProb, kingSquares = percent_check(boardDist)
    if actuallyUs: inCheckProb, checkerSquares = percent_in_check(boardDist)
    if actuallyUs: print("Check probs:", checkProb, kingSquares)
    if actuallyUs: print("inCheck probs:", inCheckProb, checkerSquares)
    if actuallyUs:
        if checkProb > .5 and len(kingSquares) > 1:
            bestSenseMove = None
            bestSenseScore = 0
            for senseMove in GOOD_SENSING_SQUARES:
                senseScore = 0
                for sensedSquare in get_sense_squares(senseMove):
                    senseScore += kingSquares[sensedSquare]
                if senseScore > bestSenseScore:
                    bestSenseMove = senseMove
                    bestSenseScore = senseScore
            if actuallyUs: print("Best sensing move given checkProb:", bestSenseMove)
            return bestSenseMove
        if (
            (inCheckProb > .6 and sum([1 if checkerSquares[s]>.2 else 0 for s in checkerSquares])>1)
            or (inCheckProb >= .75 and not (len(checkerSquares) == 1 and inCheckProb == 1))
            ):
            bestSenseMove = None
            bestSenseScore = 0
            for senseMove in GOOD_SENSING_SQUARES:
                senseScore = 0
                for sensedSquare in get_sense_squares(senseMove):
                    senseScore += checkerSquares[sensedSquare]
                if senseScore > bestSenseScore:
                    bestSenseMove = senseMove
                    bestSenseScore = senseScore
            if actuallyUs: print("Best sensing move given inCheckProb:", bestSenseMove)
            return bestSenseMove
    squareDist = boardDist_to_squareDist(boardDist)
    sense_options = {} # dict where each key is a sense move, each value the amount of uncertainty we would remove by that move
    for senseMove in GOOD_SENSING_SQUARES:
        sense_options[senseMove] = 0
        for sensed_square in get_sense_squares(senseMove):
            total_square_certainty = sum([pow(piece_prob, 2) for piece_prob in squareDist[sensed_square].values()])
            sense_options[senseMove] += total_square_certainty
    best_sense_move = min(sense_options, key=lambda sense: sense_options[sense])
    return best_sense_move