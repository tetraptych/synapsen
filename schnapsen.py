#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Classes specific to the game of Schapsen."""
import math
import random

from ISMCTS import GameState

SUIT_TO_UNICODE_MAP = {
    'S': u'♠️ ',
    'H': u'♥️ ',
    'C': u'♣️ ',
    'D': u'♦️ ',
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
        if self.rank not in {12, 13}:
            return None
        else:
            # Return 13 if the current card is rank 12 and 12 if it is 13.
            return Card(rank=12 + (self.rank == 12), suit=self.suit)

    def __repr__(self):
        """Represent a card as a string."""
        return self.RANK_TO_REPR_MAP[self.rank] + SUIT_TO_UNICODE_MAP[self.suit]

    def __hash__(self):
        """A card's representation is an immutable, unique identifier."""
        return hash((self.suit, self.rank))

    def __eq__(self, other):
        """Two cards are equal if they are equal in rank and suit."""
        return (self.suit, self.rank) == (other.suit, other.rank)

    def __copy__(self):
        """Create a copy of the given card."""
        return Card(rank=self.rank, suit=self.suit)

    def __deepcopy__(self, memo):
        """Create a deep copy of the given card."""
        return Card(rank=self.rank, suit=self.suit)


FULL_DECK = [Card(rank, suit) for rank in range(10, 14 + 1) for suit in ['C', 'D', 'H', 'S']]


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
        return (self.close_talon, self.card) == (other.close_talon, other.card)

    def __hash__(self):
        """A move's representation is an immutable, unique identifier."""
        return hash((self.close_talon, self.card))


class SchnapsenGameState(GameState):
    """A state of the game Schnapsen."""

    def __init__(self, omniscient_players=set()):
        """Initialize the game state."""
        self.numberOfPlayers = 2
        self.players = [1, 2]
        self.playerHands = {p: [] for p in self.players}
        self.omniscient_players = omniscient_players
        self.playerToMove = 1
        self.marriageCardsRevealed = {p: set() for p in self.players}
        self.knownEmptySuits = {p: set() for p in self.players}
        self.isTalonClosed = False
        self.whoClosedTalon = None
        self.gamePointsAtStake = {1: 1.0, 2: 1.0}
        self.winner = None
        # Note: this sets other attributes.
        self.Deal()

    def Clone(self):
        """Create a deep clone of this game state."""
        st = SchnapsenGameState(omniscient_players=self.omniscient_players)
        st.players = self.players
        st.numberOfPlayers = self.numberOfPlayers
        st.playerToMove = self.playerToMove
        st.playerHands = {p: [card for card in self.playerHands[p]] for p in self.players}
        st.marriageCardsRevealed = {
            p: {card for card in self.marriageCardsRevealed[p]} for p in self.players
        }
        st.knownEmptySuits = {
            p: {suit for suit in self.knownEmptySuits[p]} for p in self.players
        }
        st.discards = [card for card in self.discards]
        st.currentTrick = [card for card in self.currentTrick]
        st.trumpSuit = self.trumpSuit
        st.faceUpCard = self.faceUpCard
        st.pointsTaken = {p: self.pointsTaken[p] for p in self.players}
        st.isTalonClosed = self.isTalonClosed
        st.whoClosedTalon = self.whoClosedTalon
        st.gamePointsAtStake = self.gamePointsAtStake
        st.deck = [card for card in self.deck]
        st.winner = self.winner
        return st

    def CloneAndRandomize(self, observer):
        """
        Create a deep clone of this game state.

        All information not visible to the specified observer player is randomized.
        """
        st = self.Clone()
        # If the observer is omniscient, do not randomize.
        if observer in self.omniscient_players:
            return st

        other_player = self.GetNextPlayer(observer)
        # The observer can see its own hand and the cards in the current trick.
        # The observer can also remember the cards played in previous tricks.
        # The observer can remember the revealed bottom card.
        currentTrickCards = [card for (_, card) in st.currentTrick]
        seenCards = set(
            st.playerHands[observer] + st.discards + currentTrickCards + [st.faceUpCard]
        )
        # The observer also knows about all declared marriages.
        seenCards.update(st.marriageCardsRevealed[other_player])
        # The observer also knows about any empty suits the other player has.
        seenCards.update(
            Card(rank=rank, suit=suit)
            for suit in st.knownEmptySuits[other_player]
            for rank in range(10, 14)
        )

        # The observer can't see the rest of the deck.
        unseenCards = [card for card in st.GetCardDeck() if card not in seenCards]

        assert(len(unseenCards) + len(seenCards) == len(st.GetCardDeck()))

        # Deal the unseen cards to the other player.
        random.shuffle(unseenCards)

        # Deal cards to player p, accounting for revealed marriages.
        playerHand = [card for card in st.marriageCardsRevealed[other_player]]
        # If the deck is empty, someone must have the face-up card.
        if len(st.deck) == 0 and st.faceUpCard not in st.playerHands[observer]:
            # If the observer doesn't have it and it hasn't been played yet,
            # the other player must have it.
            if st.faceUpCard not in (st.discards + currentTrickCards):
                playerHand.append(st.faceUpCard)
        numCardsToDeal = len(st.playerHands[other_player]) - len(playerHand)
        playerHand += unseenCards[:numCardsToDeal]
        st.playerHands[other_player] = [card for card in playerHand]
        # Remove those cards from unseenCards.
        unseenCards = unseenCards[numCardsToDeal:]

        st.deck = unseenCards
        # If there are cards left in the deck, the face-up card is on the bottom.
        if len(st.deck) != 0:
            st.deck += [st.faceUpCard]

        return st

    def GetCardDeck(self):
        """Construct a standard deck of 20 cards (ten through ace of each suit)."""
        return [card for card in FULL_DECK]

    def Deal(self):
        """Reset the game state for the beginning of a new round and deal the cards."""
        self.discards = []
        self.currentTrick = []
        self.pointsTaken = {p: 0 for p in self.players}

        # Construct a deck, shuffle it, and deal it to the players.
        deck = self.GetCardDeck()
        random.shuffle(deck)
        for p in self.players:
            self.playerHands[p] = deck[: 5]
            deck = deck[5:]

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
        other_player = (self.playerToMove % 2) + 1

        if self.whoClosedTalon is None:
            game_points_if_current_player_wins = 3.0 - math.ceil(
                self.pointsTaken[other_player] / 33
            )
            game_points_if_other_player_wins = 3.0 - math.ceil(
                self.pointsTaken[self.playerToMove] / 33
            )
            self.gamePointsAtStake = {
                self.playerToMove: game_points_if_current_player_wins,
                other_player: game_points_if_other_player_wins
            }

        # Close the talon if part of the current SchnapsenMove.
        if move.close_talon:
            self.isTalonClosed = True
            self.whoClosedTalon = self.playerToMove
            # FIXME: Account for marriages.
            game_points_if_closer_wins = 3.0 - math.ceil(self.pointsTaken[other_player] / 33)
            game_points_if_closer_loses = {
                3.0: 3.0,
                2.0: 2.0,
                1.0: 2.0
            }[game_points_if_closer_wins]
            self.gamePointsAtStake = {
                self.playerToMove: game_points_if_closer_wins,
                other_player: game_points_if_closer_loses
            }

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
                self.winner = self.playerToMove
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
            self.discards += [card for _, card in self.currentTrick]
            self.currentTrick = []
            self.playerToMove = trick_winner

            # Both players draw from deck if applicable.
            if not self.isTalonClosed:
                # Winner takes the top card.
                self.playerHands[trick_winner] += [self.deck[0]]
                # Other player takes the next card.
                self.playerHands[self.GetNextPlayer(trick_winner)] += [self.deck[1]]
                self.deck = self.deck[2:]
                # Close the talon if no cards remain.
                if not self.deck:
                    self.isTalonClosed = True
            else:
                # Determine winner when no one has any cards left.
                # Only applicable when the talon is closed.
                if all(len(self.playerHands[player]) == 0 for player in self.playerHands):
                    if all(self.pointsTaken[player] < 66 for player in self.pointsTaken):
                        # If someone closed the talon but no one has 66 points, that player loses.
                        if self.whoClosedTalon is not None:
                            self.winner = (self.whoClosedTalon % 2) + 1
                            return
                        # If deck is empty and no one has 66 points, current player wins.
                        elif len(self.deck) == 0:
                            self.winner = trick_winner
                            return

            # If the trick winner has enough points, they win.
            if self.pointsTaken[trick_winner] >= 66:
                self.winner = trick_winner

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
        # If the winner already exists, no further moves are possible.
        if self.winner is not None:
            return []

        currentHand = self.playerHands[self.playerToMove]

        if self.isTalonClosed:
            # Talon is closed and current player leads.
            # Current player cannot close the talon, but can play any available marriages.
            if self.currentTrick == []:
                moves = []
                for card in currentHand:
                    marriage_partner = card.get_marriage_partner()
                    if (marriage_partner is not None) and (marriage_partner in currentHand):
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
                leadCard = self.currentTrick[0][1]
                sameSuitPlays = [card for card in currentHand if card.suit == leadCard.suit]
                sameSuitWinners = [card for card in sameSuitPlays if card.score > leadCard.score]
                trumpPlays = [card for card in currentHand if card.suit == self.trumpSuit]
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
                    availablePlays = currentHand
                return [SchnapsenMove(card=card, close_talon=False) for card in availablePlays]
        elif self.currentTrick == []:
            # Talon is open and current player leads: anything goes, including marriages
            # and closing the talon.
            open_moves = []
            close_moves = []
            for card in currentHand:
                marriage_partner = card.get_marriage_partner()
                if (marriage_partner is not None) and (marriage_partner in currentHand):
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
            return [SchnapsenMove(card=card, close_talon=False) for card in currentHand]

    def GetResult(self, player):
        """
        Get the game result from the viewpoint of player.

        If the talon closer has more than 66 points, that player wins.
        Otherwise, if the talon was closed naturally, the first to 66 wins.
        If neither gets to 66, the last trick wins.
        """
        other_player = (player % 2) + 1
        # If someone closed the talon, see if that player has >= 66 points.
        if self.whoClosedTalon is not None:
            did_current_player_close_talon = (player == self.whoClosedTalon)
            did_player_who_closed_talon_win = (self.pointsTaken[self.whoClosedTalon] >= 66)
            did_current_player_win = (
                did_current_player_close_talon and did_player_who_closed_talon_win
            ) or (
                not did_current_player_close_talon and not did_player_who_closed_talon_win
            )
            # If the current player won, give them the points at stake.
            if did_current_player_win:
                return float(self.gamePointsAtStake[player])
            # Otherwise, award the game points to the other player.
            else:
                return -1.0 * float(self.gamePointsAtStake[other_player])
        else:
            if self.pointsTaken[player] >= 66:
                return self.gamePointsAtStake[player]
            elif self.pointsTaken[other_player] >= 66:
                return -1.0 * float(self.gamePointsAtStake[other_player])
            else:
                # No one made it to 66. playerToMove wins.
                return 2.0 * float(player == self.playerToMove) - 1

    def __repr__(self):
        """Return a human-readable representation of the state."""
        if self.whoClosedTalon:
            result = 'P{} closed talon!'.format(self.whoClosedTalon)
        elif self.isTalonClosed:
            result = 'Talon exhausted!'
        else:
            result = 'Talon open'
        result += ' | P%i: ' % self.playerToMove
        result += ', '.join(str(card) for card in self.playerHands[self.playerToMove])
        result += '  | pointsTaken: '
        result += ', '.join(
            ['P{}: {}'.format(player, self.pointsTaken[player]) for player in self.players])
        result += ' | Trump suit: %s' % SUIT_TO_UNICODE_MAP[self.trumpSuit]
        result += ' | Face-up card: %s' % self.faceUpCard
        result += ' | Trick: ['
        result += ', '.join((' %i: %s' % (player, card)) for (player, card) in self.currentTrick)
        result += ']'
        result += ' | Cards left: {}'.format(len(self.deck))
        result += ' | Stake: {}'.format(self.gamePointsAtStake)
        result += ' | Empty: ' + ', '.join(
            [
                'P{}: {}'.format(
                    player,
                    ', '.join([SUIT_TO_UNICODE_MAP[suit] for suit in self.knownEmptySuits[player]])
                )
                for player in self.players
            ])
        return result

    def deep_repr(self):
        """A representation of all information in the game state from an omniscient POV."""
        return self.__repr__() + '\nDeck: ' + ', '.join([card.__repr__() for card in self.deck])
