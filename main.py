import sys
import threading
import pygame
from board import Board
from moveGen import generate_legal_moves
from ai import get_ai_move
from ai import _evaluate
from pieces import (PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
                    WHITE, BLACK, PIECE_SYMBOLS, FILE_NAMES)

# ── Layout ──────────────────────────────────────────────────────────────
W, H = 1040, 700
SQ = 70                       # pixels per square
BOARD_X, BOARD_Y = 50, 60    # top-left of the board
BOARD_PX = SQ * 8            # 560

PANEL_X = BOARD_X + BOARD_PX + 24
PANEL_W = W - PANEL_X - 16

# ── Palette ─────────────────────────────────────────────────────────────
BG          = (22,  27,  34)
SQ_LIGHT    = (240, 217, 181)
SQ_DARK     = (181, 136,  99)
HL_LAST     = (205, 210, 106, 110)   # last-move tint
HL_SEL      = ( 205, 210,  106, 160)   # selected square
HL_LEGAL    = ( 0, 0,  0, 50)   # legal-move dot/ring
HL_CHECK    = (220,  50,  50, 180)   # king in check
PANEL_BG    = ( 30,  36,  46)
BORDER      = ( 60,  70,  90)
TXT         = (210, 215, 225)
TXT_DIM     = (120, 128, 145)
BTN_NORM    = ( 56, 119, 178)
BTN_HOV     = ( 80, 148, 210)
BTN_ACT     = ( 40, 160,  80)
BTN_TXT     = (255, 255, 255)
MV_ROW_A    = ( 38,  44,  56)
MV_ROW_B    = ( 44,  52,  64)
COORD_TXT   = (160, 168, 180)

DIFF_NAMES = ['Easy', 'Medium', 'Hard']
PLAYER = WHITE   # player always plays white


# ── SAN builder ─────────────────────────────────────────────────────────

def build_san(board, move, all_legal):
    if move.castling_side in ('K', 'k'):
        return 'O-O'
    if move.castling_side in ('Q', 'q'):
        return 'O-O-O'

    fr, fc = move.from_sq
    tr, tc = move.to_sq
    p = board.squares[fr][fc]
    if not p:
        return '?'
    pt, color = p
    sym = PIECE_SYMBOLS[pt]
    is_cap = bool(board.squares[tr][tc]) or move.is_en_passant
    dest = FILE_NAMES[tc] + str(8 - tr)

    if pt == PAWN:
        s = (FILE_NAMES[fc] + 'x' + dest) if is_cap else dest
        if move.promotion:
            s += '=' + PIECE_SYMBOLS[move.promotion]
        return s

    # Disambiguation
    ambig = [m for m in all_legal
             if m.to_sq == (tr, tc)
             and m.from_sq != (fr, fc)
             and board.squares[m.from_sq[0]][m.from_sq[1]]
             and board.squares[m.from_sq[0]][m.from_sq[1]][0] == pt]
    dis = ''
    if ambig:
        same_file = any(m.from_sq[1] == fc for m in ambig)
        same_rank = any(m.from_sq[0] == fr for m in ambig)
        if not same_file:
            dis = FILE_NAMES[fc]
        elif not same_rank:
            dis = str(8 - fr)
        else:
            dis = FILE_NAMES[fc] + str(8 - fr)

    cap_str = 'x' if is_cap else ''
    return sym + dis + cap_str + dest


# ── Game state ───────────────────────────────────────────────────────────

