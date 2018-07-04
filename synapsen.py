"""Play games of Schnapsen using ISMCTS players."""
from players import ComputerPlayer, HumanPlayer
from schnapsen import SchnapsenGameState


def PlayGame(game_type='human-human'):
    """Play a game between two players."""
    state = SchnapsenGameState()
    player_by_index = _game_type_string_to_players(game_type)

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
        move = player.select_move(state)
        print('Player {} played {}!\n'.format(state.playerToMove, move))
        state.DoMove(move)

    someoneWon = False
    for p in range(1, state.numberOfPlayers + 1):
        if state.GetResult(p) >= 1.0:
            print('Player ' + str(p) + ' wins!')
            someoneWon = True
    if not someoneWon:
        print('Nobody wins!')


def _game_type_string_to_players(game_type_str):
    """Convert a game type string (e.g., 'computer-human') to actual players."""
    player_strings = game_type_str.split('-')
    players = [
        HumanPlayer(_id=idx + 1) if string.lower() == 'human' else ComputerPlayer(_id=idx + 1)
        for idx, string in enumerate(player_strings)
    ]
    return {idx + 1: player for idx, player in enumerate(players)}


if __name__ == '__main__':
    PlayGame('human-computer')
