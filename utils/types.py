from typing import List, Tuple, Optional, Type
from reconchess import *

Fen = str
Probability = float
BoardDist = {Fen: Probability}
SquareDist = {Square: Probability}

SenseMove = int