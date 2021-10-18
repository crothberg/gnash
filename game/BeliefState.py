import threading
from game.MoveSelector import MoveSelector
from collections import defaultdict
from strategy.select_sense import select_sense
from utils.util import *
import utils.parallelism_utils as parallel
import multiprocessing as mp
from reconchess.utilities import revise_move
import chess

class BeliefState:
    def __init__(self, color, fen = chess.STARTING_FEN, moveSelector = None, oppMoveSelector = None):
        self.color = color
        #belief distribution over possible boards
        self.myBoardDist = {fen: 1} #Map<fen, probability>
        #A distribution of distributions:
        #  For each possible opponent placement,
        #  opponent has a different belief distribution over possible boards
        self.oppBoardDists = {fen: {fen: 1}} #Map<fen, Map<fen, prob>)

        self.catchingUp = False

        self.moveSelector = moveSelector or MoveSelector(actuallyUs=True, gambleFactor=.1, timePerMove=5)
        self.oppMoveSelector = oppMoveSelector or MoveSelector(actuallyUs=False, gambleFactor=.3, timePerMove=None)
        self.believedMoveSelector = MoveSelector(actuallyUs=False, gambleFactor=.15, timePerMove=None)

    def sense_update_helper(fen, senseResult, impossibleBoards):
        board = chess.Board(fen)
        for square, piece in senseResult:
            if board.piece_at(square) != piece:
                impossibleBoards.add(board.fen())
    def sense_update(self, senseResult, maxTime):
        self._check_invariants()
        #Calculate impossible boards
        impossibleBoards = set()
        for fen in self.myBoardDist:
            BeliefState.sense_update_helper(fen, senseResult, impossibleBoards)
        # parallel.run_parallel(BeliefState.sense_update_helper, [[fen, senseResult, impossibleBoards] for fen in self.myBoardDist])
        #Remove impossible board views
        for board in impossibleBoards:
            del self.myBoardDist[board]
            del self.oppBoardDists[board]
        self.myBoardDist = normalize_our_board_dist(self.myBoardDist, self.color) if maxTime > .5 else normalize(self.myBoardDist, adjust=True)
        self._check_invariants()

    def opp_sense_result_update_helper(self, fen, boardDist):
        board = chess.Board(fen)
        senseSquare = select_sense(boardDist, actuallyUs=False)
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
        self._check_invariants()
        for fen, boardDist in self.oppBoardDists.items():
            BeliefState.opp_sense_result_update_helper(self, fen, boardDist)
        # parallel.run_parallel(BeliefState.opp_sense_result_update_helper, list((self, fen, boardDist) for fen, boardDist in self.oppBoardDists.items()))
        # gevent.joinall([gevent.spawn(BeliefState.opp_sense_result_update_helper, self, fen, boardDist) for fen, boardDist in self.oppBoardDists.items()])
        self._check_invariants()

    def opp_move_result_update_helper(self, fen, timeShare, boardProb, newMyBoardDist, oppBoardDist, newOppBoardDists, capturedMyPiece, captureSquare):
        # print(f"Opening thread {threading.get_ident()} for board {fen} with time {timeShare}", flush=True)
        # print(f"Opening process {mp.current_process()} for board {fen} with time {timeShare}", flush=True)
        t0 = time.time()
        moveProbs = self.oppMoveSelector.get_move_dist(oppBoardDist, maxTime=timeShare)
        # print(f"Thread {threading.get_ident()} for board {fen} with timeshare {timeShare} got move dist after {time.time() - t0} seconds", flush=True)
        for move, moveProb in moveProbs.items():
            board = chess.Board(fen)
            revisedMove = revise_move(board, move) if move != chess.Move.null() else chess.Move.null()
            revisedMove = revisedMove or chess.Move.null()
            if ((capturedMyPiece and captureSquare != real_capture_square_of_move(board, revisedMove))
                or (not capturedMyPiece and real_capture_square_of_move(board, revisedMove) != None)):
                    continue
            board.push(revisedMove)
            board.halfmove_clock = 0
            newFen = board.fen()
            newMyBoardDist[newFen] = moveProb*boardProb + (newMyBoardDist[newFen] if newFen in newMyBoardDist else 0)
            newOppBoardDist = dict()
            if self.catchingUp:
                newOppBoardDist = {newFen: 1.0}
            else:
                board = chess.Board(fen)
                for fen2, totalProb2 in oppBoardDist.items():
                    board2 = chess.Board(fen2)
                    revisedMoveOnRealBoard = revise_move(board, move) if move != chess.Move.null() else chess.Move.null()
                    revisedMoveOnRealBoard = revisedMoveOnRealBoard or chess.Move.null()
                    revisedMove = revise_move(board, move) if move != chess.Move.null() else chess.Move.null()
                    revisedMove = revisedMove or chess.Move.null()
                    if revisedMove != revisedMoveOnRealBoard:
                        continue
                    if ((capturedMyPiece and captureSquare != real_capture_square_of_move(board2, revisedMove))
                        or (not capturedMyPiece and real_capture_square_of_move(board2, revisedMove) != None)):
                            continue
                    board2.push(revisedMove)
                    board2.halfmove_clock = 0
                    newFen2 = board2.fen()
                    newOppBoardDist[newFen2] = moveProbs[move]*totalProb2 + (0 if newFen2 not in newOppBoardDist else newOppBoardDist[newFen2])
            assert len(newOppBoardDist) > 0
            newOppBoardDist = normalize(newOppBoardDist, adjust=True)
            newOppBoardDists[newFen] = newOppBoardDist
        t1 = time.time()
    def opp_move_result_update(self, capturedMyPiece, captureSquare, maxTime):
        self._check_invariants()
        #Calculate impossible boards
        impossibleBoards = set()
        for fen in self.myBoardDist:
            board = chess.Board(fen)
            #if you captured my piece but couldn't have, impossible
            if capturedMyPiece:
                possible = False
                for move in get_pseudo_legal_moves({board.fen()}):
                    if real_capture_square_of_move(board, move) == captureSquare:
                        possible = True
                if not possible:
                    impossibleBoards.add(board.fen())
            # if capturedMyPiece:
            #     couldHaveBeenEp =  False
            #     if board.ep_square == captureSquare:
            #         couldHaveBeenEp = True
            #     if not (board.is_attacked_by(not self.color, captureSquare) or couldHaveBeenEp):
                    # impossibleBoards.add(board.fen())
        #Remove impossible board views
        try:
            BeliefState._remove_impossible_boards(self.myBoardDist, impossibleBoards)
        except EmptyBoardDist:
            self.oppBoardDists = {}
            raise EmptyBoardDist

        for board in impossibleBoards:
            del self.oppBoardDists[board]
        
        self._check_invariants()
        
        newMyBoardDist = dict()
        newOppBoardDists = dict()
        mbd = self.myBoardDist
        sortedFens = list(sorted(self.myBoardDist.keys(), key=self.myBoardDist.get, reverse=True))
        parallel.run_parallel(self.opp_move_result_update_helper, list((fen, min(1.5, maxTime*mbd[fen]), mbd[fen], newMyBoardDist, self.oppBoardDists[fen], newOppBoardDists, capturedMyPiece, captureSquare) for fen in sortedFens), threadingOnly=False)
            # print(newMyBoardDist)
            # print(newOppBoardDists)
        # for fen, boardProb in self.myBoardDist.items():
        #     ##TODO: Make boards where they could have taken our king (and knew it) much more unlikely
        #     # self.opp_move_result_update_helper(fen, min(1.5, (maxTime*.5)/len(self.myBoardDist) + (maxTime*.5)*boardProb), boardProb, newMyBoardDist, self.oppBoardDists[fen], newOppBoardDists, capturedMyPiece, captureSquare)
        #     self.opp_move_result_update_helper(fen, min(1.5, maxTime*boardProb), boardProb, newMyBoardDist, self.oppBoardDists[fen], newOppBoardDists, capturedMyPiece, captureSquare)
        self.oppBoardDists = newOppBoardDists
        newMyBoardDistKeys = set(newMyBoardDist.keys())
        assert len(newMyBoardDistKeys)>0, f"Updates based on myBoardDist({self.myBoardDist.keys()} should have created at least one new possible board."
        try:
            self.myBoardDist = normalize_our_board_dist(newMyBoardDist, self.color) if maxTime > .5 else normalize(newMyBoardDist, adjust=True)
        except:
            assert False, (
                f"Normalizing \n{newMyBoardDistKeys}\n should not have resulted in an error"
                + f"self.myBoardDist: {self.myBoardDist}"
            )
        self._condense_opp_board_dists()
        self._check_invariants()


    def _our_move_result_update_helper(self, oldFen, maxTime, captureSquare):
        oppBoardDist = self.oppBoardDists[oldFen]
        prob = self.myBoardDist[oldFen]
        newOppBoardDist = defaultdict(float)
        believedMoveProbs = self.believedMoveSelector.get_move_dist(oppBoardDist, maxTime=maxTime*prob)
        for move in get_all_moves(chess.Board(oldFen)):
            if move not in believedMoveProbs:
                believedMoveProbs[move] = 0
        for fen, fenProb in oppBoardDist.items():
            allMoves = get_all_moves(chess.Board(fen))
            for move, moveProb in believedMoveProbs.items():
                if move not in allMoves:
                    continue
                board2 = chess.Board(fen)
                revisedMove = revise_move(board2, move) if move != chess.Move.null() else chess.Move.null()
                revisedMove = revisedMove or chess.Move.null()
                if (real_capture_square_of_move(board2, revisedMove) != captureSquare):
                    continue
                board2.push(revisedMove)
                board2.halfmove_clock = 0
                newFen = board2.fen()
                newOppBoardDist[newFen] += moveProb*fenProb
        self.oppBoardDists[oldFen] = normalize(newOppBoardDist, adjust=True)

    def our_move_result_update(self, requestedMove, takenMove, capturedOppPiece, captureSquare, maxTime):
        self._check_invariants()
        #Calculate impossible boards
        impossibleBoards = set()
        kingless = 0
        legal = 0
        for fen in self.myBoardDist:
            board = chess.Board(fen)
            pseudoLegalMoves = get_pseudo_legal_moves({fen})
            pseudoLegalMoves.add(None)
            if ((real_capture_square_of_move(board, takenMove) != captureSquare)
                or (requestedMove != takenMove and requestedMove in pseudoLegalMoves)
                or (takenMove not in pseudoLegalMoves)):
                impossibleBoards.add(board.fen())
                continue
            legal += 1
            if takenMove != None:
                board.push(takenMove)
                if board.king(board.turn) == None:
                    impossibleBoards.add(fen)
                    kingless += 1
        if kingless > 1:
            print(kingless, legal)
        if kingless == legal and kingless > 1:
            return "won"
        # print(f"Finding impossible boards took {time.time() - t} seconds")
                    
        #Remove impossible board views
        try:
            BeliefState._remove_impossible_boards(self.myBoardDist, impossibleBoards)
        except EmptyBoardDist:
            self.oppBoardDists = {}
            raise EmptyBoardDist
        for board in impossibleBoards:
            del self.oppBoardDists[board]

        for boardKey in self.myBoardDist:
            boardDist = self.oppBoardDists[boardKey]
            impossibleBoards = set()
            for fen in boardDist:
                board = chess.Board(fen)
                pseudoLegalMoves = get_pseudo_legal_moves({fen})
                pseudoLegalMoves.add(None)
                if ((real_capture_square_of_move(board, takenMove) != captureSquare)
                    or (requestedMove != takenMove and requestedMove in pseudoLegalMoves)
                    or (takenMove not in pseudoLegalMoves)):
                    impossibleBoards.add(board.fen())
                    continue
            BeliefState._remove_impossible_boards(self.oppBoardDists[boardKey], impossibleBoards)

        self._check_invariants()
        
        if not self.catchingUp:
            parallel.run_parallel(self._our_move_result_update_helper, list((fen, maxTime, captureSquare) for fen in self.oppBoardDists))
            self._check_invariants()

        #Update myBoardDist keys based on taken move
        newBoardDist = defaultdict(float)
        newOppBoardDists = dict()
        for fen in self.myBoardDist:
            oldBoard = chess.Board(fen)
            newBoard = oldBoard
            newBoard.push(takenMove if takenMove is not None else chess.Move.null())
            newBoard.halfmove_clock = 0
            newFen = newBoard.fen()
            newBoardDist[newFen] += self.myBoardDist[fen]
            newOppBoardDists[newFen] = self.oppBoardDists[fen]
        self.myBoardDist = newBoardDist
        if self.catchingUp:
            self.oppBoardDists = {fen: {fen: 1.0} for fen in self.myBoardDist}
        else:
            self.oppBoardDists = newOppBoardDists
        self._condense_opp_board_dists()
        self._check_invariants()

    def _condense_opp_board_dists(self, maxBoards=400):
        self._check_invariants()
        if sum([len(dist) for dist in self.oppBoardDists.values()]) > maxBoards:
            newOppBoardDists = dict()
            for boardKey, dist in self.oppBoardDists.items():
                maxBoardsForDist = max(2, int(maxBoards * self.myBoardDist[boardKey]))
                mostLikelyBoards = set(list(sorted(dist, key=dist.get, reverse=True))[:maxBoardsForDist-1])
                mostLikelyBoards.add(boardKey)
                newOppBoardDist = {board : dist[board] for board in mostLikelyBoards}
                newOppBoardDists[boardKey] = normalize(newOppBoardDist, adjust=True)
            self.oppBoardDists = newOppBoardDists
        self._check_invariants()

    def _remove_impossible_boards(dist, impossibleBoards):
        for board in impossibleBoards:
            del dist[board]
        normalize(dist, adjust=True)

    def _boardDist_works(dist, color):
        pieces = without_pieces(chess.Board(list(dist.keys())[0]), color).fen()
        if not all(pieces == without_pieces(chess.Board(x), color).fen() for x in dist.keys()):
            fens = set()
            for x in dist.keys():
                fens.add(without_pieces(chess.Board(x), color).fen())
            return False
        return True
    
    def _check_invariants(self):
        # return
        startTime = time.time()
        if not (len(set(self.oppBoardDists.keys()).intersection(self.myBoardDist.keys())) == len(self.myBoardDist) == len(self.oppBoardDists)):
            assert False, (
                "Keys should always match between myBoardDist and oppBoardDists"
                + f"\nself.catchingUp: {self.catchingUp}"
                + f"\nonly in oppBoardDist: {set(self.oppBoardDists.keys()).difference(self.myBoardDist.keys())}"
                + f"\nonly in myBoardDist: {set(self.myBoardDist.keys()).difference(self.oppBoardDists.keys())}"
            )
        for fen, boardDist in self.oppBoardDists.items():
            if len(boardDist) == 0:
                continue
            works = BeliefState._boardDist_works(boardDist, self.color)
            if not works:
                print(fen)
                assert False, "Board dist pieces should be consistent for one side"
        if len(self.myBoardDist)>0 and abs(1 - sum(self.myBoardDist.values())) >= .0001:
            print(self.myBoardDist)
            print(sum(self.myBoardDist.values()))
            assert False, "board dist values should always sum to 1"
        for dist in self.oppBoardDists.values():
            if len(dist)>0:
                assert abs(1-sum(dist.values())) < .0001
        endTime = time.time()
        # print(f"Checked invariants in {endTime - startTime} seconds")

    def display(self, stash=None):
        print(f'\tMY BOARD DISTRIBUTION: ({len(self.myBoardDist)})')
        sortedFens = list(sorted(self.myBoardDist, key=self.myBoardDist.get))
        for fen in sortedFens:
            prob = self.myBoardDist[fen]
            # if prob > .05:
            print('\t\t', fen, '\tprobability:', prob)
        if stash != None:
            print(f"Additional {len(stash)} boards stashed.")
        # print(f'\tOPP\'S BOARD DISTS ({len(self.oppBoardDists)}):')
        # for fen, dist in self.oppBoardDists.items():
        #     print('\t\t', fen)
        #     for (sub_fen, prob) in dist.items():
        #         print('\t\t\t', sub_fen, '\tprobability:', prob)