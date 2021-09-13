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
        #A dictionary of unexpanded boards where:
        #  The keys are turn numbers
        #  The values are all boards last expanded at that turn
        self.stashedBoards = defaultdict(set)

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

    def sense_update_helper(fen, senseResult, impossibleBoards):
        board = chess.Board(fen)
        for square, piece in senseResult:
            if board.piece_at(square) != piece:
                impossibleBoards.add(board.fen())
    def sense_update(self, senseResult):
        #Calculate impossible boards
        impossibleBoards = set()
        gevent.joinall([gevent.spawn(BeliefState.sense_update_helper, fen, senseResult, impossibleBoards) for fen in self.myBoardDist])
        #Remove impossible board views
        BeliefState._remove_impossible_boards(self.myBoardDist, impossibleBoards)
        for board in impossibleBoards:
            del self.oppBoardDists[board]

    def opp_sense_result_update_helper(self, fen, boardDist):
        board = chess.Board(fen)
        senseSquare = select_sense.select_sense(boardDist)
        senseResult = simulate_sense(board, senseSquare)
        impossibleBoards = set()
        for fen in boardDist:
            board = chess.Board(fen)
            if board.king(board.turn) == None:
                impossibleBoards.add(board.fen())
            for square, piece in senseResult:
                if board.piece_at(square) != piece:
                    impossibleBoards.add(board.fen())
        BeliefState._remove_impossible_boards(boardDist, impossibleBoards)
    def opp_sense_result_update(self):
        gevent.joinall([gevent.spawn(BeliefState.opp_sense_result_update_helper, self, fen, boardDist) for fen, boardDist in self.oppBoardDists.items()])

    def opp_move_result_update_helper(fen, timeShare, boardProb, newMyBoardDist, oldOppBoardDists, newOppBoardDists, capturedMyPiece, captureSquare):
        board = chess.Board(fen)
        moveProbs = get_move_dist(oldOppBoardDists[fen], maxTime=timeShare)
        allMoves = get_all_moves(board)
        for move, moveProb in moveProbs.items():
            if move not in allMoves:
                continue
            board = chess.Board(fen)
            revisedMove = revise_move(board, move) if move != chess.Move.null() else chess.Move.null()
            revisedMove = revisedMove or chess.Move.null()
            if ((capturedMyPiece and revisedMove.to_square != captureSquare)
                or (not capturedMyPiece and board.piece_at(revisedMove.to_square))):
                    continue
            board.push(revisedMove)
            newFen = board.fen()
            newMyBoardDist[newFen] += moveProb*boardProb
            newOppBoardDist = defaultdict(float)
            oppBoardDist = oldOppBoardDists[fen]
            for fen2, totalProb2 in oppBoardDist.items():
                board = chess.Board(fen2)
                revisedMove = revise_move(board, move) if move != chess.Move.null() else chess.Move.null()
                revisedMove = revisedMove or chess.Move.null()
                board.push(revisedMove)
                newFen2 = board.fen()
                newOppBoardDist[newFen2] += moveProbs[move]*totalProb2
            newOppBoardDists[newFen] = normalize(newOppBoardDist, adjust=True)
    def opp_move_result_update(self, capturedMyPiece, captureSquare, maxTime):
        #Calculate impossible boards
        impossibleBoards = set()
        if capturedMyPiece:
            for fen in self.myBoardDist:
                board = chess.Board(fen)
                if not board.is_attacked_by(not self.color, captureSquare):
                    impossibleBoards.add(board.fen())
        #Remove impossible board views
        BeliefState._remove_impossible_boards(self.myBoardDist, impossibleBoards)
        for board in impossibleBoards:
            del self.oppBoardDists[board]
        
        newMyBoardDist = defaultdict(float)
        newOppBoardDists = dict()
        gevent.joinall([gevent.spawn(BeliefState.opp_move_result_update_helper, fen, maxTime*boardProb, boardProb, newMyBoardDist, self.oppBoardDists, newOppBoardDists, capturedMyPiece, captureSquare) for fen, boardProb in self.myBoardDist.items()])
        # print(f"Completed after {time.time()-startUpdateTime} seconds")
        self.oppBoardDists = newOppBoardDists
        self.myBoardDist = normalize_board_dist(newMyBoardDist)
        self._condense_opp_board_dists()
        if abs(1 - sum(self.myBoardDist.values())) >= .0001:
            print(self.myBoardDist)
            print(sum(self.myBoardDist.values()))
            assert False, "board dist values should always sum to 1"
        for dist in self.oppBoardDists.values():
            assert abs(1-sum(dist.values())) < .0001

    def our_move_result_update(self, requestedMove, takenMove, capturedOppPiece, captureSquare, maxTime):
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
        for board in impossibleBoards:
            del self.oppBoardDists[board]

        for oldFen, oppBoardDist in self.oppBoardDists.items():
            prob = self.myBoardDist[oldFen]
            newOppBoardDist = defaultdict(float)
            believedMoveProbs = get_move_dist(oppBoardDist, maxTime=maxTime*prob)
            for fen, fenProb in oppBoardDist.items():
                board = chess.Board(fen)
                allMoves = get_all_moves(board)
                for move, moveProb in believedMoveProbs.items():
                    if move not in allMoves:
                        continue
                    board = chess.Board(fen)
                    revisedMove = revise_move(board, move) if move != chess.Move.null() else chess.Move.null()
                    revisedMove = revisedMove or chess.Move.null()
                    if ((capturedOppPiece and revisedMove.to_square != captureSquare)
                        or (not capturedOppPiece and board.piece_at(revisedMove.to_square))):
                        continue
                    board.push(revisedMove)
                    newFen = board.fen()
                    newOppBoardDist[newFen] += moveProb*fenProb
            self.oppBoardDists[oldFen] = normalize(newOppBoardDist, adjust=True)

        #Update myBoardDist keys based on taken move
        newBoardDist = defaultdict(float)
        newOppBoardDists = dict()
        for fen in self.myBoardDist:
            oldBoard = chess.Board(fen)
            newBoard = oldBoard
            newBoard.push(takenMove if takenMove is not None else chess.Move.null())
            newFen = newBoard.fen()
            newBoardDist[newFen] += self.myBoardDist[fen]
            newOppBoardDists[newFen] = self.oppBoardDists[fen]
        self.myBoardDist = newBoardDist
        self.oppBoardDists = newOppBoardDists
        self._condense_opp_board_dists()
        if abs(1 - sum(self.myBoardDist.values())) >= .0001:
            print(self.myBoardDist)
            print(sum(self.myBoardDist.values()))
            assert False, "board dist values should always sum to 1"

    def _condense_opp_board_dists(self, maxBoards=500):
        if sum([len(dist) for dist in self.oppBoardDists.values()]) > maxBoards:
            newOppBoardDists = dict()
            for boardKey, dist in self.oppBoardDists.items():
                maxBoardsForDist = int(maxBoards * self.myBoardDist[boardKey])
                mostLikelyBoards = set(list(sorted(dist, key=dist.get, reverse=True))[:maxBoardsForDist-1])
                mostLikelyBoards.add(boardKey)
                newOppBoardDist = {board : dist[board] for board in mostLikelyBoards}
                newOppBoardDists[boardKey] = normalize(newOppBoardDist, adjust=True)
            self.oppBoardDists = newOppBoardDists

    # def _restore_opp_board_dists(self):
    #     for board in self.myBoardDist:
    #         if len(self.oppBoardDists[board]) == 0:
    #             self.oppBoardDists[board] = {board : 1.0}

    def _remove_impossible_boards(dist, impossibleBoards):
        for board in impossibleBoards:
            del dist[board]
        normalize(dist, adjust=True)

    def display(self):
        print(f'\tMY BOARD DISTRIBUTION: ({len(self.myBoardDist)})')
        for fen, prob in self.myBoardDist.items():
            print('\t\t', fen, '\tprobability:', prob)
        print(f"Additional {sum([len(x) for x in self.stashedBoards.values()])} boards stashed.")
        # print(f'\tOPP\'S BOARD DISTS ({len(self.oppBoardDists)}):')
        # for fen, dist in self.oppBoardDists.items():
        #     print('\t\t', fen)
        #     for (sub_fen, prob) in dist.items():
        #         print('\t\t\t', sub_fen, '\tprobability:', prob)