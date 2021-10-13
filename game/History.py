from game.BeliefState import BeliefState
from utils.history_utils import *
from utils.util import *

class History:
    def __init__(self):
        #opponent_move_result, sense_result, move_result
        #for every turn
        self.history = dict()

        
    def __str__(self):
        print("History:")
        for level in self.history:
            for phase in self.history[level]:
                print(level, phase)
                print(self.history[level][phase])
        return ''

    def get_history(self, turn : int, phase : Phase):
        assert self.has_history(phase, turn)
        return self.history[turn][phase]

    def get_current_phase_and_turn(self):
        lastTurn = max(self.history.keys())
        lastPhase = Phase(max(phase.value for phase in self.history[lastTurn].keys()))
        return lastPhase, lastTurn

    def get_future_phase_and_turn(self):
        curPhase, curTurn = self.get_current_phase_and_turn()
        return get_next_phase_and_turn(curPhase, curTurn)

    def add_history(self, turn : int, phase : Phase, result):
        if turn not in self.history: self.history[turn] = dict()
        self.history[turn][phase] = result

    def has_history(self, phase : Phase, turn : int):
        return turn in self.history and phase in self.history[turn]

    def apply_history(self, beliefState : BeliefState, phase : Phase, turn: int):
        assert self.has_history(phase, turn)
        history = self.history[turn][phase]
        if phase == Phase.OPP_MOVE_RESULT:
            captured_my_piece, capture_square = history
            beliefState.opp_move_result_update(captured_my_piece, capture_square, maxTime = 0.001)
        elif phase == Phase.SENSE_RESULT:
            senseResult = history
            beliefState.sense_update(senseResult, maxTime = 0.001)
        elif phase == Phase.OUR_MOVE_RESULT:
            requested_move, taken_move, captured_opponent_piece, capture_square = history
            beliefState.our_move_result_update(requested_move, taken_move, captured_opponent_piece, capture_square, maxTime = .001)