class Game:
    def __init__(self):
        self.board = Board()
        self.all_legal = generate_legal_moves(self.board)
        self.selected = None          # (row, col) or None
        self.moves_from_sel = []      # legal moves from selected square
        self.last_move = None
        self.status = 'ongoing'       # 'ongoing','checkmate','stalemate','draw_50move'
        self.difficulty = 1
        self.display_moves = []       # list of strings shown in panel
        self.scroll = 0
        self.ai_thinking = False
        self._ai_result = [None]
        self._promo_pending = None    # (from_sq, to_sq) when promotion dialog needed

    # ── Move handling ────────────────────────────────────────────────────

    def apply_move(self, move):
        san = build_san(self.board, move, self.all_legal)
        self.board.make_move(move)
        self.last_move = move
        self.selected = None
        self.moves_from_sel = []

        if self.board.turn == BLACK:   # white just moved
            mn = self.board.fullmove_number
            self.display_moves.append(f"{mn}.  {san}")
        else:
            if self.display_moves:
                self.display_moves[-1] += f"   {san}"
            else:
                self.display_moves.append(f"…  {san}")

        self.all_legal = generate_legal_moves(self.board)
        self.status = self.board.get_game_status(self.all_legal)
        if self.status == 'ongoing' and self.board.turn != PLAYER:
            self._start_ai()

    def _start_ai(self):
        self.ai_thinking = True
        self._ai_result[0] = None
        diff = self.difficulty
        board_ref = self.board

        def worker():
            move = get_ai_move(board_ref, diff)
            self._ai_result[0] = move
            self.ai_thinking = False

        threading.Thread(target=worker, daemon=True).start()

    def poll_ai(self):
        if not self.ai_thinking and self._ai_result[0] is not None:
            move = self._ai_result[0]
            self._ai_result[0] = None
            if move:
                self.apply_move(move)

    def click_square(self, sq):
        if self.status != 'ongoing' or self.ai_thinking or self.board.turn != PLAYER:
            return
        r, c = sq
        p = self.board.squares[r][c]

        if self.selected:
            # Find a legal move to this square
            candidates = [m for m in self.moves_from_sel if m.to_sq == sq]
            if candidates:
                # Promotion: pick queen automatically
                promo_moves = [m for m in candidates if m.promotion == QUEEN]
                move = (promo_moves or candidates)[0]
                self.apply_move(move)
                return
            # Reselect own piece or deselect
            if p and p[1] == PLAYER:
                self.selected = sq
                self.moves_from_sel = [m for m in self.all_legal if m.from_sq == sq]
            else:
                self.selected = None
                self.moves_from_sel = []
        else:
            if p and p[1] == PLAYER:
                self.selected = sq
                self.moves_from_sel = [m for m in self.all_legal if m.from_sq == sq]

    def reset(self):
        self.__init__()


# ── Renderer ─────────────────────────────────────────────────────────────

