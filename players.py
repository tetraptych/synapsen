"""
Classes representing computer and human players.

Each player responds to the game state by making moves on their turn.
"""
from ISMCTS import ISMCTS


class Player(object):
    """Interface for Schnapsen players."""

    def __init__(self, _id):
        """Initialize a player."""
        self._id = _id

    def select_move(self, state, verbose=False):
        """Return a legal move in the game state (but do not make it)."""
        raise NotImplementedError

    def survey_game_state(self, state):
        """Display all the information available to the player."""
        state_repr = state.__repr__()
        available_moves_as_strs = [
            '{idx}: {move}{winner}'.format(
                idx=idx + 1,
                move=move,
                winner=' (W)' if (
                    state.currentTrick != [] and
                    state.GetTrickWinner(state.currentTrick + [(self._id, move.card)]) == self._id
                ) else ''
            )
            for idx, move in enumerate(state.GetMoves())
        ]
        available_moves_string = 'Available Moves: \n\t' + '\n\t'.join(available_moves_as_strs)
        return state_repr + '\n' + available_moves_string


class ComputerPlayer(Player):
    """A player using the ISMCTS algorithm to make moves."""

    def __init__(self, _id, itermax=3000):
        """
        Initialize an ISMCTS player.

        Parameters
        ----------
        itermax: Number of iterations to perform ISMCTS.
        """
        super(ComputerPlayer, self).__init__(_id=_id)
        self.itermax = itermax
        self.type = 'computer'

    def select_move(self, state, verbose=False):
        """Return a legal move in the game state (but do not make it)."""
        return ISMCTS(rootstate=state, itermax=self.itermax, verbose=verbose)


class HumanPlayer(Player):
    """A human player."""

    def __init__(self, _id):
        """Initialize a human player."""
        super(HumanPlayer, self).__init__(_id=_id)
        self.type = 'human'

    def select_move(self, state, verbose=False):
        """Return a legal move in the game state (but do not make it)."""
        available_moves = state.GetMoves()

        valid_move = False
        while valid_move is False:
            move_idx = input('Enter your move (1 to {}): '.format(len(available_moves)))
            try:
                move = available_moves[int(move_idx) - 1]
                valid_move = True
            except (TypeError, IndexError):
                print('Index must be between 1 and {}!'.format(len(available_moves)))
                valid_move = False

        return move
