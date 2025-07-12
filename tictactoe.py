import random

class TicTacToe:
    def __init__(self):
        self.board = [' ' for _ in range(9)]
        self.current_winner = None

    def print_board(self):
        # this is just for debugging
        for row in [self.board[i*3:(i+1)*3] for i in range(3)]:
            print('| ' + ' | '.join(row) + ' |')

    def available_moves(self):
        return [i for i, spot in enumerate(self.board) if spot == ' ']

    def empty_squares(self):
        return ' ' in self.board

    def num_empty_squares(self):
        return self.board.count(' ')

    def make_move(self, square, letter):
        if self.board[square] == ' ':
            self.board[square] = letter
            if self.winner(square, letter):
                self.current_winner = letter
            return True
        return False

    def winner(self, square, letter):
        # check row
        row_ind = square // 3
        row = self.board[row_ind*3 : (row_ind + 1) * 3]
        if all([spot == letter for spot in row]):
            return True
        # check column
        col_ind = square % 3
        column = [self.board[col_ind+i*3] for i in range(3)]
        if all([spot == letter for spot in column]):
            return True
        # check diagonal
        if square % 2 == 0:
            diagonal1 = [self.board[i] for i in [0, 4, 8]]
            if all([spot == letter for spot in diagonal1]):
                return True
            diagonal2 = [self.board[i] for i in [2, 4, 6]]
            if all([spot == letter for spot in diagonal2]):
                return True
        return False

    def get_board_string(self):
        board_str = ""
        for i in range(3):
            row = self.board[i*3:(i+1)*3]
            board_str += ' | '.join(row) + '\n'
            if i < 2:
                board_str += '---------\n'
        return f"```\n{board_str}```"

def get_ai_move(game):
    if game.num_empty_squares() == 9:
        square = random.choice(game.available_moves())
    else:
        square = minimax(game, 'O')['position']
    return square

def minimax(state, player):
    max_player = 'O'  # AI
    other_player = 'X' if player == 'O' else 'O'

    # first, we want to check if the previous move is a winner
    if state.current_winner == other_player:
        return {'position': None, 'score': 1 * (state.num_empty_squares() + 1) if other_player == max_player else -1 * (
                    state.num_empty_squares() + 1)}
    elif not state.empty_squares():
        return {'position': None, 'score': 0}

    if player == max_player:
        best = {'position': None, 'score': -float('inf')}  # each score should maximize
    else:
        best = {'position': None, 'score': float('inf')}  # each score should minimize

    for possible_move in state.available_moves():
        state.make_move(possible_move, player)
        sim_score = minimax(state, other_player)  # simulate a game after making that move

        # undo move
        state.board[possible_move] = ' '
        state.current_winner = None
        sim_score['position'] = possible_move  # this is the move that was just tested

        if player == max_player:  # X is max player
            if sim_score['score'] > best['score']:
                best = sim_score
        else:
            if sim_score['score'] < best['score']:
                best = sim_score
    return best
