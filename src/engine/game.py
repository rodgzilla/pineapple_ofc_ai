import pdb
from typing import List, Tuple, Union, Optional, cast, DefaultDict
from enum import Enum, IntEnum, auto
from functools import total_ordering
from collections import Counter, defaultdict
import copy
import random
from abc import ABC, abstractmethod
import itertools


class Suit(Enum):
    d = auto()
    c = auto()
    s = auto()
    h = auto()


class HandId(Enum):
    front  = auto()
    middle = auto()
    back   = auto()


class PlayerId(Enum):
    player_1 = auto()
    player_2 = auto()


class PlayId(Enum):
    front   = auto()
    middle  = auto()
    back    = auto()
    discard = auto()


play_id_to_hand_id = {
    PlayId.front  : HandId.front,
    PlayId.middle : HandId.middle,
    PlayId.back   : HandId.back
}


class HandRank(IntEnum):
    HIGH_CARD       = 0
    ONE_PAIR        = 1
    TWO_PAIRS       = 2
    THREE_OF_A_KIND = 3
    STRAIGHT        = 4
    FLUSH           = 5
    FULL_HOUSE      = 6
    FOUR_OF_A_KIND  = 7
    STRAIGHT_FLUSH  = 8


@total_ordering
class Card:
    def __init__(self, suit: Suit, height: str):
        height_to_int   = dict(zip('23456789TJQKA', range(13)))
        self.suit       = suit
        self.height     = height
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

class CardDeck():
    def __init__(self):
        self.cards = [
            Card(suit, height)
            for suit in Suit
            for height in '23456789TJQKA'
        ]
        random.shuffle(self.cards)

    def __repr__(self) -> str:
        return ' '.join(repr(card) for card in self.cards)

    def __len__(self) -> int:
        return len(self.cards)

    def reshuffle(self):
        random.shuffle(self.cards)

    def draw_card(self) -> Card:
        if len(self) == 0:
            raise ValueError('The deck is empty.')

        return self.cards.pop(0)

class SingleHand():
    def __init__(self, cards: Optional[List[Card]] = None):
        if cards is None:
            self.cards = []
        else:
            self.cards = cards

    def __len__(self) -> int:
        return len(self.cards)

    def __repr__(self) -> str:
        return ' '.join(str(card) for card in sorted(self.cards))

    def add_card(self, card: Card):
        self.cards.append(card)

