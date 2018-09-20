"""Play games of Schnapsen using ISMCTS players."""
import argparse
import random

from players import ComputerPlayer, HumanPlayer
from schnapsen import SchnapsenGameState

DIFFICULTY_TO_ITERMAX_MAP = {
    'trivial': 1,   # For testing purposes only!
    'easy': 500,
    'medium': 1500,
    'hard': 5000,
    'insane': 5000
}


def PlayGame(**kwargs):
    """Play a game between two players."""
    players_by_index = _kwargs_to_players(**kwargs)
    game_type = kwargs['game_type']

    omniscient_players = {
        idx for idx in players_by_index if players_by_index[idx].is_omniscient
    }
    state = SchnapsenGameState(omniscient_players=omniscient_players)

    while (state.GetMoves() != []):
        # Get the current player.
        player = players_by_index[state.playerToMove]
        # Only show the part of the game state visible to human players.
        if player.type == 'human':
            print(player.survey_game_state(state))
        # Display everything in computer-computer games.
        if game_type == 'computer-computer':
            print(state)

        # The current player selects a move.
        move = player.select_move(state, verbose=(game_type == 'computer-computer'))
        print('Player {} played {}!\n'.format(state.playerToMove, move))
        state.DoMove(move)

    if state.winner:
        print('Player {} wins!'.format(str(state.winner)))
    else:
        print('Nobody wins!')

    return state


def _kwargs_to_players(**kwargs):
    """Convert a game type string (e.g., 'computer-human') to actual players."""
    player_strings = kwargs['game_type'].split('-')

    players = []
    for idx, string in enumerate(player_strings):
        if string == 'human':
            player = HumanPlayer(_id=idx + 1)
        elif idx == 0 or not kwargs.get('difficulty2'):
            # If only one difficulty is specified, use it for all computer players.
            player = ComputerPlayer(
                _id=idx + 1,
                itermax=DIFFICULTY_TO_ITERMAX_MAP[kwargs['difficulty']],
                is_omniscient=(kwargs['difficulty'] == 'insane')
            )
        else:
            # If multiple difficulties are specified, use the second for the second computer player.
            player = ComputerPlayer(
                _id=idx + 1,
                itermax=DIFFICULTY_TO_ITERMAX_MAP[kwargs['difficulty2']],
                is_omniscient=(kwargs['difficulty2'] == 'insane')
            )
        players.append(player)

    return {idx + 1: player for idx, player in enumerate(players)}


def _get_arguments():
    """Get command line arguments to start a game of Schnapsen."""
    parser = argparse.ArgumentParser(description='This begins a game of Schnapsen.')

    parser.add_argument(
        '-gt', '--game-type',
        help="""
            The type of the players in the game.

            Available options are:
                - human-human
                - human-computer
                - computer-computer
                - computer-human
        """.strip(),
        required=False,
        default='human-computer',
        type=str
    )

    parser.add_argument(
        '-d', '--difficulty',
        help="""
            The difficulty of the first computer player in the game.

            Available options are:
                - easy
                - medium
                - hard
                - insane
        """.strip(),
        required=False,
        default='medium',
        type=str
    )

    parser.add_argument(
        '-d2', '--difficulty2',
        help="""
            The difficulty of the second computer player (optional).

            Available options are:
                - easy
                - medium
                - hard
                - insane
        """.strip(),
        required=False,
        type=str
    )

    parser.add_argument(
        '-s', '--seed',
        help='The seed for the random state.',
        required=False,
        type=int
    )

    return parser.parse_args().__dict__


if __name__ == '__main__':
    arguments = _get_arguments()
    print('Game arguments are {}'.format(arguments))
    if 'seed' in arguments:
        random.seed(arguments['seed'])
    PlayGame(**arguments)
