from os import name

profiles = {
    #us and them
    "Oracle": (1, 0),
    "random": (1.0, None),
    "RandomBot": (1.0, None),
    "attacker": (.1, 1),
    "AttackBot": (.1, 1),
    "penumbra": (.7, 1),
    # "Fianchetto": (0, 0), #looks really good!
    "Fianchetto": (.5,0), #experimental
    # "StrangeFish2": (.7, 0), #wins some loses some, good enough for the tournament
    "StrangeFish2": (.5, .5), #experimental
    # "StrangeFish2": (.5, 0), #experimental (0/1)
    # "StrangeFish2": (0, 0),#experimental (0/1) (but didn't seem terrible)
    # "StrangeFish2": (1, 1), #experimental: wins sometimes
    "trout": (1, 0), #this is solid.
    "TroutBot": (None, None),
    "default": (.1, 1)
}

onlyGivesCheckBots = {
    "attacker",
    "AttackBot",
    "DynamicEntropy"
}

giveFrivChecksTo = {
    "trout",
    "TroutBot",
    "attacker",
    "AttackBot",
    "TimoBertram",
    "random",
    "RandomBot"
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