# Robert's attempt
# Game rules:
#   -No check
#   -No castling
#   -No En passant


# game state is a list of pieces
# board state should probably be hardcoded for speed.
# Each piece should include:
#   -position
#   -player (can this be merged into everything else?)
#   -an iterator that takes the board state and returns a list of possible board states
#   -a function for taking the piece's position and return it's value?

import sys
import time
from shared import StalemateException

# Define global rules
board_size = 8
board = [(row, col) for row in range(0, board_size, 1) for col in range(0, board_size, 1)]


def move_set(move_dirs, move_dist):
    """Define piece movement functions
        They return a list of valid states"""
    def piece_moves(state, piece_name, player):
        # Returns the list of moves
        current_piece = state[piece_name]
        current_position = current_piece['posn']
        new_states = []

        # Check player
        if player != current_piece['player']:
            return []

        for move_dir in move_dirs:
            for dist in range(1, move_dist+1, 1):
                position = (current_position[0] + dist * move_dir[0], current_position[1] + dist * move_dir[1])
                # Check for bad collisions
                if position not in board:
                    break
                is_blocked = False
                for piece2 in state.values():
                    if piece2['posn'] == position and piece2['player'] == player:
                        is_blocked = True
                        break
                if is_blocked:
                    break

                #print('Good Position found')
                new_piece = current_piece.copy()
                new_piece.update({'posn': position})
                new_state = state.copy()

                # Check for captures
                did_capture = False
                for piece_name2, piece2 in list(new_state.items()):
                    if piece2['posn'] == position and piece2['player'] != player:
                        did_capture = True
                        del new_state[piece_name2]

                new_state.update({piece_name: new_piece})
                new_states.append(new_state)

                # Checks if next posn valid i.e if movement blocked by capture
                if did_capture:
                    break
                # look at next position
                position = (position[0] + move_dir[0], position[1] + move_dir[1])

        return new_states
    return piece_moves


def move_pawn(move_dir):
    def pawn_moves(state, piece_name, player):
        # Returns the list of moves for pawns
        current_piece = state[piece_name]
        current_position = current_piece['posn']
        new_states = []

        # Check player
        if player != current_piece['player']:
            return []

        # Can move up, if nothing is in the way.
        position = (current_position[0] + move_dir, current_position[1])
        # Check for bad collisions
        is_blocked = position not in board or any(i_piece['posn'] == position for i_piece in state.values())
        if not is_blocked:
            new_piece = current_piece.copy()
            new_piece.update({'posn': position})
            new_state = state.copy()
            new_state.update({piece_name: new_piece})
            new_states.append(new_state)

            # if on first row, can move twice
            if current_position[0] == 1 or current_position[0] == board_size - 2:
                position = (position[0] + move_dir, position[1])
                # Check for bad collisions
                is_blocked = position not in board or any(i_piece['posn'] == position for i_piece in state.values())
                if not is_blocked:
                    new_piece = current_piece.copy()
                    new_piece.update({'posn': position})
                    new_state = state.copy()
                    new_state.update({piece_name: new_piece})
                    new_states.append(new_state)

        # Can take diagonally.
        for position in [(current_position[0] + move_dir, current_position[1] - 1),
                         (current_position[0] + move_dir, current_position[1] + 1)]:
            # Must move into hostile piece
            if not any(i_piece['posn'] == position and i_piece['player'] != player for i_piece in state.values()):
                continue

            #print('Good Position found')
            new_piece = current_piece.copy()
            new_piece.update({'posn': position})
            new_state = state.copy()

            # Check for captures
            did_capture = False
            for piece_name2, piece2 in list(new_state.items()):
                if piece2['posn'] == position and piece2['player'] != player:
                    did_capture = True
                    del new_state[piece_name2]
            if not did_capture:
                print("Bad pawn capture")
                sys.exit(1)

            new_state.update({piece_name: new_piece})
            new_states.append(new_state)

        # TODO check for queening

        return new_states
    return pawn_moves


def get_value(base_val, value_matrix):
    # Normalise value matrix
    error = sum([sum(row) for row in value_matrix]) / board_size ** 2
    value_matrix = [[element * error for element in row] for row in value_matrix]

    def piece_value(posn):
        return base_val * value_matrix[posn[0]][posn[1]]
    return piece_value

diversion_factor = 1/100000
default_posn_values = [[(1 - diversion_factor * (col - (board_size-1)/2) ** 2) * (1 - diversion_factor * (row - (board_size-1)/2) ** 2) for col in range(0, board_size, 1)] for row in range(0, board_size, 1)]
flat_posn_values = [[1 for col in range(0, board_size, 1)] for row in range(0, board_size, 1)]


