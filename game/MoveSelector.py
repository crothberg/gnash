import chess
from utils.util import *
import utils.engine_utils as engines
import strategy.select_move as strategy

class MoveSelector:
    def __init__(self, actuallyUs, gambleFactor, timePerMove):
        assert 0 <= gambleFactor <= 1
        self.actuallyUs = actuallyUs
        self.gambleFactor = gambleFactor
        self.timePerMove = timePerMove
    
    def select_move(self, beliefState):
        assert self.actuallyUs
        topFen = list(beliefState.myBoardDist.keys())[0]
        board = chess.Board(topFen)
        if beliefState.myBoardDist[topFen] > .75:
            enemy_king_square = board.king(not board.turn)
            if enemy_king_square:
                # if there are any ally pieces that can take king, execute one of those moves
                enemy_king_attackers = board.attackers(board.turn, enemy_king_square)
                if enemy_king_attackers:
                    attacker_square = enemy_king_attackers.pop()
                    return chess.Move(attacker_square, enemy_king_square)
            move = engines.play(board, chess.engine.Limit(time=min(self.timePerMove, 1.0))).move
            if move != None and move.promotion != None and move.promotion != chess.KNIGHT:
                move.promotion = chess.QUEEN
            return move
        moveDist = self.get_move_dist(beliefState.myBoardDist, maxTime=self.timePerMove)
        print(moveDist)
        topMoves = sorted(moveDist, key=moveDist.get, reverse=True)[:5]
        print([(move, moveDist[move]) for move in topMoves])
        move = topMoves[0]
        print(moveDist[move])
        if move != None and move.promotion != None and move.promotion != chess.KNIGHT:
            move.promotion = chess.QUEEN
        choices = normalize({move: moveDist[move] for move in topMoves}, adjust=True, giveToZeros=0, raiseNum=7)
        print(choices)
        return sample(choices)

    def get_move_dist(self, boardDist, maxTime : float, movesToConsider=None):
        return strategy.get_move_dist(boardDist, maxTime, self.actuallyUs, self.gambleFactor, movesToConsider)