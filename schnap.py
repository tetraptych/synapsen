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
import copy
import math
import random


class GameState:
    """
    A state of the game, i.e. the game board. These are the only functions which are
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
        """ Update a state by carrying out the given move.
            Must update playerToMove.
        """
        self.playerToMove = self.GetNextPlayer(self.playerToMove)

    def GetMoves(self):
        """ Get all possible moves from this state.
        """
        raise NotImplementedError()

    def GetResult(self, player):
        """ Get the game result from the viewpoint of player.
        """
        raise NotImplementedError()

    def __repr__(self):
        """ Don't need this - but good style.
        """
        pass


class Card(object):
    """
    A playing card, with rank and suit.

    rank must be an integer between 10 and 14 inclusive (Jack=11, Queen=12, King=13, Ace=14).
    suit must be a string of length 1, one of 'C', 'D', 'H', 'S'.
    """
    RANK_TO_SCORE_MAP = {
        10: 10,
        11: 2,
        12: 3,
        13: 4,
        14: 11
    }

    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
        self.score = self.RANK_TO_SCORE_MAP[self.rank]

    def get_marriage_partner(self):
        """Return another card representing the marriage partner."""
        if self.rank == 12:
            return Card(rank=13, suit=self.suit)
        elif self.rank == 13:
            return Card(rank=12, suit=self.suit)
        else:
            return None

    def __repr__(self):
        return "??23456789TJQKA"[self.rank] + self.suit

    def __eq__(self, other):
        return self.rank == other.rank and self.suit == other.suit

    def __ne__(self, other):
        return self.rank != other.rank or self.suit != other.suit

    def __copy__(self):
        return Card(rank=self.rank, suit=self.suit)

    def __deepcopy__(self, memo):
        return Card(rank=self.rank, suit=self.suit)


class SchnapsenMove(object):
    """
    Represents a single move in a game of Schnapsen.

    A move consists of a decision to close the talon or not and a card to play.
    """

    def __init__(self, card, close_talon=False, marriage_points=None):
        self.card = card
        self.close_talon = close_talon
        self.marriage_points = marriage_points

    def __repr__(self):
        res = ''
        if self.close_talon:
            res += 'Close + '
        if self.marriage_points:
            res += 'Marriage + '
        res += self.card.__repr__()
        return res

    def __eq__(self, other):
        return self.card == other.card and self.close_talon == other.close_talon

    def __ne__(self, other):
        return self.card != other.card or self.close_talon != other.close_talon


class SchnapsenGameState(GameState):

    def __init__(self):
        """Initialize the game state."""
        self.numberOfPlayers = 2
        self.players = [1, 2]
        self.playerToMove = 1
        self.playerHands = {p: [] for p in self.players}
        self.marriageCardsRevealed = {p: [] for p in self.players}
        self.handSize = 5
        self.discards = []  # Stores the cards that have been played already in this round
        self.currentTrick = []
        self.trumpSuit = None
        self.pointsTaken = {}  # Number of tricks taken by each player this round
        self.isTalonClosed = False
        self.whoClosedTalon = None
        self.gamePointsAtStake = None
        self.deck = None
        self.Deal()

    def Clone(self):
        """Create a deep clone of this game state."""
        st = SchnapsenGameState()
        st.players = self.players
        st.numberOfPlayers = self.numberOfPlayers
        st.playerToMove = self.playerToMove
        st.playerHands = copy.deepcopy(self.playerHands)
        st.marriageCardsRevealed = copy.deepcopy(self.marriageCardsRevealed)
        st.handSize = self.handSize
        st.discards = copy.deepcopy(self.discards)
        st.currentTrick = copy.deepcopy(self.currentTrick)
        st.trumpSuit = self.trumpSuit
        st.pointsTaken = copy.deepcopy(self.pointsTaken)
        st.isTalonClosed = self.isTalonClosed
        st.whoClosedTalon = self.whoClosedTalon
        st.gamePointsAtStake = self.gamePointsAtStake
        st.deck = copy.deepcopy(self.deck)
        return st

    def CloneAndRandomize(self, observer):
        """
        Create a deep clone of this game state.

        All information not visible to the specified observer player is randomized.
        """
        st = self.Clone()
        # The observer can see its own hand and the cards in the current trick.
        # The observer can also remember the cards played in previous tricks.
        currentTrickCards = [card for (player, card) in st.currentTrick]
        seenCards = st.playerHands[observer] + st.discards + currentTrickCards
        # The observer also knows about all declared marriages.
        marriagePartners = [
            card for p in st.players
            for card in st.marriageCardsRevealed[p]
            if (p != observer and card not in currentTrickCards)
        ]
        seenCards += marriagePartners
        # The observer can't see the rest of the deck.
        unseenCards = [card for card in st.GetCardDeck() if card not in seenCards]

        assert(len(unseenCards) + len(seenCards) == len(st.GetCardDeck()))

        # Deal the unseen cards to the other players.
        random.shuffle(unseenCards)
        for p in st.players:
            if p != observer:
                # Deal cards to player p, accounting for revealed marriages.
                playerHand = [card for card in st.marriageCardsRevealed[p]]
                numCardsToDeal = len(st.playerHands[p]) - len(playerHand)
                playerHand += unseenCards[: numCardsToDeal]
                st.playerHands[p] = [card for card in playerHand]
                # Remove those cards from unseenCards.
                unseenCards = unseenCards[numCardsToDeal:]

        st.deck = unseenCards
        return st

    def GetCardDeck(self):
        """Construct a standard deck of 20 cards (ten through ace of each suit)."""
        return [Card(rank, suit) for rank in range(10, 14 + 1) for suit in ['C', 'D', 'H', 'S']]

    def Deal(self):
        """Reset the game state for the beginning of a new round and deal the cards."""
        self.discards = []
        self.currentTrick = []
        self.pointsTaken = {p: 0 for p in range(1, self.numberOfPlayers + 1)}

        # Construct a deck, shuffle it, and deal it to the players
        deck = self.GetCardDeck()
        random.shuffle(deck)
        for p in range(1, self.numberOfPlayers + 1):
            self.playerHands[p] = deck[: self.handSize]
            deck = deck[self.handSize:]

        # Set the remaining cards to draw.
        self.deck = deck
        # Choose the trump suit for this round.
        self.trumpSuit = random.choice(['C', 'D', 'H', 'S'])

    def GetNextPlayer(self, p):
        """Return the player to the left of the specified player."""
        return (p % self.numberOfPlayers) + 1

    def DoMove(self, move):
        """
        Update a state by carrying out the given move.

        Must update playerToMove.
        """
        # Close the talon if part of the current SchnapsenMove.
        if move.close_talon:
            self.isTalonClosed = True
            self.whoClosedTalon = self.playerToMove

        # Check for marriages, updating known information about the game state.
        if move.marriage_points is not None:
            self.pointsTaken[self.playerToMove] += move.marriage_points
            self.marriageCardsRevealed[self.playerToMove].append(
                move.card.get_marriage_partner()
            )
            # THIS BREAKS THINGS.
            # # Remove the marriage partner from the deck if possible.
            # if move.card.get_marriage_partner() in self.deck:
            #     self.deck.remove(move.card.get_marriage_partner())

            # End game if the marriage puts the current player over 66 points.
            if self.pointsTaken[self.playerToMove] >= 66:
                return

        # Store the played card in the current trick.
        self.currentTrick.append((self.playerToMove, move.card))
        # Remove the card from the player's hand.
        self.playerHands[self.playerToMove].remove(move.card)
        # If applicable, remove the card from the current player's revealed marriage cards.
        if move.card in self.marriageCardsRevealed[self.playerToMove]:
            self.marriageCardsRevealed[self.playerToMove].remove(move.card)
        # Find the next player.
        self.playerToMove = self.GetNextPlayer(self.playerToMove)

        # If the next player has already played in this trick, then the trick is over.
        if any(True for (player, card) in self.currentTrick if player == self.playerToMove):
            # Sort the plays in the trick:
            # First, those that followed suit (in ascending rank order).
            # Then, any trump plays (also in ascending rank order).
            # The winning play is the last element in sortedPlays.
            (leader, leadCard) = self.currentTrick[0]
            suited_players = [
                (player, card.score)
                for (player, card) in self.currentTrick
                if card.suit == leadCard.suit
            ]
            trump_plays = [
                (player, card.score)
                for (player, card) in self.currentTrick
                if card.suit == self.trumpSuit
            ]
            sorted_plays = sorted(
                suited_players, key=lambda player_score: player_score[1]
            ) + sorted(trump_plays, key=lambda player_score: player_score[1])
            trick_winner = sorted_plays[-1][0]

            # Update the game state
            self.pointsTaken[trick_winner] += sum(card.score for _, card in self.currentTrick)
            self.discards += [card for (player, card) in self.currentTrick]
            self.currentTrick = []
            self.playerToMove = trick_winner

            # Both players draw from deck if applicable.
            if not self.isTalonClosed:
                if (self.marriageCardsRevealed[1] != [] and (len(self.deck) % 2 == 1)):
                    print(self.marriageCardsRevealed[1])
                    print('1: ' + str(len(self.deck)))
                if (self.marriageCardsRevealed[2] != [] and (len(self.deck) % 2 == 1)):
                    print(self.marriageCardsRevealed[2])
                    print('2: ' + str(len(self.deck)))
                # Winner takes the top card.
                self.playerHands[trick_winner] += [self.deck[0]]
                self.deck = self.deck[1:]
                # Other player takes the next card.
                self.playerHands[self.GetNextPlayer(trick_winner)] += [self.deck[0]]
                self.deck = self.deck[1:]
                # Close the talon if no cards remain.
                if not self.deck:
                    self.isTalonClosed = True

            # If the next player's hand is empty, the game is over.
            if self.playerHands[self.playerToMove] == []:
                return

    def GetMoves(self):
        """Get all possible moves from this state."""
        currentHand = self.playerHands[self.playerToMove]
        currentPoints = self.pointsTaken[self.playerToMove]
        # If the current player has more than 66 points, the game is over.
        if currentPoints >= 66:
            return []

        if self.isTalonClosed:
            # Talon is closed and current player leads.
            # Current player cannot close the talon, but can play any available marriages.
            if self.currentTrick == []:
                availablePlays = self.playerHands[self.playerToMove]
                moves = []
                for card in availablePlays:
                    marriage_partner = card.get_marriage_partner()
                    if (marriage_partner is not None) and (marriage_partner in availablePlays):
                        marriage_points = 20 + (20 * bool(card.suit == self.trumpSuit))
                    else:
                        marriage_points = None
                    moves.append(
                        SchnapsenMove(
                            card=card, close_talon=False, marriage_points=marriage_points
                        )
                    )
                return moves
            else:
                # Talon is closed and current player does not lead: special rules apply.
                (leader, leadCard) = self.currentTrick[0]
                sameSuitPlays = [card for card in currentHand if (card.suit == leadCard.suit)]
                sameSuitWinners = [card for card in sameSuitPlays if card.score > leadCard.score]
                trumpPlays = [card for card in currentHand if (card.suit == self.trumpSuit)]
                # If possible, must match suit and win.
                # Otherwise, must match suit if possible.
                # Otherwise, must play trump if possible.
                # If no same suit plays or trump plays, anything is playable.
                if sameSuitWinners != []:
                    availablePlays = sameSuitWinners
                elif sameSuitPlays != []:
                    availablePlays = sameSuitPlays
                elif trumpPlays != []:
                    availablePlays = trumpPlays
                else:
                    availablePlays = self.playerHands[self.playerToMove]
                return [SchnapsenMove(card=card, close_talon=False) for card in availablePlays]
        elif self.currentTrick == []:
            # Talon is open and current player leads: anything goes, including marriages
            # and closing the talon.
            availablePlays = currentHand
            moves = []
            for card in availablePlays:
                marriage_partner = card.get_marriage_partner()
                if (marriage_partner is not None) and (marriage_partner in availablePlays):
                    marriage_points = 20 + (20 * bool(card.suit == self.trumpSuit))
                else:
                    marriage_points = None
                for close_talon in [True, False]:
                    moves.append(
                        SchnapsenMove(
                            card=card, close_talon=close_talon, marriage_points=marriage_points
                        )
                    )
            return moves
        else:
            # Talon is open and current player follows: any card is playable, but
            # not marriages or closing the talon.
            availablePlays = currentHand
            return [SchnapsenMove(card=card, close_talon=False) for card in availablePlays]

    def GetResult(self, player):
        """
        Get the game result from the viewpoint of player.

        If the talon closer has more than 66 points, that player wins.
        Otherwise, if the talon was closed naturally, the first to 66 wins.
        If neither gets to 66, the last trick wins.
        """
        # If someone closed the talon, see if that player has >= 66 points
        if self.whoClosedTalon is not None:
            # If the current player closed the talon, they need >= 66 points to win.
            # If the other player closed the talon, the current player needs them to have < 66.
            didClosingPlayerGetEnoughPoints = (self.pointsTaken[self.whoClosedTalon] >= 66)
            if self.whoClosedTalon == player:
                return float(didClosingPlayerGetEnoughPoints)
            else:
                return 1.0 - float(didClosingPlayerGetEnoughPoints)
        else:
            if any(self.pointsTaken[p] >= 66 for p in self.pointsTaken):
                # 0 if current player has < 66, 1 otherwise.
                return float(self.pointsTaken[player] >= 66)
            else:
                # No one made it to 66. playerToMove wins.
                return float(player == self.playerToMove)

    def __repr__(self):
        """ Return a human-readable representation of the state
        """
        result = "P{} closed talon!".format(self.whoClosedTalon) if self.isTalonClosed else "Talon open"
        result += " | P%i: " % self.playerToMove
        result += ",".join(str(card) for card in self.playerHands[self.playerToMove])
        result += " | pointsTaken: %i" % self.pointsTaken[self.playerToMove]
        result += " | Trump: %s" % self.trumpSuit
        result += " | Trick: ["
        result += ",".join(("%i:%s" % (player, card)) for (player, card) in self.currentTrick)
        result += "]"
        result += " | Cards left: {}".format(len(self.deck))
        return result


class Node:
    """
    A node in the game tree.

    Note wins is always from the viewpoint of playerJustMoved.
    """
    def __init__(self, move=None, parent=None, playerJustMoved=None, isTalonClosed=False, whoClosedTalon=None):
        self.move = move  # the move that got us to this node - "None" for the root node
        self.parentNode = parent  # "None" for the root node
        self.childNodes = []
        self.wins = 0
        self.visits = 0
        self.avails = 1
        self.playerJustMoved = playerJustMoved  # part of the state that the Node needs later
        self.isTalonClosed = isTalonClosed  # part of the state that the Node needs later
        self.whoClosedTalon = whoClosedTalon    # part of the state that the Node needs later

    def GetUntriedMoves(self, legalMoves):
        """Return the elements of legalMoves for which this node does not have children."""
        # Find all moves for which this node *does* have children
        triedMoves = [child.move for child in self.childNodes]
        # Return all moves that are legal but have not been tried yet
        return [move for move in legalMoves if move not in triedMoves]

    def UCBSelectChild(self, legalMoves, exploration=0.7):
        """
        Use the UCB1 formula to select a child node, filtered by the given list of legal moves.

        exploration is a constant balancing between exploitation and exploration.
        """
        # Filter the list of children by the list of legal moves
        legalChildren = [child for child in self.childNodes if child.move in legalMoves]
        # Get the child with the highest UCB score
        s = max(
            legalChildren,
            key=lambda c:
                float(c.wins) / float(c.visits) + exploration * math.sqrt(math.log(c.avails) / float(c.visits))
        )
        # Update availability counts -- it is easier to do this now than during backpropagation
        for child in legalChildren:
            child.avails += 1

        # Return the child selected above
        return s

    def AddChild(self, m, p, isTalonClosed, whoClosedTalon):
        """
        Add a new child node for the move m.

        Return the added child node.
        """
        if whoClosedTalon is not None:
            w = whoClosedTalon
        elif m.close_talon:
            w = p
        else:
            w = None

        n = Node(
            move=m,
            parent=self,
            playerJustMoved=p,
            isTalonClosed=isTalonClosed or m.close_talon,
            whoClosedTalon=w
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
            self.wins += terminalState.GetResult(self.playerJustMoved)

    def __repr__(self):
        return "[M:%s W/V/A: %4i/%4i/%4i]" % (self.move, self.wins, self.visits, self.avails)

    def TreeToString(self, indent):
        """ Represent the tree as a string, for debugging purposes.
        """
        s = self.IndentString(indent) + str(self)
        for c in self.childNodes:
            s += c.TreeToString(indent + 1)
        return s

    def IndentString(self, indent):
        s = "\n"
        for i in range(1, indent + 1):
            s += "| "
        return s

    def ChildrenToString(self):
        s = ""
        for c in self.childNodes:
            s += str(c) + "\n"
        return s


def ISMCTS(rootstate, itermax, verbose=False):
    """
    Conduct an ISMCTS search for itermax iterations starting from rootstate.

    Return the best move from the rootstate.
    """
    rootnode = Node()

    for i in range(itermax):
        node = rootnode

        # Determinize
        state = rootstate.CloneAndRandomize(rootstate.playerToMove)

        # Select
        # While: node is fully expanded and non-terminal
        while state.GetMoves() != [] and node.GetUntriedMoves(state.GetMoves()) == []:
            node = node.UCBSelectChild(state.GetMoves())
            state.DoMove(node.move)

        # Expand
        untriedMoves = node.GetUntriedMoves(state.GetMoves())
        if untriedMoves != []:  # if we can expand (i.e. state/node is non-terminal)
            m = random.choice(untriedMoves)
            player = state.playerToMove
            state.DoMove(m)
            node = node.AddChild(
                m=m, p=player, isTalonClosed=state.isTalonClosed, whoClosedTalon=state.whoClosedTalon
            )  # add child and descend tree

        # Simulate
        while state.GetMoves() != []:  # while state is non-terminal
            moves = state.GetMoves()
            random_move = random.choice(moves)
            state.DoMove(random_move)

        # Backpropagate
        while node is not None:  # backpropagate from the expanded node and work back to the root node
            node.Update(state)
            node = node.parentNode

    # Output some information about the tree - can be omitted
    if (verbose):
        print(rootnode.TreeToString(0))
    else:
        print(rootnode.ChildrenToString())

    return max(rootnode.childNodes, key=lambda c: c.visits).move   # return the move that was most visited


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
