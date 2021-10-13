from enum import Enum

class Phase(Enum):
    OPP_MOVE_RESULT = 0
    SENSE_RESULT = 1
    OUR_MOVE_RESULT = 2

PHASES = (Phase(0), Phase(1), Phase(2))

def get_stash_size(stash):
    total = 0
    for turn in stash.values():
        for phase in PHASES:
            if phase in turn: total += len(turn[phase])
    return total
    
def get_next_phase_and_turn(phase : Phase, turn : int):
    phase = phase.value
    phase += 1
    if phase == 3:
        phase = 0
        turn += 1
    phase = Phase(phase)
    return phase, turn

def get_prev_phase_and_turn(phase : Phase, turn : int):
    phase = phase.value
    phase -= 1
    if phase < 0:
        phase = 2
        turn -= 1
    phase = Phase(phase)
    return phase, turn