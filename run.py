from multiprocessing import freeze_support

def main():
    import os
    import traceback, sys
    from reconchess import load_player, play_local_game, LocalGame
    import reconchess
    import chess
    from gnash_bot import GnashBot
    from reconchess.bots.trout_bot import TroutBot
    from reconchess.bots.random_bot import RandomBot
    from reconchess.bots.attacker_bot import AttackerBot

    SECONDS_PER_PLAYER = 900

    game = LocalGame(SECONDS_PER_PLAYER)

    # white = GnashBot(isTest=True)
    white = RandomBot()
    # white = AttackerBot()
    # white = TroutBot()
    black = GnashBot(isTest=True)

    # opponent.handle_game_start(chess.WHITE, game.board.copy(), 'Trout')
    # gnash.handle_game_start(chess.BLACK, game.board.copy(), 'Gnash')
    # game.start()

    # try:
    #     reconchess.play_move(game, opponent, game.move_actions())
    #     reconchess.notify_opponent_move_results(game, gnash)
    #     reconchess.play_sense(game, gnash, game.sense_actions(), game.move_actions())
    #     reconchess.play_move(game, gnash, game.move_actions())
    #     reconchess.notify_opponent_move_results(game, opponent)
    #     reconchess.play_sense(game, opponent, game.sense_actions(), game.move_actions())
    #     reconchess.play_move(game, opponent, game.move_actions())
    #     reconchess.notify_opponent_move_results(game, gnash)
    # except Exception as e:
    #     traceback.print_exc(file=sys.stdout)

    # game.end()
    # winner_color = game.get_winner_color()
    # win_reason = game.get_win_reason()
    # game_history = game.get_game_history()

    # opponent.handle_game_end(winner_color, win_reason, game_history)
    # gnash.handle_game_end(winner_color, win_reason, game_history)

    # reconchess.play_sense(game, gnash)

    winner_color, win_reason, history = play_local_game(white, black, game=game)
    history.save('games/game.json')

if __name__ == '__main__':
    freeze_support()
    main()