def pawn_value(base_val, move_dir):
    #Pawns use a different value system, they prefer to move up if possible.
    diversion_factor = 1 / 100000

    value_matrix = [[(1 - diversion_factor * (col - (board_size - 1) / 2) ** 2) *
                     (2 + move_dir * (row + 1)/board_size) for col in range(0, board_size, 1)] for row in
                        range(0, board_size, 1)]
    # Normalise value matrix
    error = sum([sum(row) for row in value_matrix]) / board_size ** 2
    value_matrix = [[element * error for element in row] for row in value_matrix]

    def piece_value(posn):
        return base_val * value_matrix[posn[0]][posn[1]]
    return piece_value


def search(depth, old_state, player):
    # This function returns the best possible next game state for the player after searching to depth
    # generate list of game states
    new_states = [state for i_piece in old_state for state in old_state[i_piece]['moves'](old_state, i_piece, player)]

    if len(new_states) == 0:
        raise StalemateException

    # valuate over them
    values = [
        -evaluate(depth - 1, state, 1-player)
        for state in new_states
        ]
    best_state = new_states[values.index(max(values))]
    return best_state


def evaluate(depth, old_state, player):
    # This function returns the value of a particular game state

    # TODO: implement forking on capture

    # Check for loss condition, then recurse if necessary.
    if not any([piece['player'] == player and piece['symbol'].lower() == 'k' for piece in old_state.values()]):
        value = -float('inf')
    elif depth == 0:
        value = sum([piece['value'](piece['posn']) * (1 - 2 * (piece['player'] != player)) for piece in old_state.values()])
    else:
        # Value of this state is equal to the value of the next one.
        try:
            next_state = search(depth, old_state, player)
            value = -evaluate(depth - 1, next_state, 1 - player)
        except StalemateException:
            value = 0

    return value

knight_dirs = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
bish_dirs = [(1, 1), (-1, -1), (-1, 1), (1, -1)]
rook_dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
royal_dirs = rook_dirs + bish_dirs

piece_library = {
    'p': {'symbol': 'p',
          'player': 1,
          'moves': move_pawn(-1),
          'value': pawn_value(1, -1),
          },
    'P': {'symbol': 'P',
          'player': 0,
          'moves': move_pawn(1),
          'value': pawn_value(1, 1),
          },
    'n': {'symbol': 'n',
          'player': 1,
          'moves': move_set(knight_dirs, 1),
          'value': get_value(3, default_posn_values),
          },
    'N': {'symbol': 'N',
          'player': 0,
          'moves': move_set(knight_dirs, 1),
          'value': get_value(3, default_posn_values),
          },
    'b': {'symbol': 'b',
          'player': 1,
          'moves': move_set(bish_dirs, 999),
          'value': get_value(3.5, default_posn_values),
          },
    'B': {'symbol': 'B',
          'player': 0,
          'moves': move_set(bish_dirs, 999),
          'value': get_value(3.5, default_posn_values),
          },
    'r': {'symbol': 'r',
          'player': 1,
          'moves': move_set(rook_dirs, 999),
          'value': get_value(5, default_posn_values),
          },
    'R': {'symbol': 'R',
          'player': 0,
          'moves': move_set(rook_dirs, 999),
          'value': get_value(5, default_posn_values),
          },
    'q': {'symbol': 'q',
          'player': 1,
          'moves': move_set(royal_dirs, 999),
          'value': get_value(9, default_posn_values),
          },
    'Q': {'symbol': 'Q',
          'player': 0,
          'moves': move_set(royal_dirs, 999),
          'value': get_value(9, default_posn_values),
          },
    'k': {'symbol': 'k',
          'player': 1,
          'moves': move_set(royal_dirs, 1),
          'value': get_value(999, default_posn_values),
          },
    'K': {'symbol': 'K',
          'player': 0,
          'moves': move_set(royal_dirs, 1),
          'value': get_value(999, flat_posn_values),
          },
    '.': {},
}


def construct_piece(in_char, row, col):
    """ Converts from characters in a list of strings to piece dicts."""
    if in_char == '.':
        return None
    properties = piece_library[in_char]
    properties.update({'posn': (row, col),
                       # 'ID': properties['symbol'] + str(row) + str(col),
                       })
    return properties.copy()


def main(history, white_time, black_time):
    start_player = (len(history) - 1) % 2

    # Load initial game state
    board_text = history[-1]

    start_state = {}
    for row in range(0, board_size, 1):
        for col in range(0, board_size, 1):
            symbol = board_text[row][col]
            if symbol == '.':
                continue
            start_state.update({symbol + str(row) + str(col): construct_piece(symbol, row, col)})

    new_state = search(2, start_state, start_player)

    # Unparse
    new_board_text = [['.' for col in range(0, board_size, 1)] for row in range(0, board_size, 1)]
    for piece in new_state.values():
        new_board_text[piece['posn'][0]][piece['posn'][1]] = piece['symbol']

    return new_board_text
