from collections import defaultdict
import itertools
from utils.information_utils import entropy, jenson_shannon_divergence
from utils.types import *
from utils.util import *
import chess

class BoardsAndProb:
    def __init__(self):
        self.fens = set()
        self.prob = 0
    def add(self, fen, prob):
        self.fens.add(fen)
        self.prob += prob
        assert 0 <= self.prob <= 1.000001

def board_beliefs_by_square(boardDist: BoardDist):
    boardBeliefsBySquare = defaultdict(dict)
    for fen, prob in boardDist.items():
        board = chess.Board(fen)
        for square in chess.SQUARES:
            if board.piece_at(square) not in boardBeliefsBySquare[square]:
                boardBeliefsBySquare[square][board.piece_at(square)] = BoardsAndProb()
            boardBeliefsBySquare[square][board.piece_at(square)].add(fen, prob)
    return boardBeliefsBySquare

def get_set_differences_with_probs(listOfBoardSetsForMultipleSquares):
    combosWithOneBoardSetEachSquare = itertools.product(*listOfBoardSetsForMultipleSquares)
    results = dict()
    for boardsAndProbSet in combosWithOneBoardSetEachSquare:
        boardSets = [boardsAndProb.fens for boardsAndProb in boardsAndProbSet]
        resultingBoards = frozenset(set.intersection(*boardSets))
        resultingProb = product([boardsAndProb.prob for boardsAndProb in boardsAndProbSet])
        if len(resultingBoards) > 0: results[resultingBoards] = resultingProb
    normalize(results, adjust=False, giveToZeros=0, raiseNum=0)
    return results

def select_sense(boardDist: BoardDist) -> SenseMove:
    zeroForEachMove = {move : 0 for move in get_pseudo_legal_moves(boardDist.keys()) }
    moveDistsByFen = {fen : zeroForEachMove.copy() for fen in boardDist}
    for fen in boardDist:
        bestMove = engines.play(chess.Board(fen), maxTime=.01)
        moveDistsByFen[fen][bestMove] = 1

    #get the board sets (and probabilities) for each square
    #for each set of 9 squares...
    #   take the difference of of every combo of board sets (one from each square)...
    #   for each of those new sets:
    #       find its probability
    #       calculate the entropy of its boards move dists
    #   find the weighted average entropy of the move dists of the resulting sets
    #choose the sense move resulting in the lowest weighted average entropy
    boardBeliefsBySquare = board_beliefs_by_square(boardDist)
    senseScores = defaultdict(float)
    for senseMove in GOOD_SENSING_SQUARES:
        senseSquares = get_sense_squares(senseMove)
        setDifferencesWithProbs = get_set_differences_with_probs([boardBeliefsBySquare[square].values() for square in senseSquares])
        for fenSet, prob in setDifferencesWithProbs.items():
            moveDists = [list(moveDistsByFen[fen].values()) for fen in fenSet]
            moveProbs = [boardDist[fen] for fen in fenSet]
            moveDivergence = jenson_shannon_divergence(moveDists, weights=moveProbs)
            senseScores[senseMove] += moveDivergence * prob
    return min(senseScores, key=senseScores.get)