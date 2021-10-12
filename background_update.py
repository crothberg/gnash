import os
# os.environ['FORKED_BY_MULTIPROCESSING'] = '1'

import chess
import flask

from flask import Flask, request, url_for
from celery import Celery

# from gnash_bot import GnashBot
import json
import time

'''
SETUP INSTRUCTIONS:
1. pip install celery, flask, gevent
2. Download redis (https://github.com/microsoftarchive/redis/releases/tag/win-3.0.504)
3. Start a redis server (redis-server.exe)
4. Run `celery -A background_update.celery worker -l info -P gevent`
5. Run `python background-update.py`
6. You can now access background processes on the server
'''

app = Flask(__name__)
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['RESULT_BACKEND'] = 'redis://localhost:6379/0'

celery = Celery(app.name, backend=app.config['RESULT_BACKEND'], broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

@celery.task(bind=True)
def long_task(self):
    for i in range(15):
        time.sleep(1)
        self.update_state(state='PROGRESS', meta={'current': i, 'total': 15, 'status': 'message here'})
    return {'current': 15, 'total': 15, 'status': 'Task completed!', 'result': 42}

@app.route('/status/<task_id>')
def taskstatus(task_id):
    task = long_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        # job did not start yet
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return json.dumps(response)

@app.route('/longtask', methods=['GET'])
def longtask():
    task = long_task.apply_async()
    return flask.Response(json.dumps({}), 202, {'Location': url_for('taskstatus', task_id=task.id)})

all_games = {}
"""
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
"""
if __name__ == '__main__':
    app.run(debug=True)