from pieces import (PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
                    WHITE, BLACK, PIECE_SYMBOLS, FILE_NAMES)


class Move:
    __slots__ = ('from_sq', 'to_sq', 'promotion', 'is_en_passant', 'castling_side',
                 'captured_piece', 'prev_en_passant', 'prev_castling_rights',
                 'prev_halfmove', 'piece_type')

    def __init__(self, from_sq, to_sq, promotion=None,
                 is_en_passant=False, castling_side=None):
        self.from_sq = from_sq        # (row, col)
        self.to_sq = to_sq
        self.promotion = promotion    # KNIGHT/BISHOP/ROOK/QUEEN or None
        self.is_en_passant = is_en_passant
        self.castling_side = castling_side  # 'K','Q','k','q' or None
        # Filled in by make_move for unmake_move
        self.captured_piece = None
        self.prev_en_passant = None
        self.prev_castling_rights = None
        self.prev_halfmove = None
        self.piece_type = None

    def to_uci(self):
        fr, fc = self.from_sq
        tr, tc = self.to_sq
        s = FILE_NAMES[fc] + str(8 - fr) + FILE_NAMES[tc] + str(8 - tr)
        if self.promotion:
            s += PIECE_SYMBOLS[self.promotion].lower()
        return s


class Board:
    def __init__(self):
        self.squares = [[None] * 8 for _ in range(8)]
        self.turn = WHITE
        self.castling_rights = {'K': True, 'Q': True, 'k': True, 'q': True}
        self.en_passant_sq = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.history = []
        self._setup_initial_position()

    def _setup_initial_position(self):
        back_rank = [ROOK, KNIGHT, BISHOP, QUEEN, KING, BISHOP, KNIGHT, ROOK]
        for col, pt in enumerate(back_rank):
            self.squares[0][col] = (pt, BLACK)
            self.squares[7][col] = (pt, WHITE)
        for col in range(8):
            self.squares[1][col] = (PAWN, BLACK)
            self.squares[6][col] = (PAWN, WHITE)

    def copy_board(self):
        boardCopy=Board()

        for r in range(8):
            for c in range(8):
                p=self.squares[r][c]
                boardCopy.set_square(r,c,p)

        boardCopy.turn=self.turn
        boardCopy.castling_rights=self.castling_rights 
        boardCopy.en_passant_sq=self.en_passant_sq
        boardCopy.halfMove_clock=self.halfmove_clock
        boardCopy.fullMove_number=self.fullmove_number
        boardCopy.history=self.history
        return boardCopy

    # ------------------------------------------------------------------
    # Make / Unmake
    # ------------------------------------------------------------------
    def set_square(self,r,c,value):
        self.squares[r][c]=value
        
    def make_move(self, move):
        fr, fc = move.from_sq
        tr, tc = move.to_sq
        piece = self.squares[fr][fc]
        piece_type, piece_color = piece

        move.captured_piece = self.squares[tr][tc]
        move.prev_en_passant = self.en_passant_sq
        move.prev_castling_rights = dict(self.castling_rights)
        move.prev_halfmove = self.halfmove_clock
        move.piece_type = piece_type

        # En passant capture: remove the captured pawn
        if move.is_en_passant:
            ep_cap_row = tr + (1 if piece_color == WHITE else -1)
            move.captured_piece = self.squares[ep_cap_row][tc]
            self.squares[ep_cap_row][tc] = None

        # Move piece (handle promotion)
        self.squares[fr][fc] = None
        self.squares[tr][tc] = (move.promotion, piece_color) if move.promotion else piece

        # Move rook for castling
        if move.castling_side:
            if move.castling_side in ('K', 'k'):
                self.squares[fr][5] = self.squares[fr][7]
                self.squares[fr][7] = None
            else:
                self.squares[fr][3] = self.squares[fr][0]
                self.squares[fr][0] = None

        # Update castling rights
        if piece_type == KING:
            if piece_color == WHITE:
                self.castling_rights['K'] = self.castling_rights['Q'] = False
            else:
                self.castling_rights['k'] = self.castling_rights['q'] = False
        if piece_type == ROOK:
            _rook_cr_update(self.castling_rights, fr, fc, 'remove')
        if move.captured_piece and move.captured_piece[0] == ROOK:
            _rook_cr_update(self.castling_rights, tr, tc, 'remove')

        # En passant target square
        self.en_passant_sq = None
        if piece_type == PAWN and abs(tr - fr) == 2:
            self.en_passant_sq = ((fr + tr) // 2, fc)

        # Clocks
        if piece_type == PAWN or move.captured_piece:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        if self.turn == BLACK:
            self.fullmove_number += 1
        self.turn = BLACK if self.turn == WHITE else WHITE

        self.history.append(move)

    def unmake_move(self):
        if not self.history:
            return
        move = self.history.pop()
        fr, fc = move.from_sq
        tr, tc = move.to_sq

        # Switch turn back
        self.turn = BLACK if self.turn == WHITE else WHITE
        if self.turn == BLACK:
            self.fullmove_number -= 1

        piece = self.squares[tr][tc]
        _, piece_color = piece

        # Restore origin square (undo promotion)
        self.squares[fr][fc] = (PAWN, piece_color) if move.promotion else piece

        # Restore destination
        if move.is_en_passant:
            self.squares[tr][tc] = None
            ep_cap_row = tr + (1 if piece_color == WHITE else -1)
            self.squares[ep_cap_row][tc] = move.captured_piece
        else:
            self.squares[tr][tc] = move.captured_piece

        # Restore rook for castling
        if move.castling_side:
            if move.castling_side in ('K', 'k'):
                self.squares[fr][7] = self.squares[fr][5]
                self.squares[fr][5] = None
            else:
                self.squares[fr][0] = self.squares[fr][3]
                self.squares[fr][3] = None

        self.en_passant_sq = move.prev_en_passant
        self.castling_rights = move.prev_castling_rights
        self.halfmove_clock = move.prev_halfmove

    # ------------------------------------------------------------------
    # Check / attack detection
    # ------------------------------------------------------------------

    def is_in_check(self, color):
        for r in range(8):
            for c in range(8):
                p = self.squares[r][c]
                if p and p[0] == KING and p[1] == color:
                    return self.is_attacked((r, c), 1 - color)
        return False

    def is_attacked(self, sq, by_color):
        r, c = sq
        opp = by_color

        # Pawns
        pawn_dr = 1 if opp == WHITE else -1
        for dc in (-1, 1):
            pr, pc = r + pawn_dr, c + dc
            if 0 <= pr < 8 and 0 <= pc < 8:
                p = self.squares[pr][pc]
                if p and p[0] == PAWN and p[1] == opp:
                    return True

        # Knights
        for dr, dc in ((-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                p = self.squares[nr][nc]
                if p and p[0] == KNIGHT and p[1] == opp:
                    return True

        # Bishops / Queens (diagonals)
        for dr, dc in ((-1,-1),(-1,1),(1,-1),(1,1)):
            nr, nc = r + dr, c + dc
            while 0 <= nr < 8 and 0 <= nc < 8:
                p = self.squares[nr][nc]
                if p:
                    if p[1] == opp and p[0] in (BISHOP, QUEEN):
                        return True
                    break
                nr += dr; nc += dc

        # Rooks / Queens (straight)
        for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
            nr, nc = r + dr, c + dc
            while 0 <= nr < 8 and 0 <= nc < 8:
                p = self.squares[nr][nc]
                if p:
                    if p[1] == opp and p[0] in (ROOK, QUEEN):
                        return True
                    break
                nr += dr; nc += dc

        # King
        for dr, dc in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                p = self.squares[nr][nc]
                if p and p[0] == KING and p[1] == opp:
                    return True

        return False

    # ------------------------------------------------------------------
    # Game status
    # ------------------------------------------------------------------

    def get_game_status(self, legal_moves):
        if not legal_moves:
            return 'checkmate' if self.is_in_check(self.turn) else 'stalemate'
        if self.halfmove_clock >= 100:
            return 'draw_50move'
        return 'ongoing'


def _rook_cr_update(cr, r, c, action):
    mapping = {(7, 7): 'K', (7, 0): 'Q', (0, 7): 'k', (0, 0): 'q'}
    key = mapping.get((r, c))
    if key:
        cr[key] = False
