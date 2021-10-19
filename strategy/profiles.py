from os import name


profiles = {
    #us and them
    "oracle": (.7, 0),
    "random": (1.0, None),
    "RandomBot": (1.0, None),
    "attacker": (.1, 1.5),
    "AttackBot": (.1, 1.5),
    "penumbra": (.7, .85),
    "Fianchetto": (.8, .1),
    "StrangeFish2": (.7, 0),
    "trout": (.7, .1),
    "TroutBot": (.7, .1),
    "default": (.7, .1)
}

def get_gamble_factor(name):
    gUs, gThem = profiles[name] if name in profiles else profiles["default"]
    if gUs is None:
        gUs = profiles["default"][0]
    if gThem is None:
        gThem = profiles["default"][1]
    return gUs, gThem