@total_ordering
class SingleHandStrength():
    def __init__(self, hand: SingleHand):
        self.cards          = sorted(hand.cards)
        self.suit_counter   = Counter(card.suit for card in self.cards)
        self.height_counter = Counter(card.int_height for card in self.cards)
        self.rank, self.val = self._compute_strength()

    def __repr__(self) -> str:
        return f'{self.rank.name}, {self.val}'

    def __eq__(self, other: object):
        if not isinstance(other, SingleHandStrength):
            raise NotImplementedError

        return (self.rank, self.val) == (other.rank, other.val)

    def __lt__(self, other: object):
        if not isinstance(other, SingleHandStrength):
            raise NotImplementedError

        return (self.rank, self.val) < (other.rank, other.val)


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
        self.hands                = {}
        self.hands[HandId.back]   = SingleHand()
        self.hands[HandId.middle] = SingleHand()
        self.hands[HandId.front]  = SingleHand()
        self.strength             = {}
        self.bonus                = {}

    def __repr__(self) -> str:
        return '\n'.join(
            repr(self.hands[hand_id])
            for hand_id in [
                    HandId.front,
                    HandId.middle,
                    HandId.back
            ]
        )

    def __len__(self) -> int:
        return sum(len(hand) for hand in self.hands.values())

    def add_card(self, hand_id: HandId, card: Card):
        if (hand_id == HandId.front and len(self.hands[hand_id]) == 3) or \
           (hand_id in (HandId.middle, HandId.back) and
            len(self.hands[hand_id]) == 5):
            raise ValueError(f'Hand {hand_id} is full')

        self.hands[hand_id].add_card(card)

    def is_hand_complete(self) -> bool:
        for hand_id, hand in self.hands.items():
            if (hand_id == HandId.front and len(hand) != 3) or \
               (hand_id in (HandId.middle, HandId.back) and len(hand) != 5):
                return False

        return True

    def _compute_strength(self):
        if not self.is_hand_complete():
            raise ValueError('Hand is incomplete')

        for hand_id in HandId:
            self.strength[hand_id] = SingleHandStrength(self.hands[hand_id])

    def is_foul(self):
        if len(self.strength) == 0:
            self._compute_strength()

            return not (
                self.strength[HandId.front] <=
                self.strength[HandId.middle] <=
                self.strength[HandId.back]
            )

    def compute_bonus(self):
        if not self.is_hand_complete():
            raise ValueError('Hand is incomplete')

        if len(self.strength) == 0:
            self._compute_strength()

        for hand_id in HandId:
            hand_strength  = self.strength[hand_id]
            hand_bonus_map = bonus_map[hand_id].get(
                hand_strength.rank,
                0
            )
            if type(hand_bonus_map) == int:
                bonus_value = hand_bonus_map
            else:
                hand_val = hand_strength.val

                bonus_value = hand_bonus_map.get(
                    hand_val[0] if type(hand_val) == tuple else hand_val,
                    0
                )
            self.bonus[hand_id] = bonus_value

    def score_versus(self, other: 'Hand') -> Tuple[int, int]:
        self_foul  = self.is_foul()
        other_foul = other.is_foul()

        self.compute_bonus()
        other.compute_bonus()

        # If both players foul their hand, no one scores points
        if self_foul and other_foul:
            return 0, 0

        # Hand to hand battles
        battle_score_self  = 0
        battle_score_other = 0
        for hand_id in HandId:
            self_hand_strength = self.strength[hand_id]
            other_hand_strength = other.strength[hand_id]

            if self_foul or \
               (not other_foul and other_hand_strength > self_hand_strength):
                battle_score_other += 1
            elif other_foul or \
                 (not self_foul and self_hand_strength > other_hand_strength):
                battle_score_self += 1

        # Scooping happens when a player wins all the hand battles
        if battle_score_self == 3:
            battle_score_self += 3

        if battle_score_other == 3:
            battle_score_other += 3

        # If a player fouls his hand, he gets a three point
        # penalty. Otherwise, his score is the sum of its hand to hand
        # battle score and its royalties
        total_self_score  = 0
        total_other_score = 0
        if not self_foul:
            total_self_score = battle_score_self + sum(self.bonus.values())

        if not other_foul:
            total_other_score = battle_score_other + sum(other.bonus.values())

        return total_self_score, total_other_score

