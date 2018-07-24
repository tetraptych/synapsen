"""Classes specific to the game of Schapsen."""
import copy
import random

from ISMCTS import GameState

SUIT_TO_UNICODE_MAP = {
    'S': u'♠️',
    'H': u'♥️',
    'C': u'♣️',
    'D': u'♦️',
}


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

    RANK_TO_REPR_MAP = dict(enumerate('??23456789TJQKA'))

    def __init__(self, rank, suit):
        """Initialize a playing card of the given rank and suit."""
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
        """Represent a card as a string."""
        return self.RANK_TO_REPR_MAP[self.rank] + SUIT_TO_UNICODE_MAP[self.suit]

    def __hash__(self):
        """A card's representation is an immutable, unique identifier."""
        return hash(self.__repr__())

    def __eq__(self, other):
        """Two cards are equal if they are equal in rank and suit."""
        return self.rank == other.rank and self.suit == other.suit

    def __ne__(self, other):
        """Two cards are not equal if they differ in rank or suit."""
        return self.rank != other.rank or self.suit != other.suit

    def __copy__(self):
        """Create a copy of the given card."""
        return Card(rank=self.rank, suit=self.suit)

    def __deepcopy__(self, memo):
        """Create a deep copy of the given card."""
        return Card(rank=self.rank, suit=self.suit)


class SchnapsenMove(object):
    """
    Represents a single move in a game of Schnapsen.

    A move consists of a decision to close the talon or not and a card to play.
    """

    def __init__(self, card, close_talon=False, marriage_points=None):
        """
        Initialize a move.

        A move consists of a card, closing or not, and the number of marriage points.
        """
        self.card = card
        self.close_talon = close_talon
        self.marriage_points = marriage_points

    def __repr__(self):
        """Represent a move as a string."""
        res = ''
        if self.close_talon:
            res += 'Close + '
        if self.marriage_points == 20:
            res += 'Marriage + '
        if self.marriage_points == 40:
            res += 'Royal Marriage + '
        res += self.card.__repr__()
        return res

    def __eq__(self, other):
        """Two moves are equal if they are the same card and both close the talon or not."""
        return self.card == other.card and self.close_talon == other.close_talon

    def __ne__(self, other):
        """Two moves are unequal if they are different cards or if only one closes the talon."""
        return self.card != other.card or self.close_talon != other.close_talon


