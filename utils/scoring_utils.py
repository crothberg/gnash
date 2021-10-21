import chess
import chess.engine
import utils.engine_utils as engines

MATE_SCORE=5000

#return a score in [0,1]
def score(board : chess.Board, time : float, color : chess.Color):
    if board.king(color) == None: return 0
    if board.king(not color) == None: return 1
    
    if board.attackers(board.turn, board.king(not board.turn)):
        if board.turn == color: return 1
        else: return 0

    board.clear_stack()
    if board.is_check():
        board.ep_square = None
    analysis = engines.analyse(board, .01)
    if analysis == None:
        return 0 ##TODO: make this better
    score = analysis['score']
    score = score.pov(color).score(mate_score=MATE_SCORE)

    positive = score >= 0
    score = (abs(score)**(1/6))/(MATE_SCORE**(1/6))
    if not positive: score *= -1

    #set score between .05 and .95
    score = max(-.9, min(.9, score))
    score += (1-score)/2

    return score