class Game():
    def __init__(self):
        self.deck            = CardDeck()
        self.p1_hand         = Hand()
        self.p2_hand         = Hand()
        self.hands           = {
            player_id: Hand()
            for player_id in PlayerId
        }
        self.discarded_cards = defaultdict(list)

    def __repr__(self) -> str:
        return (
        #     '#######\n'
        #     'Deck\n'
        #     f'{self.deck}\n'
            '#######\n'
            'Player 1 hand\n'
            f'{self.hands[PlayerId.player_1]}\n'
            '#######\n'
            'Player 2 hand\n'
            f'{self.hands[PlayerId.player_2]}\n'
            '#######\n'
            # 'Discarded cards\n'
            # f'Player 1: {self.discarded_cards[PlayerId.player_1]}\n'
            # f'Player 2: {self.discarded_cards[PlayerId.player_2]}'
        )

    def _draw_n_cards(self, n: int) -> Tuple[Card, ...]:
        return tuple([
            self.deck.draw_card()
            for _ in range(n)
        ])

    def draw_five_cards(self) -> Tuple[Card, ...]:
        return self._draw_n_cards(5)

    def draw_three_cards(self) -> Tuple[Card, ...]:
        return self._draw_n_cards(3)

    def is_valid_play(
            self,
            player_id : PlayerId,
            cards     : List[Card],
            play_ids  : Tuple[PlayId, ...]
    ) -> bool:
        if len(cards) != len(play_ids):
            return False

        hand = self.hands[player_id]
        if hand.is_hand_complete():
            return False

        play_counter = Counter(play_ids)

        if len(cards) == 5:
            # Discarding in the initial 5 cards is not allowed
            if play_counter[PlayId.discard] != 0:
                return False

            # The front hand is limited to 3 cards
            if play_counter[PlayId.front] > 3:
                return False
        elif len(cards) == 3:
            # pdb.set_trace()
            # For each 3 cards draws, we have a discard exactly one
            if play_counter[PlayId.discard] != 1:
                return False

            front_hand_size = len(hand.hands[HandId.front])
            if front_hand_size + play_counter[PlayId.front] > 3:
                return False

            middle_hand_size = len(hand.hands[HandId.middle])
            if middle_hand_size + play_counter[PlayId.middle] > 5:
                return False

            back_hand_size = len(hand.hands[HandId.back])
            if back_hand_size + play_counter[PlayId.back] > 5:
                return False
        else:
            return False

        return True

    def play(
            self,
            player_id : PlayerId,
            cards     : List[Card],
            play_ids  : Tuple[PlayId, ...]
    ):
        if not self.is_valid_play(player_id, cards, play_ids):
            raise ValueError('Invalid move')

        hand = self.hands[player_id]
        for card, position in zip(cards, play_ids):
            if position == PlayId.discard:
                self.discarded_cards[player_id].append(card)
            else:
                hand.hands[play_id_to_hand_id[position]].add_card(card)


class Player(ABC):
    @abstractmethod
    def get_play(
            self,
            game      : Game,
            player_id : PlayerId,
            cards     : List[Card],
            initial   : bool
    ) -> Tuple[PlayId, ...]:
        raise NotImplementedError

class HumanPlayer(Player):
    def __init__(self):
        self.char_to_play_id = {
            'B': PlayId.back,
            'M': PlayId.middle,
            'F': PlayId.front,
            'D': PlayId.discard,
        }

    def _convert_str_to_play_ids(self, s: str) -> Tuple[PlayId, ...]:
        return tuple([
            self.char_to_play_id[c]
            for c in s
        ])

    def get_play(
            self,
            game      : Game,
            player_id : PlayerId,
            cards     : List[Card],
            initial   : bool
    ) -> Tuple[PlayId, ...]:
        hand     = game.hands[player_id]
        play_ids = cast(Tuple[PlayId, ...], (PlayId.discard,))

        while not game.is_valid_play(player_id, cards, play_ids):
            if len(hand) != 0:
                print(hand)
            print('Your cards:', cards)
            play_str = input(
                'Your play (BMF): '
                if initial else
                'Your play (BMFD): '
            ).upper()
            if any(play_char not in 'BMFD' for play_char in play_str):
                print('All moves must be in BMFD')
                continue
            play_ids = self._convert_str_to_play_ids(play_str)

        return play_ids


def generate_initial_plays() -> List[Tuple[PlayId, ...]]:
    return [
        play
        for play in itertools.product(
                PlayId,
                repeat = 5
        )
        if play.count(PlayId.discard) == 0 and
        play.count(PlayId.front) <= 3
    ]

def generate_non_initial_plays() -> List[Tuple[PlayId, ...]]:
    return [
        play
        for play in itertools.product(
                PlayId,
                repeat = 3
        )
        if play.count(PlayId.discard) == 1
    ]


