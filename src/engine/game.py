from typing import List, Tuple, Union, Optional, cast
from enum import Enum, IntEnum, auto
from functools import total_ordering
from collections import Counter, defaultdict
import random


class Suit(Enum):
    d = auto()
    c = auto()
    s = auto()
    h = auto()


class HandId(Enum):
    front = auto()
    middle = auto()
    back = auto()


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
    def __init__(self, cards: Optional[List[Card]] = None):
        if cards is None:
            self.cards = []
        else:
            self.cards = cards

    def __len__(self) -> int:
        return len(self.cards)

    def __repr__(self) -> str:
        return ' '.join(str(card) for card in self.cards)

    def add_card(self, card: Card):
        self.cards.append(card)


class SingleHandStrength():
    def __init__(self, hand: SingleHand):
        self.cards = sorted(hand.cards)
        self.suit_counter = Counter(card.suit for card in self.cards)
        self.height_counter = Counter(card.int_height for card in self.cards)
        self.rank, self.val = self._compute_strength()

    def __repr__(self) -> str:
        return f'{self.rank.name}, {self.val}'

    def _compute_strength(self) -> Tuple[HandRank, Union[int, Tuple[int, ...]]]:
        def is_flush() -> Tuple[bool, Tuple[int, ...]]:
            check = len(self.cards) == 5 and len(self.suit_counter) == 1

            if check:
                height = tuple([card.int_height for card in self.cards[::-1]])
            else:
                height = (1,) * len(self.cards)

            return check, height

        def is_straight() -> Tuple[bool, int]:
            # If there is less than 5 cards or any pair, three of kind
            # or four of a kind, there cannot be a straight
            if len(self.cards) != 5 or len(self.height_counter) != 5:
                return False, -1

            heights = [card.int_height for card in self.cards]
            # If there is no pair and the smallest one is 4 values
            # away from the biggest, we have a straight
            if heights[0] == heights[-1] - 4:
                return True, heights[-1]

            # Special case for the ace to five straight
            if heights == [0, 1, 2, 3, 12]:
                return True, 3

            return False, -1

        def is_full_house() -> Tuple[bool, Tuple[int, ...]]:
            if len(self.height_counter) != 2:
                return False, (-1, -1)

            most_common = self.height_counter.most_common()
            (
                (first_mc_height, first_mc_count),
                (second_mc_height, second_mc_count),
            ) = most_common

            if first_mc_count == 3 and second_mc_count == 2:
                return True, (first_mc_height, second_mc_height)

            return False, (-1, -1)

        def is_n_of_a_kind(n: int) -> Tuple[bool, int]:
            (mc_height, mc_count), *_ = self.height_counter.most_common()
            if mc_count == n:
                return True, mc_height

            return False, -1

        def is_four_of_a_kind() -> Tuple[bool, int]:
            return is_n_of_a_kind(4)

        def is_three_of_a_kind() -> Tuple[bool, int]:
            return is_n_of_a_kind(3)

        def is_two_pairs() -> Tuple[bool, Tuple[int, ...]]:
            if len(self.height_counter) != 3:
                return False, (-1, -1, -1)

            (
                (first_mc_height, first_mc_count),
                (second_mc_height, second_mc_count),
                (third_mc_height, third_mc_count)
            ) = self.height_counter.most_common()

            if first_mc_count == 2 and \
               second_mc_count == 2 and \
               third_mc_count == 1:
                if second_mc_height > first_mc_height:
                    (
                        first_mc_height,
                        second_mc_height
                    ) = second_mc_height, first_mc_height
                return True, (
                    first_mc_height,
                    second_mc_height,
                    third_mc_height
                )

            return False, (-1, -1, -1)

        def is_one_pair() -> Tuple[bool, Tuple[int, ...]]:
            if (len(self.cards) == 5 and len(self.height_counter) != 4) or \
               (len(self.cards) == 3 and len(self.height_counter) != 2):
                return False, (-1,) * (len(self.cards) - 1)

            (mc_height, mc_count), *_ = self.height_counter.most_common()

            if mc_count == 2:
                non_paired_cards_heights = [
                    card.int_height
                    for card in self.cards[::-1]
                    if card.int_height != mc_height
                ]
                return True, (mc_height, *non_paired_cards_heights)

            return False, (-1,) * (len(self.cards) - 1)

        def is_high_card() -> Tuple[bool, Tuple[int, ...]]:
            if (len(self.cards) == 5 and len(self.height_counter) != 5) or \
               (len(self.cards) == 3 and len(self.height_counter) != 3):
                return False, (-1,) * len(self.cards)

            return True, tuple([card.int_height for card in self.cards[::-1]])

        flush_check, flush_val = is_flush()
        straight_check, straight_val = is_straight()

        if flush_check:
            if straight_check:
                return HandRank.STRAIGHT_FLUSH, straight_val

            return HandRank.FLUSH, flush_val

        if straight_check:
            return HandRank.STRAIGHT, straight_val

        for rank, check_fun in zip(
                [
                    HandRank.FOUR_OF_A_KIND,
                    HandRank.FULL_HOUSE,
                    HandRank.THREE_OF_A_KIND,
                    HandRank.TWO_PAIRS,
                    HandRank.ONE_PAIR
                ],
                [
                    is_four_of_a_kind,
                    is_full_house,
                    is_three_of_a_kind,
                    is_two_pairs,
                    is_one_pair
                ]
        ):
            check, value = check_fun()
            if check:
                return rank, cast(Union[int, Tuple[int, ...]], value)

        high_card_check, high_card_value = is_high_card()

        if not high_card_check:
            print('Strange behavior')

        return HandRank.HIGH_CARD, high_card_value

