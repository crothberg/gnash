import os
from reconchess import load_player, play_local_game, LocalGame
from bots import gnash_bot, trout_bot

SECONDS_PER_PLAYER = 900

os.environ['STOCKFISH_EXECUTABLE'] = os.path.dirname(os.path.realpath(__file__)) + '/stockfish/stockfish_14_x64_avx2.exe'
game = LocalGame(SECONDS_PER_PLAYER)

winner_color, win_reason, history = play_local_game(gnash_bot.GnashBot(), trout_bot.TroutBot(), game=game)
history.save('games/game.json')
