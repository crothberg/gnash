from collections import defaultdict
from strategy import select_sense
from strategy.select_move import *
from utils.util import normalize, simulate_sense
from reconchess.utilities import revise_move
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
        BeliefState._remove_impossible_boards(self.myBoardDist, impossibleBoards)
        # for board in impossibleBoards:
        #     del self.oppBoardDists[board]

    def opp_sense_result_update(self):
        for fen, boardDist in self.oppBoardDists.items():
            board = chess.Board(fen)
            senseSquare = select_sense.select_sense(boardDist)
            senseResult = simulate_sense(board, senseSquare)
            impossibleBoards = set()
            for fen in boardDist:
                board = chess.Board(fen)
                for square, piece in senseResult:
                    if board.piece_at(square) != piece:
                        impossibleBoards.add(board.fen())
            BeliefState._remove_impossible_boards(boardDist, impossibleBoards)

    def opp_move_result_update(self, capturedMyPiece, captureSquare):
        #Calculate impossible boards
        impossibleBoards = set()
        if capturedMyPiece:
            for fen in self.myBoardDist:
                board = chess.Board(fen)
                if not board.is_attacked_by(not self.color, captureSquare):
                    impossibleBoards.add(board.fen())
        #Remove impossible board views
        BeliefState._remove_impossible_boards(self.myBoardDist, impossibleBoards)
        # for board in impossibleBoards:
        #     del self.oppBoardDists[board]
        
        newMyBoardDist = defaultdict(float)
        # newOppBoardDists = dict()
        
        for fen, totalProb in self.myBoardDist.items():
            board = chess.Board(fen)
            #TODO: fix this, I think it should move out of the loop
            moveProbs = get_move_dist({fen: 1}, maxSamples=50)
            for move, prob in moveProbs.items():
                board = chess.Board(fen)
                if ((move not in get_all_moves(board))
                 or (capturedMyPiece and move.to_square != captureSquare)):
                        continue
                board.push(move)
                newFen = board.fen()
                newMyBoardDist[newFen] += moveProbs[move]*totalProb
                # newOppBoardDist = defaultdict(float)
                # oppBoardDist = self.oppBoardDists[fen]
                # for fen2, totalProb2 in oppBoardDist.items():
                #     board = chess.Board(fen2)
                #     board.push(move)
                #     newFen2 = board.fen()
                #     newOppBoardDist[newFen2] += moveProbs[move]*totalProb2
                # newOppBoardDists[newFen] = normalize(newOppBoardDist)

        # self.oppBoardDists = newOppBoardDists
        self.myBoardDist = normalize(newMyBoardDist)
        if abs(1 - sum(self.myBoardDist.values())) >= .0001:
            print(self.myBoardDist)
            print(sum(self.myBoardDist.values()))
            assert False, "board dist values should always sum to 1"
        # for dist in self.oppBoardDists.values():
        #     assert abs(1-sum(dist.values())) < .0001


    def our_move_result_update(self, requestedMove, takenMove, capturedOppPiece, captureSquare):
        #Calculate impossible boards
        impossibleBoards = set()
        for fen in self.myBoardDist:
            board = chess.Board(fen)
            if ((capturedOppPiece and not board.is_attacked_by(self.color, captureSquare))
                or (requestedMove != takenMove and requestedMove in board.pseudo_legal_moves)
                or (takenMove not in list(board.pseudo_legal_moves) + [None])):
                impossibleBoards.add(board.fen())
                    
        #Remove impossible board views
        BeliefState._remove_impossible_boards(self.myBoardDist, impossibleBoards)
        # for board in impossibleBoards:
        #     del self.oppBoardDists[board]

        # for oldFen, oppBoardDist in self.oppBoardDists.items():
        #     newOppBoardDist = defaultdict(float)
        #     for fen, fenProb in oppBoardDist.items():
        #         board = chess.Board(fen)
        #         #TODO Fix this, I think it should move out of the loop or something
        #         believedMoveProbs = get_move_dist({board.fen(): 1}, maxSamples=50)
        #         for move, moveProb in believedMoveProbs.items():
        #             board = chess.Board(fen)
        #             board.push(move)
        #             newFen = board.fen()
        #             newOppBoardDist[newFen] += believedMoveProbs[move]*fenProb
        #     self.oppBoardDists[oldFen] = normalize(newOppBoardDist)

        #Update myBoardDist keys based on taken move
        newBoardDist = defaultdict(float)
        # newOppBoardDists = dict()
        for fen in self.myBoardDist:
            oldBoard = chess.Board(fen)
            newBoard = oldBoard
            newBoard.push(takenMove if takenMove is not None else chess.Move.null())
            newFen = newBoard.fen()
            newBoardDist[newFen] += self.myBoardDist[fen]
            # newOppBoardDists[newFen] = self.oppBoardDists[fen]
        self.myBoardDist = newBoardDist
        # self.oppBoardDists = newOppBoardDists
        if abs(1 - sum(self.myBoardDist.values())) >= .0001:
            print(self.myBoardDist)
            print(sum(self.myBoardDist.values()))
            assert False, "board dist values should always sum to 1"

    def _remove_impossible_boards(dist, impossibleBoards):
        for board in impossibleBoards:
            del dist[board]
        normalize(dist)

    def display(self):
        print(f'\tMY BOARD DISTRIBUTION: ({len(self.myBoardDist)})')
        for fen, prob in self.myBoardDist.items():
            print('\t\t', fen, '\tprobability:', prob)
        # print(f'\tOPP\'S BOARD DISTS ({len(self.oppBoardDists)}):')
        # for fen, dist in self.oppBoardDists.items():
        #     print('\t\t', fen)
        #     for (sub_fen, prob) in dist.items():
        #         print('\t\t\t', sub_fen, '\tprobability:', prob)