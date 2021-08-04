from collections import defaultdict
from strategy import select_sense
from utils.util import normalize
import chess

class BeliefState:
    def __init__(self, color, fen = chess.STARTING_FEN):
        self.color = color
        #belief distribution over possible boards
        self.myBoardDist = {fen: 1} #Map<fen, probability>
        #A distribution of distributions:
        #  For each possible opponent placement,
        #  opponent has a different belief distribution over possible boards
        self.oppBoardDists = {fen: {fen: 1}} #Map<fen, Map<fen, prob>)

    #Likelihood that a board is the true board
    def _our_board_belief(self, fen):
        return 0 if fen not in self.myBoardDist else self.myBoardDist[fen]

    #Opponents belief [0,1] that a board is the true board
    def _opp_board_belief(self, fen):
        totalProb = 0
        for board, boardDist in self.oppBoardDists.items():
            curProb = 0 if board not in boardDist else boardDist[board]
            totalProb += self._our_board_belief(board) * curProb
        return totalProb

    def sense_update(self, senseResult):
        #Calculate impossible boards
        impossibleBoards = set()
        for fen in self.myBoardDist:
            board = chess.Board(fen)
            for square, piece in senseResult:
                if board.piece_at(square) != piece:
                    impossibleBoards.add(board.fen())
        #Remove impossible board views
        self._remove_impossible_boards(impossibleBoards)

    def opp_sense_result_update(self):
        #TODO this
        return
        impossibleBoards = {}
        for board, boardDist in self.oppBoardDists.items():
            sense = select_sense(boardDist)

        #Remove impossible board views
        self._remove_impossible_boards(impossibleBoards)

    def opp_move_result_update(self, capturedMyPiece, captureSquare):
        #Calculate impossible boards
        impossibleBoards = set()
        if capturedMyPiece:
            for fen in self.myBoardDist:
                board = chess.Board(fen)
                if board.is_attacked_by(not self.color, captureSquare):
                    impossibleBoards.add(board.fen())
        #Remove impossible board views
        self._remove_impossible_boards(impossibleBoards)
        
        newMyBoardDist = defaultdict(float)
        newOppBoardDists = dict()
        
        for fen, totalProb in self.myBoardDist.items():
            board = chess.Board(fen)
            #TODO: add 'pass' to pseudo-legal moves
            moveProbs = {move: 1/len(list(board.pseudo_legal_moves)) for move in board.pseudo_legal_moves}
            for move, prob in moveProbs.items():
                board = chess.Board(fen)
                board.push(move)
                newFen = board.fen()
                newMyBoardDist[newFen] += moveProbs[move]*totalProb
                newOppBoardDist = defaultdict(float)
                oppBoardDist = self.oppBoardDists[fen]
                for fen2, totalProb2 in oppBoardDist.items():
                    board = chess.Board(fen2)
                    board.push(move)
                    newFen2 = board.fen()
                    newOppBoardDist[newFen2] += moveProbs[move]*totalProb2
                newOppBoardDists[newFen] = normalize(newOppBoardDist)

        self.oppBoardDists = newOppBoardDists
        self.myBoardDist = newMyBoardDist
        print(sum(self.myBoardDist.values()))
        for dist in self.oppBoardDists.values():
            print(sum(dist.values()))
        assert abs(1 - sum(self.myBoardDist.values())) < .0001
        for dist in self.oppBoardDists.values():
            assert abs(1-sum(dist.values())) < .0001


    def our_move_result_update(self, requestedMove, takenMove, capturedOppPiece, captureSquare):
        #Calculate impossible boards
        impossibleBoards = set()
        for board in self.mymyBoardDist:
            if ((capturedOppPiece and not board.is_attacked_by(self.color, captureSquare))
                or (requestedMove != takenMove and requestedMove in board.psuedo_legal_moves)
                or (takenMove not in list(board.pseudo_legal_moves))):
                impossibleBoards.add(board)
                    
        #Remove impossible board views
        self._remove_impossible_boards(impossibleBoards)

        #TODO: Update BeliefState after our move
        # for board in self.myBoardDist:
        #     board.push(takenMove)
        # for board, 

    def _remove_impossible_boards(self, impossibleBoards):
        for board in impossibleBoards:
            del self.myBoardDist[board]
            del self.oppBoardDists[board]
        normalize(self.myBoardDist)
        for dist in self.oppBoardDists.values():
            normalize(dist)
    
    def display(self):
        print(f'\tMY BOARD DISTRIBUTION: ({len(self.myBoardDist)})')
        for fen, prob in self.myBoardDist.items():
            print('\t\t', fen, '\tprobability:', prob)
        print(f'\tOPP\'S BOARD DISTS ({len(self.oppBoardDists)}):')
        for fen, dist in self.oppBoardDists.items():
            print('\t\t', fen)
            for (sub_fen, prob) in dist.items():
                print('\t\t\t', sub_fen, '\tprobability:', prob)