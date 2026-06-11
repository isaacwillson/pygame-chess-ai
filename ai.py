import random
from pieces import PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, WHITE, BLACK
from pieces import PIECE_VALUES, PIECE_TABLES
from moveGen import generate_legal_moves
from board import Board

INF = float('inf')

# Depth per difficulty: 0=Easy(random), 1=Medium(d3), 2=Hard(d5)
DEPTHS = [1, 3, 5]


def get_ai_move(board, difficulty):
    depth = DEPTHS[difficulty]
    if depth == 0:
        moves = generate_legal_moves(board)
        if moves:
            return random.choice(moves)
        else:
            return None
    return _search_root(board, depth)


def _search_root(board, depth):
    moves = generate_legal_moves(board)
    if not moves:
        return None
    random.shuffle(moves)  # vary play at same eval

    color = board.turn
    if color == WHITE:
        best_score=-INF
    else:
        best_score=INF

    best_move = moves[0]

    boardCopy=board.copy_board()

    for move in moves:
        boardCopy.make_move(move)
        score = _minimax(boardCopy, depth - 1, -INF, INF, color == BLACK)
        boardCopy.unmake_move()
        if color == WHITE and score > best_score:
            best_score = score
            best_move = move
        elif color == BLACK and score < best_score:
            best_score = score
            best_move = move

    return best_move


def _minimax(board, depth, alpha, beta, maximizing):
    if depth == 0:
        return _evaluate(board)

    moves = generate_legal_moves(board)
    if not moves:  
        return (-INF if maximizing else INF) if board.is_in_check(board.turn) else 0

    if maximizing:
        val = -INF
        for m in moves:
            board.make_move(m)
            val = max(val, _minimax(board, depth - 1, alpha, beta, False))
            board.unmake_move()
            alpha = max(alpha, val)
            if beta <= alpha:
                break
        return val
    else:
        val = INF
        for m in moves:
            board.make_move(m)
            val = min(val, _minimax(board, depth - 1, alpha, beta, True))
            board.unmake_move()
            beta = min(beta, val)
            if beta <= alpha:
                break
        return val


def _evaluate(board):
    score = 0
    for r in range(8):
        for c in range(8):
            p = board.squares[r][c]
            if not p:
                continue
            pt, color = p
            val = PIECE_VALUES[pt]
            table = PIECE_TABLES[pt]
            if table:
                val += table[r][c] if color == WHITE else table[7 - r][c]
            score += val if color == WHITE else -val
    return score
