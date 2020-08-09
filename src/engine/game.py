import typing
from typing import List, Tuple
from enum import Enum, IntEnum, auto
from functools import total_ordering
from collections import Counter


class Suit(Enum):
    d = auto()
    c = auto()
    s = auto()
    h = auto()


class HandRank(IntEnum):
    HIGH_CARD = 0
    ONE_PAIR = 1
    TWO_PAIRS = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8

@total_ordering
class Card:
    def __init__(self, suit: Suit, height: str):
        height_to_int = dict(zip('23456789TJQKA', range(13)))
        self.suit = suit
        self.height = height
        self.int_height = height_to_int[height]

    def __repr__(self) -> str:
        return f'{self.height}{self.suit.name}'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Card):
            raise NotImplementedError

        return (self.suit, self.height) == (other.suit, other.height)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Card):
            raise NotImplementedError
        c1 = (self.int_height, self.suit.name)
        c2 = (other.int_height, other.suit.name)

        return c1 < c2

class SingleHand():
    def __init__(self, cards: List[Card] = []):
        self.cards = cards

    def __len__(self) -> int:
        return len(self.cards)

    def __repr__(self) -> str:
        return ' '.join(str(card) for card in self.cards)

    def add_card(self, card: Card):
        self.cards.append(card)

class SingleHandStrength():
    def __init__(self, hand: SingleHand):
        self.hand = hand
        self.strength = self._compute_strength()

    def _compute_strength(self):
        def is_flush(
                cards: List[Card],
                suit_counter: typing.Counter[Suit],
        ) -> Tuple[bool, List[int]]:
            # check = len(cards) == 5 and len(set(card.suit for card in cards)) == 1
            check = len(cards) == 5 and len(suit_counter) == 1

            if check:
                height = [card.int_height for card in cards[::-1]]
            else:
                height = []

            return check, height

        def is_straight(
                cards: List[Card],
                height_counter: typing.Counter[int]
        ) -> Tuple[bool, int]:
            # If there is less than 5 cards or any pair, three of kind
            # or four of a kind, there cannot be a straight
            if len(cards) != 5 or len(height_counter) != 5:
                return False, -1

            heights = [card.int_height for card in cards]
            # # If there is any pair, there cannot be a straight
            # if len(set(heights)) != 5:
            #     return False, -1

            # If there is no pair and the smallest one is 4 values
            # away from the biggest, we have a straight
            if heights[0] == heights[-1] - 4:
                return True, heights[-1]

            # Special case for the ace to five straight
            if heights == [0, 1, 2, 3, 12]:
                return True, 3

            return False, -1

        def is_full_house(
                cards: List[Card],
                height_counter: typing.Counter[int]
        ) -> Tuple[bool, Tuple[int, int]]:
            if len(height_counter) != 2:
                return False, (-1, -1)

            most_common = height_counter.most_common()
            (
                (first_mc_height, first_mc_count),
                (second_mc_height, second_mc_count),
            ) = most_common

            if first_mc_count == 3 and second_mc_count == 2:
                return True, (first_mc_height, second_mc_height)

            return False, (-1, -1)

        def is_n_of_a_kind(
                cards: List[Card],
                n: int,
                height_counter: typing.Counter[int]
        ) -> Tuple[bool, int]:
            (mc_height, mc_count), *_ = height_counter.most_common()
            if mc_count == n:
                return True, mc_height

            return False, -1

        def is_four_of_a_kind(
                cards: List[Card],
                height_counter: typing.Counter[int]
        ) -> Tuple[bool, int]:
            return is_n_of_a_kind(cards, 4, height_counter)

        def is_three_of_a_kind(
                cards: List[Card],
                height_counter: typing.Counter[int]
        ) -> Tuple[bool, int]:
            return is_n_of_a_kind(cards, 3, height_counter)

        def is_two_pairs(
                cards: List[Card],
                height_counter: typing.Counter[int]
        ) -> Tuple[bool, int, int, int]:
            if len(height_counter) < 3:
                return False, -1, -1, -1

            most_common = height_counter.most_common()
            (
                (first_mc_height, first_mc_count),
                (second_mc_height, second_mc_count),
                (third_mc_height, third_mc_count)
            ) = most_common

            if first_mc_count == 2 and second_mc_count == 2 and third_mc_count == 1:
                if second_mc_height > first_mc_height:
                    first_mc_height, second_mc_height = second_mc_height, first_mc_height
                return True, first_mc_height, second_mc_height, third_mc_count

            return False, -1, -1, -1

        def is_one_pair(
                cards: List[Card],
                height_counter: typing.Counter[int]
        ) -> Tuple[bool, int]:
            return is_n_of_a_kind(cards, 2, height_counter)

        cards = sorted(self.hand.cards)
        suit_counter = Counter(card.suit for card in cards)
        height_counter = Counter(card.int_height for card in cards)

        flush_check, flush_val = is_flush(cards, suit_counter)
        straight_check, straight_val = is_straight(cards, height_counter)

        if flush_check:
            if straight_check:
                return HandRank.STRAIGHT_FLUSH, straight_val

            return HandRank.FLUSH, *flush_val

        if straight_check:
            return HandRank.STRAIGHT, straight_val

        four_of_a_kind_check, four_of_kind_val = is_four_of_a_kind(
            cards,
            height_counter
        )
        if four_of_a_kind_check:
            return HandRank.FOUR_OF_A_KIND, four_of_kind_val

        full_house_check, full_house_val = is_full_house(cards, height_counter)
        if full_house_check:
            return HandRank.FULL_HOUSE, *full_house_val

        three_of_a_kind_check, three_of_kind_val = is_three_of_a_kind(
            cards,
            height_counter
        )
        if three_of_a_kind_check:
            return HandRank.THREE_OF_A_KIND, three_of_kind_val

        two_pairs_check, two_pairs_val = is_two_pairs(cards, height_counter)
        if two_pairs_check:
            return HandRank.TWO_PAIRS, *two_pairs_val

