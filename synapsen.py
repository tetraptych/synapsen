"""Play games of Schnapsen using ISMCTS players."""
import argparse

from players import ComputerPlayer, HumanPlayer
from schnapsen import SchnapsenGameState

DIFFICULTY_TO_ITERMAX_MAP = {
    'trivial': 1,   # For testing purposes only!
    'easy': 500,
    'medium': 5 * 10**3,
    'hard': 10**4,
    'insane': 2 * 10**4
}


def PlayGame(**kwargs):
    """Play a game between two players."""
    state = SchnapsenGameState()
    player_by_index = _kwargs_to_players(**kwargs)

    game_type = kwargs['game_type']

    while (state.GetMoves() != []):
        # Get the current player.
        player = player_by_index[state.playerToMove]
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

    someoneWon = False
    for p in range(1, state.numberOfPlayers + 1):
        if state.GetResult(p) >= 1.0:
            print('Player ' + str(p) + ' wins!')
            someoneWon = True
    if not someoneWon:
        print('Nobody wins!')


def _kwargs_to_players(**kwargs):
    """Convert a game type string (e.g., 'computer-human') to actual players."""
    player_strings = kwargs['game_type'].split('-')
    players = [
        HumanPlayer(_id=idx + 1)
        if string.lower() == 'human'
        else ComputerPlayer(_id=idx + 1, itermax=DIFFICULTY_TO_ITERMAX_MAP[kwargs['difficulty']])
        for idx, string in enumerate(player_strings)
    ]
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
            The difficulty of any computer players in the game.

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

    return parser.parse_args().__dict__


if __name__ == '__main__':
    arguments = _get_arguments()
    print('Game arguments are {}'.format(arguments))
    PlayGame(**arguments)