bonus_map = {
    HandId.back: {
        HandRank.STRAIGHT_FLUSH: {
            12: 25,
            11: 15,
            10: 15,
            9: 15,
            8: 15,
            7: 15,
            6: 15,
            5: 15,
            4: 15,
            3: 15,
        },
        HandRank.FOUR_OF_A_KIND: 10,
        HandRank.FULL_HOUSE: 6,
        HandRank.FLUSH: 4,
        HandRank.STRAIGHT: 2
    },
    HandId.middle: {
        HandRank.STRAIGHT_FLUSH: {
            12: 50,
            11: 30,
            10: 30,
            9: 30,
            8: 30,
            7: 30,
            6: 30,
            5: 30,
            4: 30,
            3: 30,
        },
        HandRank.FOUR_OF_A_KIND: 20,
        HandRank.FULL_HOUSE: 12,
        HandRank.FLUSH: 8,
        HandRank.STRAIGHT: 4,
        HandRank.THREE_OF_A_KIND: 2
    },
    HandId.front: {
        HandRank.THREE_OF_A_KIND: {
            12: 22,
            11: 21,
            10: 20,
            9: 19,
            8: 18,
            7: 17,
            6: 16,
            5: 15,
            4: 14,
            3: 13,
            2: 12,
            1: 11,
            0: 10,
        },
        HandRank.ONE_PAIR: {
            12: 9,
            11: 8,
            10: 7,
            9: 6,
            8: 5,
            7: 4,
            6: 3,
            5: 2,
            4: 1,
        }
    }
}



