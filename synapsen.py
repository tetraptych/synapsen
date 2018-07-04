"""Play games of Schnapsen using ISMCTS players."""
from schnapsen import SchnapsenGameState

from ISMCTS import ISMCTS


def PlayGame():
    """Play a sample game between two ISMCTS players."""
    state = SchnapsenGameState()

    while (state.GetMoves() != []):
        print(str(state))
        # Use different numbers of iterations (simulations, tree nodes) for different players
        if state.playerToMove == 1:
            m = ISMCTS(rootstate=state, itermax=10000, verbose=False)
        else:
            m = ISMCTS(rootstate=state, itermax=10000, verbose=False)
        print('Best Move: ' + str(m) + '\n')
        state.DoMove(m)

    someoneWon = False
    for p in range(1, state.numberOfPlayers + 1):
        if state.GetResult(p) >= 1.0:
            print('Player ' + str(p) + ' wins!')
            someoneWon = True
    if not someoneWon:
        print('Nobody wins!')


if __name__ == '__main__':
    PlayGame()
