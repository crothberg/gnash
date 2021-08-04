import os
from reconchess import load_player, play_local_game, LocalGame
import reconchess
import chess
from bots.gnash_bot import GnashBot
from bots.trout_bot import TroutBot

SECONDS_PER_PLAYER = 900

os.environ['STOCKFISH_EXECUTABLE'] = os.path.dirname(os.path.realpath(__file__)) + '/stockfish/stockfish_14_x64_avx2.exe'
game = LocalGame(SECONDS_PER_PLAYER)

trout = TroutBot()
gnash = GnashBot()

trout.handle_game_start(chess.WHITE, game.board.copy(), 'Trout')
gnash.handle_game_start(chess.BLACK, game.board.copy(), 'Gnash')
game.start()

reconchess.play_move(game, trout, game.move_actions())
reconchess.notify_opponent_move_results(game, gnash)
reconchess.play_sense(game, gnash, game.sense_actions(), game.move_actions())
# reconchess.play_move(game, gnash, game.move_actions())

game.end()
winner_color = game.get_winner_color()
win_reason = game.get_win_reason()
game_history = game.get_game_history()

trout.handle_game_end(winner_color, win_reason, game_history)
gnash.handle_game_end(winner_color, win_reason, game_history)

# reconchess.play_sense(game, gnash)

# winner_color, win_reason, history = play_local_game(gnash_bot.GnashBot(), trout_bot.TroutBot(), game=game)
# history.save('games/game.json')