class Hand():
    def __init__(self):
        # self.hands = {
        #     hand_id: SingleHand()
        #     for hand_id in HandId
        # }
        self.hands = {}
        self.hands[HandId.back] = SingleHand()
        self.hands[HandId.middle] = SingleHand()
        self.hands[HandId.front] = SingleHand()
        self.strength = {}

    def __repr__(self):
        return '\n'.join(
            repr(self.hands[hand_id])
            for hand_id in [
                    HandId.front,
                    HandId.middle,
                    HandId.back
            ]
        )

    def add_card(self, hand_id: HandId, card: Card):
        if (hand_id == HandId.front and len(self.hands[hand_id]) == 3) or \
           (hand_id in (HandId.middle, HandId.back) and
            len(self.hands[hand_id]) == 5):
            raise ValueError(f'Hand {hand_id} is full')

        self.hands[hand_id].add_card(card)

    def _check_hand_complete(self):
        for hand_id, hand in self.hands.items():
            if (hand_id == HandId.front and len(hand) != 3) or \
               (hand_id in (HandId.middle, HandId.back) and len(hand) != 5):
                raise ValueError(f'Hand {hand_id.name} is incomplete')

    def _compute_strength(self):
        self._check_hand_complete()

        for hand_id in HandId:
            self.strength[hand_id] = SingleHandStrength(self.hands[hand_id])

    def compute_bonus(self):
        for hand_id in HandId:
            print(hand_id)

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
        Card(Suit.s, '7'),
        Card(Suit.d, '3')
    ]),
    SingleHand([
        Card(Suit.c, 'K'),
        Card(Suit.s, 'K'),
        Card(Suit.h, 'K'),
        Card(Suit.c, '5'),
        Card(Suit.s, '5')
    ]),
    SingleHand([
        Card(Suit.d, 'A'),
        Card(Suit.d, 'T'),
        Card(Suit.d, '7'),
        Card(Suit.d, '8'),
        Card(Suit.d, '4')
    ]),
    SingleHand([
        Card(Suit.s, 'J'),
        Card(Suit.c, '7'),
        Card(Suit.c, 'T'),
        Card(Suit.h, '8'),
        Card(Suit.h, '9'),
    ]),
    SingleHand([
        Card(Suit.c, 'A'),
        Card(Suit.h, 'T'),
        Card(Suit.h, '8'),
        Card(Suit.c, '8'),
        Card(Suit.s, '8')
    ]),
    SingleHand([
        Card(Suit.d, '2'),
        Card(Suit.c, 'T'),
        Card(Suit.c, 'T'),
        Card(Suit.s, '2'),
        Card(Suit.c, '6')
    ]),
    SingleHand([
        Card(Suit.c, '2'),
        Card(Suit.c, '3'),
        Card(Suit.d, 'A'),
        Card(Suit.c, '4'),
        Card(Suit.c, '5')
    ]),
    SingleHand([
        Card(Suit.c, '2'),
        Card(Suit.c, '3'),
        Card(Suit.d, 'A'),
        Card(Suit.c, '4'),
        Card(Suit.s, '3')
    ]),
    SingleHand([
        Card(Suit.c, '2'),
        Card(Suit.c, '3'),
        Card(Suit.d, '4'),
        Card(Suit.c, '5'),
        Card(Suit.s, '7')
    ]),
    SingleHand([
        Card(Suit.c, '2'),
        Card(Suit.s, '2'),
        Card(Suit.d, '2'),
    ]),
    SingleHand([
        Card(Suit.c, '2'),
        Card(Suit.s, '2'),
        Card(Suit.d, '3'),
    ]),
    SingleHand([
        Card(Suit.c, 'Q'),
        Card(Suit.s, '7'),
        Card(Suit.d, 'A'),
    ]),
]

for hand in hands:
    strength = SingleHandStrength(hand)
    print(hand, strength.rank, strength.val)

def generate_random_single_hand(n_cards):
    cards = []

    while len(cards) < n_cards:
        suit = random.choice(list(Suit))
        height = random.choice('23456789TJQKA')
        card = Card(suit, height)
        if card not in cards:
            cards.append(card)

    return SingleHand(cards)

def generate_random_hand():
    hand = Hand()
    hand_ids = list(HandId)
    hand_ids_to_card_number = {
        HandId.back: 5,
        HandId.middle: 5,
        HandId.front: 3,
    }

    for i, hand_id in enumerate(hand_ids):
        while len(hand.hands[hand_id]) < hand_ids_to_card_number[hand_id]:
            suit = random.choice(list(Suit))
            height = random.choice('23456789TJQKA')
            card = Card(suit, height)
            for j in range(i + 1):
                if card in hand.hands[hand_ids[j]].cards:
                    break
            else:
                hand.add_card(hand_id, card)

    return hand

def test_hand_strength(n):
    hand_ids = [
        HandId.front,
        HandId.middle,
        HandId.back,
    ]
    for _ in range(n):
        print('###############')
        h = generate_random_hand()
        h._compute_strength()
        for hand_id in hand_ids:
            print(f'{hand_id.name:7} '
                  f'{repr(h.hands[hand_id]):15} '
                  f'{h.strength[hand_id]}')

# h = generate_random_hand()
test_hand_strength(5)
