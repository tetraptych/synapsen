## Synapsen

Synapsen is a stand-alone, command-line implementation of the classic card game [Schnapsen](https://en.wikipedia.org/wiki/Schnapsen). The computer players use an [Information Set Monte Carlo Tree Search (ISMCTS)](http://www.aifactory.co.uk/newsletter/2013_01_reduce_burden.htm) algorithm to determine [satisficing](https://en.wikipedia.org/wiki/Satisficing) moves.

Synapsen is written in Python and requires Python3 or higher.


### Usage

Clone this repository and navigate to the new directory.

Run `python3 synapsen.py --game-type 'human-computer' --difficulty 'easy'` to begin a game of Schapsen.

The command-line arguments can be configured as follows:
```
usage: synapsen.py [-h] [-gt GAME_TYPE] [-d DIFFICULTY]

This begins a game of Schnapsen.

optional arguments:
  -h, --help            show this help message and exit
  -gt GAME_TYPE, --game-type GAME_TYPE
                        The type of the players in the game.
                        Available options are:
                            - human-human
                            - human-computer
                            - computer-computer
                            - computer-human
  -d DIFFICULTY, --difficulty DIFFICULTY
                        The difficulty of any computer players in the game.
                        Available options are:
                            - easy
                            - medium
                            - hard
                            - insane
```

### Etymology

"Synapsen" means _synapses_ in German.


### Limitations

- Trading the Jack of the trump suit for the face-up trump card is not yet implemented.
- Computer players do not explicitly infer the highest remaining card their opponent has in a particular suit when the talon is closed. For example, if the computer player led with the king of spades and the opponent played the queen of spades, the computer _would not_ infer that the opponent cannot have the ten or ace of spades. Computer players _do_ infer when their opponent has no cards left of a particular suit when the talon is closed: if the opponent responds to the king of spades with any non-spade card, the computer player understands that the opponent has no spades in hand.
