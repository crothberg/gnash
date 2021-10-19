from os import name


profiles = {
    #us and them
    "oracle": (.1, .1), #this seems to be very solid
    "random": (1.0, None),
    "RandomBot": (1.0, None),
    "attacker": (.1, None),
    "AttackBot": (.1, None),
    "penumbra": (.7, .85),
    "Fianchetto": (.8, .1),
    "StrangeFish2": (.7, 0), #wins some loses some, good enough for now
    "trout": (1, 0), #this is solid.
    "TroutBot": (None, None),
    "default": (.7, .5)
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
    return gUs, gThem, giveFrivChecks