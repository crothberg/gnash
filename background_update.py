import os
import chess
import flask

from flask import Flask, request

from gnash_bot import GnashBot
import json
import time

os.environ['FORKED_BY_MULTIPROCESSING'] = '1'

'''
celery -A background_update.celery worker --loglevel=info
'''

app = Flask(__name__)

all_games = {}

class Game:
    def __init__(self, color, board, oppName, game_id):
        self.bot = GnashBot()
        print('handling game start...')
        print(type(color), type(board), type(oppName))
        self.bot.handle_game_start(color, board, oppName, background=True)
        self.bot.game_id = game_id
        print('done!')
    # async def start_expansion_loop(self):
    #     print('Starting expansion loop...')
    #     while True:
    #         print('Expanding stashed boards...')
    #         # self.bot._expand_stashed_boards()
    #         time.sleep(5)
    def add_boards(self, boards, turn):
        pass
    def get_history(self, turn, new_history):
        return self.bot.history[turn].append(new_history)
    def get_possible_boards(self):
        return self.bot.beliefState.myBoardDist
    
'''
stash:
0. {}
1. {b2, b3, b4, b5}
2. {b19, b20, b21, b15, b16}
'''

'''
service's version:
boardDist = {b50, b51}
'''

'''
history:
0. [oppMoveResult, senseResult, ourMoveResult]
1. [oppMoveResult, senseResult, ourMoveResult]
2. [oppMoveResult]
'''

@app.route('/create_game', methods=['POST'])
def create_game():
    # Get args
    game_id = request.form.get('game_id')
    color = request.form.get('color')
    board = chess.Board(request.form.get('board'))
    oppName = request.form.get('oppName')
    # Create game
    print('About to create a new game...')
    game = Game(color, board, oppName, game_id)
    print('Game created!')
    all_games[game_id] = game
    print(f'Started game with id {game_id}')
    # asyncio.run(game.start_expansion_loop())
    print(f'Started expansion loop for game with id {game_id}')
    return json.dumps({'id': game_id})

@app.route('/add_boards_to_stash', methods=['POST'])
def add_boards_to_stash():
    # Get args
    game_id = request.form.get('game_id')
    boards = request.form.get('boards')
    turn = request.form.get('turn')
    game = all_games[game_id]
    # Add boards
    game.add_boards(boards, turn)
    return flask.Response(status=200)

@app.route('/add_history')
def add_history():
    # Get args
    game_id = request.args.get('game_id')
    new_history = request.args.get('new_history')
    turn = request.args.get('turn')
    # Add history
    game = all_games[game_id]
    game.add_history(turn, new_history)
    return flask.Response(status=200)

@app.route('/get_possible_boards')
def get_possible_boards():
    # Get args
    game_id = request.args.get('game_id')
    turn = request.args.get('turn')
    # Get boards
    game = all_games[game_id]
    boards = game.get_possible_boards(turn)
    return boards

@app.route('/destroy_game')
def destroy_game():
    game_id = request.args.get('game_id')
    del all_games[game_id]
    return flask.Response(status=200)

if __name__ == '__main__':
    app.run(debug=True)