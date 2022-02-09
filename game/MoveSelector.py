import chess
from utils.util import *
import utils.engine_utils as engines
import strategy.select_move as strategy

class MoveSelector:
    def __init__(self, actuallyUs, gambleFactor, timePerMove, giveFrivolousChecks, onlyGiveChecks, experimental=False):
        assert 0 <= gambleFactor <= 2
        self.actuallyUs = actuallyUs
        self.gambleFactor = gambleFactor
        self.timePerMove = timePerMove
        self.giveFrivolousChecks = giveFrivolousChecks
        self.onlyGiveChecks = onlyGiveChecks
        self.experimental = experimental
        if self.onlyGiveChecks: assert self.giveFrivolousChecks
    
    def select_move(self, beliefState):
        assert self.actuallyUs
        moveDist = self.get_move_dist(beliefState.myBoardDist, maxTime=self.timePerMove)
        topMoves = sorted(moveDist, key=moveDist.get, reverse=True)[:5]
        move = topMoves[0]
        if move != None and move.promotion != None and move.promotion != chess.KNIGHT:
            move.promotion = chess.QUEEN
        return move
        # choices = normalize({move: moveDist[move] for move in topMoves}, adjust=True, giveToZeros=0, raiseNum=7)
        # return sample(choices)

    def get_move_dist(self, boardDist, maxTime : float, movesToConsider=None):
        return strategy.get_move_dist(boardDist, maxTime, self.actuallyUs, self.gambleFactor, self.giveFrivolousChecks, self.onlyGiveChecks, self.experimental, movesToConsider)