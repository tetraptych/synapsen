"""
A Python 3.6 adaptation of Information Set Monte Carlo Tree Search.

See this gist for the original code: https://gist.github.com/kjlubick/8ea239ede6a026a61f4d.
"""
# This is a very simple Python 2.7 implementation of the Information Set Monte Carlo Tree Search algorithm.
# The function ISMCTS(rootstate, itermax, verbose = False) is towards the bottom of the code.
# It aims to have the clearest and simplest possible code, and for the sake of clarity, the code
# is orders of magnitude less efficient than it could be made, particularly by using a
# state.GetRandomMove() or state.DoRandomRollout() function.
#
# An example GameState classes for Knockout Whist is included to give some idea of how you
# can write your own GameState to use ISMCTS in your hidden information game.
#
# Written by Peter Cowling, Edward Powley, Daniel Whitehouse (University of York, UK) September 2012 - August 2013.
#
# Licence is granted to freely use and distribute for any sensible/legal purpose so long as this comment
# remains in any distributed code.
#
# For more information about Monte Carlo Tree Search check out our web site at www.mcts.ai
# Also read the article accompanying this code at ***URL HERE***
import math
import random


# Strategy to function mapping.
VALUATION_FUNCTIONS = {
    'id': {
        'function': lambda x: x,
        'min': -3.0,
        'max': 3.0,
    },
    'win': {
        'function': lambda x: float(x > 0.0),
        'min': 0.0,
        'max': 1.0,
    },
    'get_at_least_2': {
        'function': lambda x: float(x >= 2.0),
        'min': 0.0,
        'max': 1.0,
    },
    'get_at_least_3': {
        'function': lambda x: float(x >= 3.0),
        'min': 0.0,
        'max': 1.0,
    },
    'prevent_other_player_from_getting_2': {
        'function': lambda x: float(x > -2.0),
        'min': 0.0,
        'max': 1.0,
    },
    'prevent_other_player_from_getting_3': {
        'function': lambda x: float(x > -3.0),
        'min': 0.0,
        'max': 1.0,
    },

}


class GameState:
    """
    A state of the game, i.e. the game board.

    These are the only functions which are
    absolutely necessary to implement ISMCTS in any imperfect information game,
    although they could be enhanced and made quicker, for example by using a
    GetRandomMove() function to generate a random move during rollout.
    By convention the players are numbered 1, 2, ..., self.numberOfPlayers.
    """

    def __init__(self):
        self.numberOfPlayers = 2
        self.playerToMove = 1

    def GetNextPlayer(self, p):
        """Return the player to the left of the specified player."""
        return (p % self.numberOfPlayers) + 1

    def Clone(self):
        """Create a deep clone of this game state."""
        st = GameState()
        st.playerToMove = self.playerToMove
        return st

    def CloneAndRandomize(self, observer):
        """
        Create a deep clone of this game state.

        Randomizes any information not visible to the specified observer player.
        """
        return self.Clone()

    def DoMove(self, move):
        """
        Update a state by carrying out the given move.

        Must update playerToMove.
        """
        self.playerToMove = self.GetNextPlayer(self.playerToMove)

    def GetMoves(self):
        """Get all possible moves from this state."""
        raise NotImplementedError()

    def GetResult(self, player):
        """Get the game result from the viewpoint of player."""
        raise NotImplementedError()

    def __repr__(self):
        """Don't need this - but good style."""
        pass