class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.font_coord  = pygame.font.SysFont('Segoe UI', 14)
        self.font_sm     = pygame.font.SysFont('Segoe UI', 15)
        self.font_md     = pygame.font.SysFont('Segoe UI', 18)
        self.font_lg     = pygame.font.SysFont('Segoe UI', 22, bold=True)
        self.font_title  = pygame.font.SysFont('Segoe UI', 28, bold=True)
        self.font_piece  = pygame.font.SysFont('Segoe UI Symbol', 54)
        self.font_piece_sm = pygame.font.SysFont('Segoe UI Symbol', 50)
        # Overlay surface for transparency
        self._overlay = pygame.Surface((SQ, SQ), pygame.SRCALPHA)

        pieces= {
            KING: "king",
            QUEEN: "queen",
            ROOK: "rook",
            KNIGHT: "knight",
            BISHOP: "bishop",
            PAWN: "pawn",
        }

        self.images={}

        for piece,name in pieces.items():
            self.images[(piece,WHITE)]=pygame.image.load(f"pieceimages\w.{name}.png").convert_alpha()
            self.images[(piece,WHITE)]=pygame.transform.smoothscale(self.images[(piece,WHITE)],(self.images[(piece,WHITE)].get_width()/1.5,self.images[(piece,WHITE)].get_height()/1.5))

            self.images[(piece,BLACK)]=pygame.image.load(f"pieceimages/b.{name}.png").convert_alpha()
            self.images[(piece,BLACK)]=pygame.transform.smoothscale(self.images[(piece,BLACK)],(self.images[(piece,BLACK)].get_width()/1.5,self.images[(piece,BLACK)].get_height()/1.5))


    # ── Board ─────────────────────────────────────────────────────────

    def draw_board(self, game):
        scr = self.screen

        # Background behind board
        pygame.draw.rect(scr, (15, 18, 24),
                         (BOARD_X - 6, BOARD_Y - 6, BOARD_PX + 12, BOARD_PX + 12),
                         border_radius=4)

        for r in range(8):
            for c in range(8):
                color = SQ_LIGHT if (r + c) % 2 == 0 else SQ_DARK
                pygame.draw.rect(scr, color,
                                 (BOARD_X + c * SQ, BOARD_Y + r * SQ, SQ, SQ))

        self._draw_highlights(game)
        self._draw_coordinates()
        self._draw_pieces(game)

    def _sq_rect(self, r, c):
        return (BOARD_X + c * SQ, BOARD_Y + r * SQ, SQ, SQ)

    def _blit_overlay(self, rgba, r, c):
        self._overlay.fill(rgba)
        self.screen.blit(self._overlay, (BOARD_X + c * SQ, BOARD_Y + r * SQ))

    def _draw_highlights(self, game):
        # Last move
        if game.last_move:
            for sq in (game.last_move.from_sq, game.last_move.to_sq):
                self._blit_overlay(HL_LAST, *sq)

        # Selected square
        if game.selected:
            self._blit_overlay(HL_SEL, *game.selected)

        # Legal move targets
        for m in game.moves_from_sel:
            r, c = m.to_sq
            ov = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
            pygame.draw.circle(ov, HL_LEGAL, (SQ // 2, SQ // 2), 13)
            self.screen.blit(ov, (BOARD_X + c * SQ, BOARD_Y + r * SQ))

        # King in check
        if game.status == 'ongoing' and game.board.is_in_check(game.board.turn):
            for r in range(8):
                for c in range(8):
                    p = game.board.squares[r][c]
                    if p and p[0] == KING and p[1] == game.board.turn:
                        self._blit_overlay(HL_CHECK, r, c)

    def _draw_coordinates(self):
        for i in range(8):
            # File labels below board
            lbl = self.font_coord.render(FILE_NAMES[i], True, COORD_TXT)
            x = BOARD_X + i * SQ + SQ // 2 - lbl.get_width() // 2
            self.screen.blit(lbl, (x, BOARD_Y + BOARD_PX + 6))
            # Rank labels left of board
            lbl = self.font_coord.render(str(8 - i), True, COORD_TXT)
            self.screen.blit(lbl, (BOARD_X - 18, BOARD_Y + i * SQ + SQ // 2 - lbl.get_height() // 2))

    def _draw_pieces(self, game):
        for r in range(8):
            for c in range(8):
                p = game.board.squares[r][c]
                if not p:
                    continue

                piece = self.images[p]
                rect=piece.get_rect()
                rect.center=(BOARD_X + (c * SQ) + SQ // 2, BOARD_Y + r * SQ + SQ // 2)

                self.screen.blit(piece,rect)

    # ── Panel ─────────────────────────────────────────────────────────

    def draw_panel(self, game):
        scr = self.screen
        px, pw = PANEL_X, PANEL_W

        # Panel background
        pygame.draw.rect(scr, PANEL_BG, (px - 4, 0, pw + 8, H), border_radius=6)

        y = 18
        # Title
        t = self.font_title.render('Isaac\'s Chess Bot ', True, (240, 240, 255))
        scr.blit(t, (px, y)); y += 42



        # Status text
        if game.status == 'ongoing':
            if game.ai_thinking:
                st = 'AI is thinking…'
                col = (160, 200, 255)
            elif game.board.turn == WHITE:
                st = 'White to move'
                col = TXT
            else:
                st = 'Black to move'
                col = TXT
        elif game.status == 'checkmate':
            winner = 'Black' if game.board.turn == WHITE else 'White'
            st = f'Checkmate — {winner} wins!'
            col = (255, 180, 80)
        elif game.status == 'stalemate':
            st = 'Stalemate — Draw'
            col = (160, 200, 160)
        else:
            st = 'Draw (50-move rule)'
            col = (160, 200, 160)

        sv = self.font_md.render(st, True, col)
        scr.blit(sv, (px, y)); y += 34

        #eval_score = _evaluate(game.board)

        #eval_text = f"Evaluation: {eval_score:+.2f}"

        #ev = self.font_md.render(eval_text, True, TXT)
        #scr.blit(ev, (px, y))
        
        y += 30

        # ── Difficulty ─────────────────────────────────────────────────
        lbl = self.font_sm.render('Difficulty', True, TXT_DIM)
        scr.blit(lbl, (px, y)); y += 22

        btn_w = (pw - 8) // 3
        diff_rects = []
        mx, my = pygame.mouse.get_pos()
        for i, name in enumerate(DIFF_NAMES):
            bx = px + i * (btn_w + 4)
            br = pygame.Rect(bx, y, btn_w, 30)
            diff_rects.append(br)
            if i == game.difficulty:
                c_ = BTN_ACT
            elif br.collidepoint(mx, my):
                c_ = BTN_HOV
            else:
                c_ = BTN_NORM
            pygame.draw.rect(scr, c_, br, border_radius=6)
            ns = self.font_sm.render(name, True, BTN_TXT)
            scr.blit(ns, (br.x + (btn_w - ns.get_width()) // 2, br.y + 7))
        y += 38

        # ── Reset button ───────────────────────────────────────────────
        reset_rect = pygame.Rect(px, y, pw, 36)
        rc = BTN_HOV if reset_rect.collidepoint(mx, my) else BTN_NORM
        pygame.draw.rect(scr, rc, reset_rect, border_radius=8)
        rs = self.font_md.render('New Game', True, BTN_TXT)
        scr.blit(rs, (reset_rect.x + (pw - rs.get_width()) // 2, reset_rect.y + 8))
        y += 48

        # ── Move history ───────────────────────────────────────────────
        lbl2 = self.font_sm.render('Move History', True, TXT_DIM)
        scr.blit(lbl2, (px, y)); y += 22

        hist_rect = pygame.Rect(px - 2, y, pw + 2, H - y - 12)
        pygame.draw.rect(scr, (25, 30, 40), hist_rect, border_radius=6)

        line_h = 22
        visible = hist_rect.height // line_h
        moves = game.display_moves
        # Auto-scroll to bottom, allow scrolling up
        max_scroll = max(0, len(moves) - visible)
        game.scroll = min(game.scroll, max_scroll)
        start = max(0, len(moves) - visible - game.scroll)
        end = start + visible + 1

        clip = scr.get_clip()
        scr.set_clip(hist_rect)
        for i, text in enumerate(moves[start:end]):
            row_y = hist_rect.y + i * line_h
            bg = MV_ROW_A if i % 2 == 0 else MV_ROW_B
            pygame.draw.rect(scr, bg, (hist_rect.x, row_y, hist_rect.width, line_h))
            ts = self.font_sm.render(text, True, TXT)
            scr.blit(ts, (hist_rect.x + 6, row_y + 4))
        scr.set_clip(clip)

        return diff_rects, reset_rect


# ── Main loop ─────────────────────────────────────────────────────────────

def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption('Chess')
    clock = pygame.time.Clock()

    game = Game()
    renderer = Renderer(screen)

    # Render once to warm up fonts
    screen.fill(BG)
    renderer.draw_board(game)
    renderer.draw_panel(game)
    pygame.display.flip()

    diff_rects = []
    reset_rect = pygame.Rect(0, 0, 0, 0)

    running = True
    while running:
        clock.tick(60)
        game.poll_ai()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                # Reset button
                if reset_rect.collidepoint(mx, my):
                    game.reset()
                    continue
                # Difficulty buttons
                for i, dr in enumerate(diff_rects):
                    if dr.collidepoint(mx, my):
                        game.difficulty = i
                        break
                # Board click
                bx = mx - BOARD_X
                by = my - BOARD_Y
                if 0 <= bx < BOARD_PX and 0 <= by < BOARD_PX:
                    col = bx // SQ
                    row = by // SQ
                    game.click_square((row, col))

            elif event.type == pygame.MOUSEWHEEL:
                game.scroll = max(0, game.scroll - event.y)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    game.reset()

        # Draw frame
        screen.fill(BG)
        renderer.draw_board(game)
        diff_rects, reset_rect = renderer.draw_panel(game)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
