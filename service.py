from flask import Flask, jsonify, request
from game.BeliefState import BeliefState
from game.Stash import Stash
from utils.history_utils import *
import chess

app = Flask(__name__)

stashes = dict()

def handle_game_start(color, gameId):
    stash = Stash(color)
    stashes[gameId] = stash
    stash.start_background_processor()

@app.route("/start/<gameId>", methods=['POST'])
def start(gameId):
    content = request.json
    handle_game_start(content["color"], gameId)
    return jsonify({"Error":None})

@app.route("/add_our_move_result/<gameId>/<turn>/<phase>", methods=['POST'])
def add_our_move_result(gameId, turn, phase):
    try:
        turn, phase = int(turn), Phase(int(phase))
        content = request.json
        result = chess.Move.from_uci(content["reqMove"]) if content["reqMove"] is not None else None, chess.Move.from_uci(content["takMove"]) if content["takMove"] is not None else None, content["capOppPiece"], content["capSquare"]
        stashes[gameId].add_history(turn, phase, result)
        return jsonify({"Error":None})
    except:
        return

@app.route("/add_opp_move_result/<gameId>/<turn>/<phase>", methods=['POST'])
def add_opp_move_result(gameId, turn, phase):
    try:
        turn, phase = int(turn), Phase(int(phase))
        content = request.json
        result = content["capMyPiece"], content["capSquare"]
        stashes[gameId].add_history(turn, phase, result)
        return jsonify({"Error":None})
    except:
        return

@app.route("/add_sense_result/<gameId>/<turn>/<phase>", methods=['POST'])
def add_sense_result(gameId, turn, phase):
    try:
        turn, phase = int(turn), Phase(int(phase))
        content = request.json
        squares, pieces = content["squares"], content["pieces"]
        pieces = [chess.Piece.from_symbol(piece) if piece is not None else None for piece in pieces]
        senseResult = [(square, piece) for square, piece in zip(squares, pieces)]
        stashes[gameId].add_history(turn, phase, senseResult)
        return jsonify({"Error":None})
    except:
        return

@app.route("/get_possible_boards/<gameId>", methods=['POST'])
def get_possible_boards(gameId):
    try:
        stash = stashes[gameId]
        beliefState = BeliefState(stash.color)
        beliefState.myBoardDist = {}
        beliefState.oppBoardDists = {}
        numBoards = request.json["numBoards"]
        timeRemaining = float(request.json["extraTime"])
        rescueBoard = stash.add_possible_boards(beliefState, numBoards, urgent=True, timeRemaining=timeRemaining)
        if rescueBoard == None:
            return jsonify({"useHelperBot": False, "fens":list(beliefState.myBoardDist.keys())})
        else:
            return jsonify({"useHelperBot":True, "helperBotFen": rescueBoard})
    except:
        return jsonify({"fens":[]})

@app.route("/stash_boards/<gameId>/<turn>/<phase>", methods = ['POST'])
def stash_boards(gameId, turn, phase):
    try:
        turn, phase = int(turn), Phase(int(phase))
        stash = stashes[gameId]
        boards = request.json["boardsToStash"]
        bestBoard = request.json["bestBoard"]
        beliefState = BeliefState(stash.color)
        beliefState.myBoardDist = {b: 1/len(b) for b in boards}
        beliefState.oppBoardDists = {b : {b : 1} for b in boards}
        stash.stash_boards(phase, turn, beliefState, 0, bestBoard = bestBoard)
        return jsonify({"Error":None})
    except:
        return

@app.route("/game_over/<gameId>", methods = ['POST'])
def end_game(gameId):
    return jsonify({"Error":None})
        
if __name__ == "__main__":
    app.run(debug=False)