class Node:
    """
    A node in the game tree.

    Note wins is always from the viewpoint of playerJustMoved.
    """

    def __init__(
            self, move=None, parent=None, playerJustMoved=None,
            isTalonClosed=False, whoClosedTalon=None, strategy='id'
    ):
        self.move = move  # the move that got us to this node - "None" for the root node
        self.strategy = strategy
        self.parentNode = parent  # "None" for the root node
        self.childNodes = []
        self.wins = 0
        self.visits = 0
        self.avails = 1
        self.playerJustMoved = playerJustMoved  # part of the state that the Node needs later
        self.isTalonClosed = isTalonClosed  # part of the state that the Node needs later
        self.whoClosedTalon = whoClosedTalon    # part of the state that the Node needs later
        self.valuation_function = VALUATION_FUNCTIONS[self.strategy]['function']
        self._min_value = VALUATION_FUNCTIONS[self.strategy]['min']
        self._max_value = VALUATION_FUNCTIONS[self.strategy]['max']

    def GetUntriedMoves(self, legalMoves):
        """Return the elements of legalMoves for which this node does not have children."""
        # Find all moves for which this node *does* have children
        triedMoves = [child.move for child in self.childNodes]
        # Return all moves that are legal but have not been tried yet
        return [move for move in legalMoves if move not in triedMoves]

    def UCBSelectChild(self, legalMoves, exploration=0.8):
        """
        Use the UCB1 formula to select a child node, filtered by the given list of legal moves.

        `exploration` is a constant balancing between exploitation and exploration.
        """
        # Filter the list of children by the list of legal moves
        legalChildren = [child for child in self.childNodes if child.move in legalMoves]
        # Get the child with the highest UCB score.
        # Rescale wins / visits to the range [0, 1] in case the valuation function doesn't.
        s = max(
            legalChildren,
            key=lambda c:
                (
                    float(c.wins) / float(c.visits) - self._min_value
                ) / (self._max_value - self._min_value) +
                exploration * math.sqrt(math.log(c.avails) / float(c.visits))
        )
        # Update availability counts -- it is easier to do this now than during backpropagation
        for child in legalChildren:
            child.avails += 1

        # Return the child selected above
        return s

    def AddChild(self, m, playerJustMoved, isTalonClosed, whoClosedTalon):
        """
        Add a new child node for the move m.

        Return the added child node.
        """
        if whoClosedTalon is not None:
            w = whoClosedTalon
        elif m.close_talon:
            w = playerJustMoved
        else:
            w = None

        n = Node(
            move=m,
            parent=self,
            playerJustMoved=playerJustMoved,
            isTalonClosed=isTalonClosed or m.close_talon,
            whoClosedTalon=w,
            strategy=self.strategy
        )
        self.childNodes.append(n)
        return n

    def Update(self, terminalState):
        """
        Update this node.

        1. Increment the visit count by one.
        2. increase the win count by the result of terminalState for self.playerJustMoved.
        """
        self.visits += 1
        if self.playerJustMoved is not None:
            self.wins += self.valuation_function(terminalState.GetResult(self.playerJustMoved))

    def __repr__(self):
        """Represent a node as a string."""
        return '[M:{} E/W/V/A: {:.3f} / {:.2f} / {:6d} / {:6d}]'.format(
            str(self.move).ljust(20),
            (self.wins / self.visits),
            self.wins,
            self.visits,
            self.avails,
        )

    def TreeToString(self, indent):
        """Represent the tree as a string for debugging purposes."""
        s = self.IndentString(indent) + str(self)
        for c in self.childNodes:
            s += c.TreeToString(indent + 1)
        return s

    def IndentString(self, indent):
        """Indent a string for debugging purposes."""
        s = "\n"
        for i in range(1, indent + 1):
            s += "| "
        return s

    def ChildrenToString(self):
        """Represent children as strings for debugging purposes."""
        s = ""
        for c in sorted(self.childNodes, key=lambda node: node.visits, reverse=True):
            s += str(c) + "\n"
        return s


def ISMCTS(rootstate, itermax, strategy='id', verbose=False):
    """
    Conduct an ISMCTS search for itermax iterations starting from rootstate.

    Return the best move from the rootstate.
    """
    rootnode = Node(strategy=strategy)

    for i in range(itermax):
        node = rootnode

        # Determinize
        state = rootstate.CloneAndRandomize(rootstate.playerToMove)

        # Select
        # While: node is fully expanded and non-terminal
        moves = state.GetMoves()
        while moves != [] and node.GetUntriedMoves(legalMoves=moves) == []:
            node = node.UCBSelectChild(legalMoves=moves)
            state.DoMove(move=node.move)
            moves = state.GetMoves()

        # Expand
        untriedMoves = node.GetUntriedMoves(legalMoves=moves)
        if untriedMoves != []:  # if we can expand (i.e. state/node is non-terminal)
            m = random.choice(untriedMoves)
            player = state.playerToMove
            state.DoMove(move=m)
            node = node.AddChild(
                m=m,
                playerJustMoved=player,
                isTalonClosed=state.isTalonClosed,
                whoClosedTalon=state.whoClosedTalon
            )  # add child and descend tree

        # Simulate
        moves = state.GetMoves()
        while moves != []:  # while state is non-terminal
            state.DoMove(move=random.choice(moves))
            moves = state.GetMoves()

        # Backpropagate
        while node is not None:  # backpropagate from the expanded node and work back to the root
            node.Update(state)
            node = node.parentNode

    # Output some information about the tree - can be omitted
    if verbose > 1.0:
        print(rootnode.TreeToString(0))
    elif verbose:
        print(rootnode.ChildrenToString())

    return max(rootnode.childNodes, key=lambda c: c.visits).move   # return the most visited move
