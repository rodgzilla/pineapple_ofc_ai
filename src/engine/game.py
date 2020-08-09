from dataclasses import dataclass
from enum import Enum, auto
from functools import total_ordering

class Suit(Enum):
    d = auto()
    c = auto()
    s = auto()
    h = auto()

@total_ordering
class Card:
    def __init__(self, suit: Suit, height: str):
        self.suit = suit
        self.height = height
        self._height_to_int = dict(zip('23456789TJQKA', range(13)))

    def __repr__(self) -> str:
        return f'{self.height}{self.suit.name}'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Card):
            raise NotImplementedError

        return (self.suit, self.height) == (other.suit, other.height)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Card):
            raise NotImplementedError
        c1 = (self.suit.name, self._height_to_int[self.height])
        c2 = (other.suit.name, self._height_to_int[other.height])

        return c1 < c2

class SingleHand():
    def __init__(self):
        self.cards = []

    def __len__(self):
        return len(self.cards)

    def __repr__(self):
        return ' '.join(str(card) for card in self.cards)

    def add_card(self, card: Card):
        self.cards.append(card)

class SingleHandStrength():
    def __init__(self, hand: SingleHand):
        self.hand = hand
        self.strength = self._compute_strength()

    def _compute_strength(self):
        pass


class Hand():
    def __init__(self):
        self.back = SingleHand()
        self.middle = SingleHand()
        self.front = SingleHand()

class Game():
    def __init__(self):
        print('salut')
        p1_hand = Hand()
        p2_hand = Hand()

# if __name__ == '__main__':
game = Game()
c1 = Card(Suit.c, 'A')
c2 = Card(Suit.h, 'T')
c3 = Card(Suit.h, '8')
print(c1)
