import os
import threading
import traceback
import chess.engine
import sys
import utils.parallelism_utils as parallel

os.environ['STOCKFISH_EXECUTABLE'] = os.path.dirname(os.path.realpath(__file__)) + '/../stockfish/stockfish_14_x64_avx2.exe'
STOCKFISH_ENV_VAR = 'STOCKFISH_EXECUTABLE'

# make sure stockfish environment variable exists
if STOCKFISH_ENV_VAR not in os.environ:
    raise KeyError(
        'Gnash requires an environment variable called "{}" pointing to the Stockfish executable'.format(
            STOCKFISH_ENV_VAR))

# make sure there is actually a file
stockfish_path = os.environ[STOCKFISH_ENV_VAR]
if not os.path.exists(stockfish_path):
    raise ValueError('No stockfish executable found at "{}"'.format(stockfish_path))

class EngineGroup:
    nextId = 0
    engines = dict()
    availableEngines = set()
    lock = threading.Lock()
    def add_engine():
        new_engine = chess.engine.SimpleEngine.popen_uci(stockfish_path, setpgrp=True)
        engineId = EngineGroup.nextId
        EngineGroup.nextId += 1
        # print(f'Added new engine {engineId}', flush=True)
        EngineGroup.engines[engineId] = new_engine
        EngineGroup.availableEngines.add(engineId)
    def get_available_engine():
        EngineGroup.lock.acquire()
        if len(EngineGroup.availableEngines) == 0:
            EngineGroup.add_engine()
            # print(f'Engine list is now {EngineGroup.engines}', flush=True)
        engineId = EngineGroup.availableEngines.pop()
        EngineGroup.lock.release()
        return EngineGroup.engines[engineId], engineId
    def release_engine(engineId):
        EngineGroup.lock.acquire()
        EngineGroup.availableEngines.add(engineId)
        EngineGroup.lock.release()
    def shut_down():
        engine_list = list(EngineGroup.engines.keys())
        for engineId in engine_list:
            EngineGroup.engines[engineId].quit()
            del EngineGroup.engines[engineId]
            EngineGroup.availableEngines.remove(engineId)

def shut_down_engines():
    print('Shutting down all engines...')
    EngineGroup.shut_down()

def play(board, maxTime, movesToConsider=None):
    # print('Starting play...')
    engine, engineId = EngineGroup.get_available_engine()
    if movesToConsider != None:
        play = engine.play(board, chess.engine.Limit(maxTime), root_moves=movesToConsider)
    else:
        play = engine.play(board, chess.engine.Limit(maxTime))
    EngineGroup.release_engine(engineId)
    # print('Play complete!')
    return play
    
def analyse(board, maxTime):
    # print('Starting analysis...', flush=True)
    engine, engineId = EngineGroup.get_available_engine()
    analysis = engine.analyse(board, chess.engine.Limit(maxTime))
    EngineGroup.release_engine(engineId)
    # print('Analysis complete!', flush=True)
    return analysis

def quit_on_exceptions(func):
    def inner_function(*args, **kwargs):
        try:
            sys.stdout.flush()
            sys.stderr.flush()
            return func(*args, **kwargs)
        except Exception as e:
            print(traceback.format_exc())
            shut_down_engines()
            parallel.clean_up()
            raise Exception(e)
        finally:
            sys.stdout.flush()
            sys.stderr.flush()

    return inner_function