class SchnapsenGameState(GameState):
    """A state of the game Schnapsen."""

    def __init__(self):
        """Initialize the game state."""
        self.numberOfPlayers = 2
        self.players = [1, 2]
        self.playerToMove = 1
        self.playerHands = {p: [] for p in self.players}
        self.marriageCardsRevealed = {p: set() for p in self.players}
        self.knownEmptySuits = {p: set() for p in self.players}
        self.handSize = 5
        self.discards = []  # Stores the cards that have been played already in this round
        self.currentTrick = []
        self.trumpSuit = None
        self.faceUpCard = None
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
        st.knownEmptySuits = copy.deepcopy(self.knownEmptySuits)
        st.handSize = self.handSize
        st.discards = copy.deepcopy(self.discards)
        st.currentTrick = copy.deepcopy(self.currentTrick)
        st.trumpSuit = self.trumpSuit
        st.faceUpCard = copy.deepcopy(self.faceUpCard)
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
        # The observer can remember the revealed bottom card.
        if st.faceUpCard is not None and st.faceUpCard not in seenCards:
            seenCards.append(st.faceUpCard)
        # The observer also knows about all declared marriages.
        seenCards += [
            card for p in st.players
            for card in st.marriageCardsRevealed[p]
            if (p != observer and card not in currentTrickCards)
        ]
        # The observer also knows about any empty suits the other player has.
        seenCards += [
            card
            for suit in st.knownEmptySuits[st.GetNextPlayer(observer)]
            for card in [Card(rank=rank, suit=suit) for rank in range(10, 14)]
            if card not in seenCards
        ]

        # The observer can't see the rest of the deck.
        unseenCards = [card for card in st.GetCardDeck() if card not in seenCards]

        assert(len(unseenCards) + len(seenCards) == len(st.GetCardDeck()))

        # Deal the unseen cards to the other players.
        random.shuffle(unseenCards)
        for p in st.players:
            if p != observer:
                # Deal cards to player p, accounting for revealed marriages.
                playerHand = [card for card in st.marriageCardsRevealed[p]]
                # If the deck is empty, someone must have the face-up card.
                if len(st.deck) == 0 and st.faceUpCard not in st.playerHands[observer]:
                    # If the observer doesn't have it and it hasn't been played yet,
                    # the other player must have it.
                    if st.faceUpCard not in (st.discards + currentTrickCards):
                        playerHand.append(st.faceUpCard)
                numCardsToDeal = len(st.playerHands[p]) - len(playerHand)
                playerHand += unseenCards[: numCardsToDeal]
                st.playerHands[p] = [card for card in playerHand]
                # Remove those cards from unseenCards.
                unseenCards = unseenCards[numCardsToDeal:]

        st.deck = unseenCards
        # If there are cards left in the deck, the face-up card is on the bottom.
        if len(st.deck) != 0:
            st.deck += [st.faceUpCard]

        return st

    def GetCardDeck(self):
        """Construct a standard deck of 20 cards (ten through ace of each suit)."""
        return [Card(rank, suit) for rank in range(10, 14 + 1) for suit in ['C', 'D', 'H', 'S']]

    def Deal(self):
        """Reset the game state for the beginning of a new round and deal the cards."""
        self.discards = []
        self.currentTrick = []
        self.pointsTaken = {p: 0 for p in range(1, self.numberOfPlayers + 1)}

        # Construct a deck, shuffle it, and deal it to the players.
        deck = self.GetCardDeck()
        random.shuffle(deck)
        for p in range(1, self.numberOfPlayers + 1):
            self.playerHands[p] = deck[: self.handSize]
            deck = deck[self.handSize:]

        # Set the remaining cards to draw.
        self.deck = deck
        # Choose the trump suit for this round.
        self.faceUpCard = self.deck[-1]
        self.trumpSuit = self.faceUpCard.suit

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
            self.marriageCardsRevealed[self.playerToMove].add(
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

        # If the talon is closed and the current trick is over, record empty suits.
        if self.isTalonClosed and len(self.currentTrick) == 2:
            suits = [card.suit for _, card in self.currentTrick]
            # If the suits were different, the second player must be missing the lead suit.
            if suits[0] != suits[1]:
                self.knownEmptySuits[self.playerToMove].add(suits[0])
                # If additionally neither suit was trump, the second player is out of trump.
                if (suits[0] != self.trumpSuit) and (suits[1] != self.trumpSuit):
                    self.knownEmptySuits[self.playerToMove].add(self.trumpSuit)

        # Find the next player.
        self.playerToMove = self.GetNextPlayer(self.playerToMove)

        # If both players have played, then the trick is over.
        if len(self.currentTrick) == 2:
            # Determine the winner.
            trick_winner = self.GetTrickWinner(self.currentTrick)

            # Update the game state.
            self.pointsTaken[trick_winner] += sum(card.score for _, card in self.currentTrick)
            self.discards += [card for (player, card) in self.currentTrick]
            self.currentTrick = []
            self.playerToMove = trick_winner

            # Both players draw from deck if applicable.
            if not self.isTalonClosed:
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

    def GetTrickWinner(self, completed_trick):
        """
        Determine the winner of a trick in which all players have played.

        Returns the winner as a player id.

        Sort the plays in the trick:
        First, those that followed suit (in ascending rank order).
        Then, any trump plays (also in ascending rank order).
        The winning play is the last element in sortedPlays.
        """
        (leader, leadCard) = completed_trick[0]
        suited_plays = [
            (player, card.score)
            for (player, card) in completed_trick
            if card.suit == leadCard.suit
        ]
        trump_plays = [
            (player, card.score)
            for (player, card) in completed_trick
            if card.suit == self.trumpSuit
        ]
        sorted_plays = sorted(
            suited_plays, key=lambda player_score: player_score[1]
        ) + sorted(trump_plays, key=lambda player_score: player_score[1])
        return sorted_plays[-1][0]

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
            open_moves = []
            close_moves = []
            for card in availablePlays:
                marriage_partner = card.get_marriage_partner()
                if (marriage_partner is not None) and (marriage_partner in availablePlays):
                    marriage_points = 20 + (20 * bool(card.suit == self.trumpSuit))
                else:
                    marriage_points = None
                open_moves.append(
                    SchnapsenMove(card=card, close_talon=False, marriage_points=marriage_points)
                )
                close_moves.append(
                    SchnapsenMove(card=card, close_talon=True, marriage_points=marriage_points)
                )
            return open_moves + close_moves
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
        """Return a human-readable representation of the state."""
        if self.whoClosedTalon:
            result = 'P{} closed talon!'.format(self.whoClosedTalon)
        elif self.isTalonClosed:
            result = 'Talon exhausted!'
        else:
            result = 'Talon open'
        result += ' | P%i: ' % self.playerToMove
        result += ' , '.join(str(card) for card in self.playerHands[self.playerToMove])
        result += '  | pointsTaken: '
        result += ', '.join(
            ['P{}: {}'.format(player, self.pointsTaken[player]) for player in self.players])
        result += ' | Trump suit: %s ' % SUIT_TO_UNICODE_MAP[self.trumpSuit]
        result += ' | Face-up card: %s ' % self.faceUpCard
        result += ' | Trick: ['
        result += ', '.join(('%i:%s' % (player, card)) for (player, card) in self.currentTrick)
        result += ']'
        result += ' | Cards left: {}'.format(len(self.deck))
        result += ' | ' + ', '.join(
            [
                'P{}: {}'.format(
                    player, [SUIT_TO_UNICODE_MAP[suit] for suit in self.knownEmptySuits[player]]
                )
                for player in self.players
            ])
        return result
