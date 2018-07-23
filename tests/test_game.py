"""Test basic AI functionality."""
import random

import synapsen

# Use a fixed random seed to ensure consistency across separate test runs.
random.seed(1)


def test_computer_vs_computer():
    """Initialize two computer players and have them play a quick game."""
    synapsen.PlayGame(game_type='computer-computer', difficulty='trivial')