class RandomPlayer(Player):
    def __init__(self):
        self.possible_initial_plays     = generate_initial_plays()
        self.possible_non_initial_plays = generate_non_initial_plays()

    def get_play(
            self,
            game      : Game,
            player_id : PlayerId,
            cards     : List[Card],
            initial   : bool
    ) -> Tuple[PlayId, ...]:
        # we get the list of possible plays corresponding to the situation
        plays = (
            self.possible_initial_plays
            if initial else
            self.possible_non_initial_plays
        )
        # We filter out plays that are not valid
        plays = [
            play
            for play in plays
            if game.is_valid_play(
                    player_id,
                    cards,
                    play
            )
        ]

        # We return a randomly chosen play
        return random.choice(plays)


class MonteCarloPlayer(Player):
    def __init__(self, player_id: PlayerId, n_run: int):
        self.n_run                      = n_run
        self.selecting_function         = max if player_id == PlayerId.player_1 else min
        self.possible_initial_plays     = generate_initial_plays()
        self.possible_non_initial_plays = generate_non_initial_plays()

    def _select_play_based_on_outcomes(
            self,
            play_to_outcomes: DefaultDict[
                Tuple[PlayId, ...],
                List[Tuple[int, int]]
            ]
    ) -> Tuple[PlayId, ...]:
        play_to_mean_diff = {
            play: (
                sum(
                    score_1 - score_2
                    for score_1, score_2 in outcomes
                ) / len(outcomes)
            )
            for play, outcomes in play_to_outcomes.items ()
        }

        res = self.selecting_function(
            play_to_mean_diff.items(),
            key = lambda x: x[1]
        )
        return res[0]

    def get_play(
            self,
            game      : Game,
            player_id : PlayerId,
            cards     : List[Card],
            initial   : bool
    ) -> Tuple[PlayId, ...]:
        print('Finding solution for:', cards)
        play_to_outcomes: DefaultDict[
            Tuple[PlayId, ...],
            List[Tuple[int, int]]
        ] = defaultdict(list)
        plays            = (
            self.possible_initial_plays
            if initial else
            self.possible_non_initial_plays
        )
        # We filter out plays that are not valid
        plays            = [
            play
            for play in plays
            if game.is_valid_play(
                    player_id,
                    cards,
                    play
            )
        ]

        for _ in range(self.n_run):
            current_game = copy.deepcopy(game)
            play_to_explore = random.choice(plays)
            current_game.play(
                player_id = player_id,
                cards     = cards,
                play_ids  = play_to_explore
            )
            current_game.deck.reshuffle()
            random_game_loop = GameLoop(
                player_1 = RandomPlayer(),
                player_2 = RandomPlayer(),
                game     = current_game,
                verbose  = False
            )
            outcome = random_game_loop.run()
            play_to_outcomes[play_to_explore].append(outcome)

        selected_play = self._select_play_based_on_outcomes(play_to_outcomes)

        return selected_play