# class HandRank(IntEnum):
#     HIGH_CARD = 0
#     ONE_PAIR = 1
#     TWO_PAIRS = 2

        four_of_a_kind = is_four_of_a_kind(cards, height_counter)
        full_house = is_full_house(cards, height_counter)
        print(
            cards,
            '--> fl', flush_check,
            'st', straight_check,
            'foak', four_of_a_kind,
            'fh', full_house
        )

class Hand():
    def __init__(self):
        self.back = SingleHand()
        self.middle = SingleHand()
        self.front = SingleHand()

# class Game():
#     def __init__(self):
#         print('salut')
#         p1_hand = Hand()
#         p2_hand = Hand()

hands = [
    SingleHand([
        Card(Suit.h, 'A'),
        Card(Suit.h, 'K'),
        Card(Suit.h, 'Q'),
        Card(Suit.h, 'J'),
        Card(Suit.h, 'T')
    ]),
    SingleHand([
        Card(Suit.s, '6'),
        Card(Suit.s, 'T'),
        Card(Suit.s, '7'),
        Card(Suit.s, '9'),
        Card(Suit.s, '8')
    ]),
    SingleHand([
        Card(Suit.c, '3'),
        Card(Suit.h, '3'),
        Card(Suit.s, '3'),
        Card(Suit.d, '3'),
        Card(Suit.s, '7')
    ]),
    SingleHand([
        Card(Suit.c, 'K'),
        Card(Suit.s, 'K'),
        Card(Suit.h, 'K'),
        Card(Suit.c, '5'),
        Card(Suit.s, '5')
    ]),
    SingleHand([
        Card(Suit.c, 'A'),
        Card(Suit.h, 'T'),
        Card(Suit.h, '8'),
        Card(Suit.c, '8'),
        Card(Suit.s, '8')
    ]),
    SingleHand([
        Card(Suit.c, '7'),
        Card(Suit.h, '8'),
        Card(Suit.h, '9'),
        Card(Suit.c, 'T'),
        Card(Suit.s, 'J'),
    ]),
    SingleHand([
        Card(Suit.c, '2'),
        Card(Suit.c, '3'),
        Card(Suit.c, '5'),
        Card(Suit.c, '4'),
        Card(Suit.c, '6')
    ]),
    SingleHand([
        Card(Suit.c, '2'),
        Card(Suit.c, '3'),
        Card(Suit.d, 'A'),
        Card(Suit.c, '4'),
        Card(Suit.c, '5')
    ]),
]

for hand in hands:
    print('##########')
    SingleHandStrength(hand)
