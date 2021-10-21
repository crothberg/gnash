profiles = {
    #us and them
    "Oracle": (1, .25),
    "random": (1.0, None),
    "RandomBot": (1.0, None),
    "attacker": (.1, 1),
    "AttackBot": (.1, 1),
    "penumbra": (.7, 1),
    # "Fianchetto": (0, 0), #best bet so far
    "Fianchetto": (1, 0), #experimental
    # "Fianchetto": (.5, 0), #experimental (just okay)
    "StrangeFish2": (.5, .1), #experimental
    # "StrangeFish2": (.5, 0), #experimental (0/1)
    # "StrangeFish2": (0, 0),#experimental (0/1) (but didn't seem terrible)
    # "StrangeFish2": (.5, 1), #experimental (fail?)
    # "StrangeFish2": (0.01, 1), #has a win at least but not clear how many, turn off experimental if using
    # # "StrangeFish2": (1, 1), #best bet so far (but pretty untested)
    "trout": (1, 0), #this is solid.
    "TroutBot": (1, 0),
    "TimoBertram": (.1, 0),
    # "Kevin": (1, 1.3), #nothing is working against Kevin!
    "Kevin": (1,1),
    "Marmot": (.5, .1),
    "Frampt": (0, 1.5),
    "default": (.1, 1)
}

onlyGivesCheckBots = {
    "Marmot",
    "DynamicEntropy",
    "theAgent",
    # "penumbra",
    "Frampt",
    "StrangeFish2",
    # "Oracle"
}

giveFrivChecksTo = {
    "trout",
    "TroutBot",
    "attacker",
    "AttackBot",
    "TimoBertram",
    "random",
    "RandomBot",
    "Kevin",
}

defaultBelievedOurGambleFactor = .25

def get_gamble_factor(name):
    gUs, gThem = profiles[name] if name in profiles else profiles["default"]
    if gUs is None:
        gUs = profiles["default"][0]
    if gThem is None:
        gThem = profiles["default"][1]
    giveFrivChecks = name in giveFrivChecksTo
    onlyGivesChecks = name in onlyGivesCheckBots
    return gUs, gThem, giveFrivChecks, onlyGivesChecks