class GameLoop():
    def __init__(
            self,
            player_1: Player,
            player_2: Player,
            game: Optional[Game] = None,
            verbose: bool = True,
    ):
        self.players         = {
            PlayerId.player_1: player_1,
            PlayerId.player_2: player_2
        }
        if game is None:
            self.game = Game()
        else:
            self.game = game
        self.verbose         = verbose
        self.current_player  = PlayerId.player_1

    def _compute_and_print_result(self):
        hand_ids           = [
            HandId.front,
            HandId.middle,
            HandId.back,
        ]
        h1                 = self.game.hands[PlayerId.player_1]
        h2                 = self.game.hands[PlayerId.player_2]

        score_h1, score_h2 = h1.score_versus(h2)
        if self.verbose:
            print()
            for hand_id in hand_ids:
                print(
                    f'{repr(h1.hands[hand_id]):15} '
                    f'{h1.strength[hand_id].rank.name:15} '
                    f'{h1.bonus[hand_id]} | '
                    f'{repr(h2.hands[hand_id]):15} '
                    f'{h2.strength[hand_id].rank.name:15} '
                    f'{h2.bonus[hand_id]}'
                )
            print('Scores:', score_h1, score_h2)
            print('Difference:', score_h1 - score_h2)

        return score_h1, score_h2

    def run(self):
        if len(self.game.hands[PlayerId.player_1]) == 0:
            if self.verbose:
                print('Player 1 to play')
            self.current_player = PlayerId.player_1
            initial_hand_p1     = self.game.draw_five_cards()
            play_ids            = self.players[PlayerId.player_1].get_play(
                game      = self.game,
                player_id = PlayerId.player_1,
                cards     = initial_hand_p1,
                initial   = True
            )
            self.game.play(PlayerId.player_1, initial_hand_p1, play_ids)
            if self.verbose:
                print(self.game)

        if len(self.game.hands[PlayerId.player_2]) == 0:
            if self.verbose:
                print('Player 2 to play')
            self.current_player = PlayerId.player_2
            initial_hand_p2     = self.game.draw_five_cards()
            play_ids            = self.players[PlayerId.player_2].get_play(
                game      = self.game,
                player_id = PlayerId.player_2,
                cards     = initial_hand_p2,
                initial   = True
            )
            self.game.play(PlayerId.player_2, initial_hand_p2, play_ids)
            if self.verbose:
                print(self.game)

        while any(
                not hand.is_hand_complete()
                for hand in self.game.hands.values()
        ):
            if self.current_player == PlayerId.player_1:
                self.current_player = PlayerId.player_2
            else:
                self.current_player = PlayerId.player_1
            if self.verbose:
                print(self.current_player.name, 'turn')
            hand     = self.game.draw_three_cards()
            play_ids = self.players[self.current_player].get_play(
                game      = self.game,
                player_id = self.current_player,
                cards     = hand,
                initial   = False
            )
            self.game.play(self.current_player, hand, play_ids)
            if self.verbose:
                print(self.game)

        return self._compute_and_print_result()


# def generate_random_single_hand(n_cards):
#     cards = []

#     while len(cards) < n_cards:
#         suit = random.choice(list(Suit))
#         height = random.choice('23456789TJQKA')
#         card = Card(suit, height)
#         if card not in cards:
#             cards.append(card)

#     return SingleHand(cards)

# def generate_random_hand():
#     hand = Hand()
#     hand_ids = list(HandId)
#     hand_ids_to_card_number = {
#         HandId.back: 5,
#         HandId.middle: 5,
#         HandId.front: 3,
#     }

#     for i, hand_id in enumerate(hand_ids):
#         while len(hand.hands[hand_id]) < hand_ids_to_card_number[hand_id]:
#             suit = random.choice(list(Suit))
#             height = random.choice('23456789TJQKA')
#             card = Card(suit, height)
#             for j in range(i + 1):
#                 if card in hand.hands[hand_ids[j]].cards:
#                     break
#             else:
#                 hand.add_card(hand_id, card)

#     return hand

# def test_hand_strength(n):
#     hand_ids = [
#         HandId.front,
#         HandId.middle,
#         HandId.back,
#     ]
#     for _ in range(n):
#         h = generate_random_hand()
#         h.compute_bonus()
#         # if h.bonus[HandId.back] == 0 and h.bonus[HandId.middle] == 0:
#         #     continue
#         print('###############')
#         for hand_id in hand_ids:
#             print(f'{hand_id.name:7} '
#                   f'{repr(h.hands[hand_id]):15} '
#                   f'{repr(h.strength[hand_id]):30} '
#                   f'{h.bonus[hand_id]}')
#         print('Is foul?', h.is_foul())
#         h.compute_bonus()

# def generate_non_fouling_hand():
#     while True:
#         h = generate_random_hand()
#         if not h.is_foul():
#             return h


# player_1 = HumanPlayer()
# player_2 = HumanPlayer()
# loop = GameLoop(player_1, player_2)
# mc_player = MonteCarloPlayer(20)
# loop = GameLoop(
#     MonteCarloPlayer(100),
#     HumanPlayer()
# )

loop = GameLoop(
    MonteCarloPlayer(PlayerId.player_1, 10000),
    MonteCarloPlayer(PlayerId.player_2, 10000),
)
