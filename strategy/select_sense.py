from collections import defaultdict
from utils.types import *
from utils import util
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
def select_sense(boardDist: BoardDist) -> SenseMove:
    squareDist = boardDist_to_squareDist(boardDist)
    sense_options = {} # dict where each key is a sense move, each value the amount of uncertainty we would remove by that move
    for senseMove in util.GOOD_SENSING_SQUARES:
        sense_options[senseMove] = 0
        for sensed_square in util.get_sense_squares(senseMove):
            total_square_certainty = sum([pow(piece_prob, 2) for piece_prob in squareDist[sensed_square].values()])
            sense_options[senseMove] += total_square_certainty
    best_sense_move = min(sense_options, key=lambda sense: sense_options[sense])
    return best_sense_move