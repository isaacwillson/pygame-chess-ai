from pieces import PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, WHITE, BLACK
from board import Move


def generate_legal_moves(board, color=None):
    if color is None:
        color = board.turn
    legal = []
    for move in _pseudo_legal(board, color):
        board.make_move(move)
        if not board.is_in_check(color):
            legal.append(move)
        board.unmake_move()
    return legal


def _pseudo_legal(board, color):
    moves = []
    for r in range(8):
        for c in range(8):
            p = board.squares[r][c]
            if not p or p[1] != color:
                continue
            pt = p[0]
            if pt == PAWN:
                moves.extend(_pawn(board, r, c, color))
            elif pt == KNIGHT:
                moves.extend(_knight(board, r, c, color))
            elif pt == BISHOP:
                moves.extend(_slider(board, r, c, color, ((-1,-1),(-1,1),(1,-1),(1,1))))
            elif pt == ROOK:
                moves.extend(_slider(board, r, c, color, ((-1,0),(1,0),(0,-1),(0,1))))
            elif pt == QUEEN:
                moves.extend(_slider(board, r, c, color,
                    ((-1,-1),(-1,1),(1,-1),(1,1),(-1,0),(1,0),(0,-1),(0,1))))
            elif pt == KING:
                moves.extend(_king(board, r, c, color))
    return moves


def _pawn(board, r, c, color):
    moves = []
    d = -1 if color == WHITE else 1       # forward direction
    start = 6 if color == WHITE else 1    # starting row
    promo_row = 0 if color == WHITE else 7

    nr = r + d
    if 0 <= nr < 8:
        # Single push
        if board.squares[nr][c] is None:
            _add_pawn_move(moves, r, c, nr, c, promo_row)
            # Double push from start
            if r == start:
                nr2 = r + 2 * d
                if board.squares[nr2][c] is None:
                    moves.append(Move((r, c), (nr2, c)))
        # Captures
        for dc in (-1, 1):
            nc = c + dc
            if 0 <= nc < 8:
                target = board.squares[nr][nc]
                if target and target[1] != color:
                    _add_pawn_move(moves, r, c, nr, nc, promo_row)
                elif board.en_passant_sq == (nr, nc):
                    moves.append(Move((r, c), (nr, nc), is_en_passant=True))
    return moves


def _add_pawn_move(moves, fr, fc, tr, tc, promo_row):
    if tr == promo_row:
        for promo in (QUEEN, ROOK, BISHOP, KNIGHT):
            moves.append(Move((fr, fc), (tr, tc), promotion=promo))
    else:
        moves.append(Move((fr, fc), (tr, tc)))


def _knight(board, r, c, color):
    moves = []
    for dr, dc in ((-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < 8 and 0 <= nc < 8:
            t = board.squares[nr][nc]
            if not t or t[1] != color:
                moves.append(Move((r, c), (nr, nc)))
    return moves


def _slider(board, r, c, color, dirs):
    moves = []
    for dr, dc in dirs:
        nr, nc = r + dr, c + dc
        while 0 <= nr < 8 and 0 <= nc < 8:
            t = board.squares[nr][nc]
            if t:
                if t[1] != color:
                    moves.append(Move((r, c), (nr, nc)))
                break
            moves.append(Move((r, c), (nr, nc)))
            nr += dr; nc += dc
    return moves


def _king(board, r, c, color):
    moves = []
    for dr, dc in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < 8 and 0 <= nc < 8:
            t = board.squares[nr][nc]
            if not t or t[1] != color:
                moves.append(Move((r, c), (nr, nc)))

    # Castling — only when king is on its home square
    back = 7 if color == WHITE else 0
    if r != back or c != 4:
        return moves
    opp = 1 - color

    # Kingside
    ks_key = 'K' if color == WHITE else 'k'
    if (board.castling_rights.get(ks_key) and
            board.squares[back][5] is None and
            board.squares[back][6] is None and
            not board.is_attacked((back, 4), opp) and
            not board.is_attacked((back, 5), opp) and
            not board.is_attacked((back, 6), opp)):
        moves.append(Move((r, c), (back, 6), castling_side=ks_key))

    # Queenside
    qs_key = 'Q' if color == WHITE else 'q'
    if (board.castling_rights.get(qs_key) and
            board.squares[back][1] is None and
            board.squares[back][2] is None and
            board.squares[back][3] is None and
            not board.is_attacked((back, 4), opp) and
            not board.is_attacked((back, 3), opp) and
            not board.is_attacked((back, 2), opp)):
        moves.append(Move((r, c), (back, 2), castling_side=qs_key))

    return moves
