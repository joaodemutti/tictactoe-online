_WIN_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),  # cols
    (0, 4, 8), (2, 4, 6),              # diagonals
]


def check_winner(board: list) -> str | None:
    """Return 'X' or 'O' if a player has won, else None."""
    for a, b, c in _WIN_LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None


def is_draw(board: list) -> bool:
    """Return True when the board is full and there is no winner."""
    return all(cell is not None for cell in board)
