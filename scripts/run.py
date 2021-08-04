import os
import subprocess

os.environ['STOCKFISH_EXECUTABLE'] = os.path.dirname(os.path.realpath(__file__)) + '/../stockfish/stockfish_14_x64_avx2.exe'
subprocess.run(['rc-bot-match', 'reconchess.bots.random_bot', 'bots/gnash_bot.py'])