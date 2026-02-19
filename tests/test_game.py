"""
Comprehensive test suite for the Pineapple OFC poker engine.
"""

import pytest
import random
from collections import Counter

from src.engine.game import (
    Suit, HandId, PlayerId, PlayId, HandRank,
    Card, CardDeck, SingleHand, SingleHandStrength,
    Hand, Game, bonus_map, play_id_to_hand_id,
    generate_initial_plays, generate_non_initial_plays,
    RandomPlayer, GameLoop, FullGame,
)


# ============================================================
# Helper utilities
# ============================================================

def c(spec: str) -> Card:
    """Build a Card from a 2-char spec like 'As', 'Td', '2h'."""
    suit_map = {'d': Suit.d, 'c': Suit.c, 's': Suit.s, 'h': Suit.h}
    height, suit_char = spec[:-1], spec[-1]
    return Card(suit_map[suit_char], height)


def single_hand(*specs: str) -> SingleHand:
    """Build a SingleHand from card specs."""
    return SingleHand([c(s) for s in specs])


def strength(*specs: str) -> SingleHandStrength:
    """Build a SingleHandStrength from card specs."""
    return SingleHandStrength(single_hand(*specs))


def make_hand(front: list, middle: list, back: list) -> Hand:
    """Build a complete Hand from three lists of card specs."""
    hand = Hand()
    for spec in front:
        hand.add_card(HandId.front, c(spec))
    for spec in middle:
        hand.add_card(HandId.middle, c(spec))
    for spec in back:
        hand.add_card(HandId.back, c(spec))
    return hand


# ============================================================
# Card
# ============================================================

class TestCard:
    def test_int_height_mapping(self):
        for i, h in enumerate('23456789TJQKA'):
            assert Card(Suit.s, h).int_height == i

    def test_repr(self):
        assert repr(Card(Suit.h, 'K')) == 'Kh'
        assert repr(Card(Suit.d, '2')) == '2d'
        assert repr(Card(Suit.c, 'A')) == 'Ac'

    def test_equality_same_card(self):
        assert Card(Suit.s, 'A') == Card(Suit.s, 'A')

    def test_equality_different_suit(self):
        assert Card(Suit.s, 'A') != Card(Suit.h, 'A')

    def test_equality_different_height(self):
        assert Card(Suit.s, 'A') != Card(Suit.s, 'K')

    def test_equality_raises_for_non_card(self):
        with pytest.raises(NotImplementedError):
            Card(Suit.s, 'A') == 'not a card'

    def test_lt_lower_height_less_than_higher(self):
        assert Card(Suit.s, '2') < Card(Suit.s, 'A')

    def test_lt_same_height_suit_tiebreak(self):
        # auto() order: d=1, c=2, s=3, h=4  ->  d < c < s < h
        assert Card(Suit.d, 'A') < Card(Suit.h, 'A')

    def test_lt_raises_for_non_card(self):
        with pytest.raises(NotImplementedError):
            Card(Suit.s, 'A') < 'not a card'

    def test_gt_via_total_ordering(self):
        assert Card(Suit.s, 'A') > Card(Suit.s, '2')

    def test_sorted_list(self):
        cards = [c('As'), c('2s'), c('Ks')]
        assert [card.height for card in sorted(cards)] == ['2', 'K', 'A']

    def test_all_heights_distinct_int_heights(self):
        heights = [Card(Suit.s, h).int_height for h in '23456789TJQKA']
        assert heights == list(range(13))


# ============================================================
# CardDeck
# ============================================================

class TestCardDeck:
    def test_deck_has_52_cards(self):
        deck = CardDeck()
        assert len(deck) == 52

    def test_deck_has_13_per_suit(self):
        deck = CardDeck()
        suit_counts = Counter(card.suit for card in deck.cards)
        for suit in Suit:
            assert suit_counts[suit] == 13

    def test_deck_has_4_per_height(self):
        deck = CardDeck()
        height_counts = Counter(card.height for card in deck.cards)
        for h in '23456789TJQKA':
            assert height_counts[h] == 4

    def test_deck_all_cards_unique(self):
        deck = CardDeck()
        pairs = [(card.suit, card.height) for card in deck.cards]
        assert len(pairs) == len(set(pairs))

    def test_draw_card_returns_card(self):
        deck = CardDeck()
        drawn = deck.draw_card()
        assert isinstance(drawn, Card)

    def test_draw_card_reduces_deck_size(self):
        deck = CardDeck()
        deck.draw_card()
        assert len(deck) == 51

    def test_draw_all_52_cards(self):
        deck = CardDeck()
        drawn = [deck.draw_card() for _ in range(52)]
        assert len(drawn) == 52
        assert len(deck) == 0

    def test_draw_from_empty_deck_raises(self):
        deck = CardDeck()
        for _ in range(52):
            deck.draw_card()
        with pytest.raises(ValueError):
            deck.draw_card()

    def test_drawn_cards_not_in_deck(self):
        deck = CardDeck()
        drawn = deck.draw_card()
        assert drawn not in deck.cards

    def test_repr_is_string(self):
        deck = CardDeck()
        assert isinstance(repr(deck), str)

    def test_reshuffle_keeps_52_cards(self):
        deck = CardDeck()
        deck.reshuffle()
        assert len(deck) == 52


# ============================================================
# SingleHand
# ============================================================

class TestSingleHand:
    def test_empty_creation(self):
        hand = SingleHand()
        assert len(hand) == 0

    def test_creation_with_cards(self):
        hand = SingleHand([c('As'), c('Kh')])
        assert len(hand) == 2

    def test_add_card_increases_length(self):
        hand = SingleHand()
        hand.add_card(c('As'))
        assert len(hand) == 1

    def test_add_multiple_cards(self):
        hand = SingleHand()
        for spec in ['As', 'Kh', 'Qd']:
            hand.add_card(c(spec))
        assert len(hand) == 3

    def test_repr_contains_card_strings(self):
        hand = single_hand('As', 'Kh')
        r = repr(hand)
        assert 'As' in r
        assert 'Kh' in r

    def test_repr_cards_sorted(self):
        # '2h' int_height=0 should come before 'As' int_height=12
        hand = single_hand('As', '2h')
        r = repr(hand)
        assert r.index('2h') < r.index('As')


# ============================================================
# SingleHandStrength — 5-card hands
# ============================================================

class TestSingleHandStrength5Card:

    # --- Straight Flush ---
    def test_royal_flush(self):
        s = strength('As', 'Ks', 'Qs', 'Js', 'Ts')
        assert s.rank == HandRank.STRAIGHT_FLUSH
        assert s.val == 12  # Ace int_height

    def test_straight_flush_nine_high(self):
        s = strength('9s', '8s', '7s', '6s', '5s')
        assert s.rank == HandRank.STRAIGHT_FLUSH
        assert s.val == 7  # 9 int_height

    def test_straight_flush_ace_to_five(self):
        s = strength('As', '2s', '3s', '4s', '5s')
        assert s.rank == HandRank.STRAIGHT_FLUSH
        assert s.val == 3  # 5 int_height (wheel top)

    def test_straight_flush_king_high(self):
        s = strength('Ks', 'Qs', 'Js', 'Ts', '9s')
        assert s.rank == HandRank.STRAIGHT_FLUSH
        assert s.val == 11  # King int_height

    # --- Four of a Kind ---
    def test_four_aces(self):
        s = strength('As', 'Ah', 'Ad', 'Ac', '2s')
        assert s.rank == HandRank.FOUR_OF_A_KIND

    def test_four_twos(self):
        s = strength('2s', '2h', '2d', '2c', 'As')
        assert s.rank == HandRank.FOUR_OF_A_KIND

    def test_four_kings(self):
        s = strength('Ks', 'Kh', 'Kd', 'Kc', 'As')
        assert s.rank == HandRank.FOUR_OF_A_KIND

    # --- Full House ---
    def test_full_house_aces_over_kings(self):
        s = strength('As', 'Ah', 'Ad', 'Ks', 'Kh')
        assert s.rank == HandRank.FULL_HOUSE
        assert s.val == (12, 11)  # (trips_height, pair_height)

    def test_full_house_twos_over_threes(self):
        s = strength('2s', '2h', '2d', '3s', '3h')
        assert s.rank == HandRank.FULL_HOUSE
        assert s.val == (0, 1)

    def test_full_house_kings_over_aces(self):
        # Pair of aces, trips of kings
        s = strength('Ks', 'Kh', 'Kd', 'As', 'Ah')
        assert s.rank == HandRank.FULL_HOUSE
        assert s.val == (11, 12)

    # --- Flush ---
    def test_flush_ace_high(self):
        s = strength('As', '8s', '6s', '4s', '2s')
        assert s.rank == HandRank.FLUSH

    def test_flush_not_a_straight(self):
        s = strength('2s', '3s', '4s', '5s', '7s')
        assert s.rank == HandRank.FLUSH

    def test_flush_val_descending(self):
        s = strength('As', 'Ks', 'Qs', 'Js', '9s')
        assert s.rank == HandRank.FLUSH
        vals = s.val
        assert vals[0] > vals[1] > vals[2] > vals[3] > vals[4]

    # --- Straight ---
    def test_straight_ace_high(self):
        s = strength('As', 'Kh', 'Qd', 'Jc', 'Ts')
        assert s.rank == HandRank.STRAIGHT
        assert s.val == 12

    def test_straight_wheel(self):
        s = strength('As', '2h', '3d', '4c', '5s')
        assert s.rank == HandRank.STRAIGHT
        assert s.val == 3  # 5 high

    def test_straight_nine_high(self):
        s = strength('9s', '8h', '7d', '6c', '5s')
        assert s.rank == HandRank.STRAIGHT
        assert s.val == 7

    def test_not_straight_with_pair(self):
        s = strength('As', 'Ah', 'Kd', 'Qc', 'Js')
        assert s.rank != HandRank.STRAIGHT

    # --- Three of a Kind ---
    def test_three_aces_with_kickers(self):
        s = strength('As', 'Ah', 'Ad', '2s', '3h')
        assert s.rank == HandRank.THREE_OF_A_KIND

    def test_three_twos(self):
        s = strength('2s', '2h', '2d', 'As', 'Kh')
        assert s.rank == HandRank.THREE_OF_A_KIND

    # --- Two Pairs ---
    def test_two_pairs_aces_and_kings(self):
        s = strength('As', 'Ah', 'Ks', 'Kh', '2s')
        assert s.rank == HandRank.TWO_PAIRS

    def test_two_pairs_higher_pair_first(self):
        s = strength('Ks', 'Kh', '2s', '2h', 'As')
        assert s.rank == HandRank.TWO_PAIRS
        assert s.val[0] >= s.val[1]

    def test_two_pairs_kicker_in_val(self):
        s = strength('As', 'Ah', 'Ks', 'Kh', '2s')
        assert s.rank == HandRank.TWO_PAIRS
        # val = (high_pair, low_pair, kicker)
        assert len(s.val) == 3

    # --- One Pair ---
    def test_one_pair_aces(self):
        s = strength('As', 'Ah', '2s', '3h', '4d')
        assert s.rank == HandRank.ONE_PAIR

    def test_one_pair_twos(self):
        s = strength('2s', '2h', 'As', 'Kh', 'Qd')
        assert s.rank == HandRank.ONE_PAIR

    def test_one_pair_val_pair_height_first(self):
        s = strength('As', 'Ah', 'Ks', 'Qh', 'Jd')
        assert s.rank == HandRank.ONE_PAIR
        assert s.val[0] == 12  # Ace int_height

    # --- High Card ---
    def test_high_card_ace_high(self):
        s = strength('As', 'Ks', 'Qh', 'Jd', '9c')
        assert s.rank == HandRank.HIGH_CARD

    def test_high_card_val_descending(self):
        s = strength('As', 'Ks', 'Qh', 'Jd', '9c')
        vals = s.val
        assert vals[0] > vals[1] > vals[2] > vals[3] > vals[4]

    def test_high_card_no_flush_no_straight(self):
        s = strength('2s', 'Kh', 'Qd', 'Jc', '9h')
        assert s.rank == HandRank.HIGH_CARD


# ============================================================
# SingleHandStrength — 3-card hands (front row)
# ============================================================

class TestSingleHandStrength3Card:
    def test_three_of_a_kind(self):
        s = strength('As', 'Ah', 'Ad')
        assert s.rank == HandRank.THREE_OF_A_KIND

    def test_three_of_a_kind_twos(self):
        s = strength('2s', '2h', '2d')
        assert s.rank == HandRank.THREE_OF_A_KIND

    def test_one_pair(self):
        s = strength('As', 'Ah', 'Ks')
        assert s.rank == HandRank.ONE_PAIR

    def test_one_pair_val_pair_first(self):
        s = strength('As', 'Ah', 'Ks')
        assert s.val[0] == 12  # Ace

    def test_high_card(self):
        s = strength('As', 'Kh', 'Qs')
        assert s.rank == HandRank.HIGH_CARD

    def test_high_card_val_descending(self):
        s = strength('As', 'Kh', 'Qs')
        assert s.val[0] > s.val[1] > s.val[2]


# ============================================================
# SingleHandStrength — comparisons
# ============================================================

class TestSingleHandStrengthComparisons:
    def test_straight_flush_beats_four_of_a_kind(self):
        assert strength('As', 'Ks', 'Qs', 'Js', 'Ts') > strength('As', 'Ah', 'Ad', 'Ac', '2s')

    def test_four_of_a_kind_beats_full_house(self):
        assert strength('As', 'Ah', 'Ad', 'Ac', '2s') > strength('As', 'Ah', 'Ad', 'Ks', 'Kh')

    def test_full_house_beats_flush(self):
        assert strength('As', 'Ah', 'Ad', 'Ks', 'Kh') > strength('2s', '4s', '6s', '8s', 'Ts')

    def test_flush_beats_straight(self):
        assert strength('2s', '4s', '6s', '8s', 'Ts') > strength('As', 'Kh', 'Qd', 'Jc', 'Ts')

    def test_straight_beats_three_of_a_kind(self):
        assert strength('9s', '8h', '7d', '6c', '5s') > strength('As', 'Ah', 'Ad', '2s', '3h')

    def test_three_of_a_kind_beats_two_pairs(self):
        assert strength('As', 'Ah', 'Ad', '2s', '3h') > strength('As', 'Ah', 'Ks', 'Kh', '2s')

    def test_two_pairs_beats_one_pair(self):
        assert strength('As', 'Ah', 'Ks', 'Kh', '2s') > strength('As', 'Ah', '2s', '3h', '4d')

    def test_one_pair_beats_high_card(self):
        assert strength('As', 'Ah', '2s', '3h', '4d') > strength('As', 'Ks', 'Qh', 'Jd', '9c')

    def test_equality_same_hand_different_suits(self):
        s1 = strength('As', 'Ks', 'Qh', 'Jd', '9c')
        s2 = strength('Ah', 'Kh', 'Qd', 'Jc', '9s')
        assert s1 == s2

    def test_higher_straight_beats_lower(self):
        assert strength('As', 'Kh', 'Qd', 'Jc', 'Ts') > strength('9s', '8h', '7d', '6c', '5s')

    def test_higher_pair_beats_lower_pair(self):
        assert strength('As', 'Ah', '2s', '3h', '4d') > strength('2s', '2h', 'As', 'Kh', 'Qd')

    def test_same_pair_higher_kicker_wins(self):
        s_ace_kicker = strength('Ks', 'Kh', 'As', '3d', '2c')
        s_queen_kicker = strength('Ks', 'Kh', 'Qs', '3d', '2c')
        assert s_ace_kicker > s_queen_kicker

    def test_higher_full_house_trips_wins(self):
        fh_aces = strength('As', 'Ah', 'Ad', 'Ks', 'Kh')
        fh_kings = strength('Ks', 'Kh', 'Kd', 'As', 'Ah')
        assert fh_aces > fh_kings

    def test_higher_four_of_a_kind_wins(self):
        foak_aces = strength('As', 'Ah', 'Ad', 'Ac', '2s')
        foak_kings = strength('Ks', 'Kh', 'Kd', 'Kc', 'As')
        assert foak_aces > foak_kings

    def test_not_equal_different_hands(self):
        assert strength('As', 'Ks', 'Qh', 'Jd', '9c') != strength('As', 'Ks', 'Qh', 'Jd', '8c')

    def test_repr_is_string(self):
        s = strength('As', 'Ks', 'Qh', 'Jd', '9c')
        assert isinstance(repr(s), str)


# ============================================================
# Hand — structure and completeness
# ============================================================

class TestHand:
    def test_creation_has_three_rows(self):
        hand = Hand()
        assert HandId.front in hand.hands
        assert HandId.middle in hand.hands
        assert HandId.back in hand.hands

    def test_empty_hand_length_zero(self):
        assert len(Hand()) == 0

    def test_add_to_front(self):
        hand = Hand()
        hand.add_card(HandId.front, c('As'))
        assert len(hand.hands[HandId.front]) == 1

    def test_add_to_middle(self):
        hand = Hand()
        hand.add_card(HandId.middle, c('As'))
        assert len(hand.hands[HandId.middle]) == 1

    def test_add_to_back(self):
        hand = Hand()
        hand.add_card(HandId.back, c('As'))
        assert len(hand.hands[HandId.back]) == 1

    def test_front_overflow_raises(self):
        hand = Hand()
        for h in ['A', 'K', 'Q']:
            hand.add_card(HandId.front, Card(Suit.s, h))
        with pytest.raises(ValueError):
            hand.add_card(HandId.front, Card(Suit.s, 'J'))

    def test_middle_overflow_raises(self):
        hand = Hand()
        for h in ['A', 'K', 'Q', 'J', 'T']:
            hand.add_card(HandId.middle, Card(Suit.s, h))
        with pytest.raises(ValueError):
            hand.add_card(HandId.middle, Card(Suit.s, '9'))

    def test_back_overflow_raises(self):
        hand = Hand()
        for h in ['A', 'K', 'Q', 'J', 'T']:
            hand.add_card(HandId.back, Card(Suit.s, h))
        with pytest.raises(ValueError):
            hand.add_card(HandId.back, Card(Suit.s, '9'))

    def test_is_hand_complete_false_empty(self):
        assert not Hand().is_hand_complete()

    def test_is_hand_complete_false_partial(self):
        hand = Hand()
        hand.add_card(HandId.front, c('As'))
        assert not hand.is_hand_complete()

    def test_is_hand_complete_true(self):
        hand = make_hand(
            ['As', 'Kh', 'Qd'],
            ['Jc', 'Ts', '9h', '8d', '7c'],
            ['6s', '5h', '4d', '3c', '2s'],
        )
        assert hand.is_hand_complete()

    def test_full_hand_has_13_cards(self):
        hand = make_hand(
            ['As', 'Kh', 'Qd'],
            ['Jc', 'Ts', '9h', '8d', '7c'],
            ['6s', '5h', '4d', '3c', '2s'],
        )
        assert len(hand) == 13

    def test_repr_is_string(self):
        hand = make_hand(
            ['As', 'Kh', 'Qd'],
            ['Jc', 'Ts', '9h', '8d', '7c'],
            ['6s', '5h', '4d', '3c', '2s'],
        )
        assert isinstance(repr(hand), str)

    def test_compute_strength_on_incomplete_raises(self):
        hand = Hand()
        with pytest.raises(ValueError):
            hand._compute_strength()


# ============================================================
# Hand — foul detection
# ============================================================

class TestHandFoul:
    def test_valid_hand_not_foul(self):
        # front: pair aces, middle: straight, back: flush
        hand = make_hand(
            ['As', 'Ah', '2d'],
            ['3c', '4s', '5h', '6d', '7c'],
            ['8s', 'Ts', 'Js', 'Qs', 'Ks'],
        )
        assert not hand.is_foul()

    def test_valid_hand_all_high_cards_not_foul(self):
        # front HIGH_CARD <= middle HIGH_CARD (higher) <= back HIGH_CARD (higher still)
        hand = make_hand(
            ['2s', '3h', '4d'],
            ['5c', '6h', '7d', '8c', '9s'],
            ['Th', 'Jd', 'Qc', 'Ks', 'Ah'],
        )
        assert not hand.is_foul()

    def test_foul_front_stronger_than_middle(self):
        # front: trips aces (THREE_OF_A_KIND), middle: high card
        hand = make_hand(
            ['As', 'Ah', 'Ad'],
            ['2c', '4s', '6h', '8d', 'Tc'],
            ['3s', '5h', '7d', '9c', 'Jh'],
        )
        assert hand.is_foul()

    def test_foul_middle_stronger_than_back(self):
        # middle: flush, back: high card
        hand = make_hand(
            ['2s', '3h', '4d'],
            ['5s', '7s', '9s', 'Js', 'Qs'],
            ['2h', '4c', '6d', '8c', 'Td'],
        )
        assert hand.is_foul()

    def test_foul_front_pair_stronger_than_middle_pair(self):
        # front: pair aces, middle: pair 2s — both ONE_PAIR but front val > middle val
        hand = make_hand(
            ['As', 'Ah', '2d'],
            ['2c', '2s', '3h', '4d', '5c'],
            ['6s', '7h', '8d', '9c', 'Ts'],
        )
        assert hand.is_foul()

    def test_valid_full_house_back_flush_middle(self):
        # middle: flush, back: full house — OK
        hand = make_hand(
            ['2s', '3h', '4d'],
            ['5s', '7s', '9s', 'Js', 'Qs'],
            ['As', 'Ah', 'Ad', 'Ks', 'Kh'],
        )
        assert not hand.is_foul()


# ============================================================
# Hand — bonus computation
# ============================================================

class TestHandBonus:

    # Back row bonuses
    def test_back_royal_flush_bonus(self):
        hand = make_hand(
            ['2s', '3h', '4d'],
            ['5h', '6c', '7d', '8c', '9d'],
            ['As', 'Ks', 'Qs', 'Js', 'Ts'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.back] == 25

    def test_back_straight_flush_non_royal(self):
        hand = make_hand(
            ['2s', '3h', '4d'],
            ['5h', '6c', '7d', '8c', '9d'],
            ['Ks', 'Qs', 'Js', 'Ts', '9s'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.back] == 15

    def test_back_four_of_a_kind_bonus(self):
        hand = make_hand(
            ['2s', '3h', '4d'],
            ['5h', '6c', '7d', '8c', '9d'],
            ['As', 'Ah', 'Ad', 'Ac', 'Ks'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.back] == 10

    def test_back_full_house_bonus(self):
        hand = make_hand(
            ['2s', '3h', '4d'],
            ['5h', '6c', '7d', '8c', '9d'],
            ['As', 'Ah', 'Ad', 'Ks', 'Kh'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.back] == 6

    def test_back_flush_bonus(self):
        hand = make_hand(
            ['2s', '3h', '4d'],
            ['5h', '6c', '7d', '8c', '9d'],
            ['2h', '4h', '6h', '8h', 'Th'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.back] == 4

    def test_back_straight_bonus(self):
        hand = make_hand(
            ['2s', '3h', '4d'],
            ['5h', '6c', '7d', '8c', '9d'],
            ['As', 'Kh', 'Qd', 'Jc', 'Ts'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.back] == 2

    def test_back_no_bonus_for_three_of_a_kind(self):
        hand = make_hand(
            ['2s', '3h', '4d'],
            ['5h', '6c', '7d', '8c', '9d'],
            ['As', 'Ah', 'Ad', '2c', '3d'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.back] == 0

    def test_back_no_bonus_for_high_card(self):
        hand = make_hand(
            ['2s', '3h', '4d'],
            ['5h', '6c', '7d', '8c', '9d'],
            ['As', 'Kh', 'Qd', 'Jc', '9s'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.back] == 0

    # Middle row bonuses
    def test_middle_royal_flush_bonus(self):
        hand = make_hand(
            ['2s', '3h', '4d'],
            ['As', 'Ks', 'Qs', 'Js', 'Ts'],
            ['5h', '6c', '7d', '8c', '9d'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.middle] == 50

    def test_middle_straight_flush_non_royal(self):
        hand = make_hand(
            ['2s', '3h', '4d'],
            ['Ks', 'Qs', 'Js', 'Ts', '9s'],
            ['5h', '6c', '7d', '8c', '9d'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.middle] == 30

    def test_middle_four_of_a_kind_bonus(self):
        hand = make_hand(
            ['2s', '3h', '4d'],
            ['As', 'Ah', 'Ad', 'Ac', '5s'],
            ['6h', '7c', '8d', '9c', 'Td'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.middle] == 20

    def test_middle_full_house_bonus(self):
        hand = make_hand(
            ['2s', '3h', '4d'],
            ['As', 'Ah', 'Ad', 'Ks', 'Kh'],
            ['5h', '6c', '7d', '8c', '9d'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.middle] == 12

    def test_middle_flush_bonus(self):
        hand = make_hand(
            ['2s', '3h', '4d'],
            ['2h', '4h', '6h', '8h', 'Th'],
            ['As', 'Ah', 'Ad', 'Ks', 'Kh'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.middle] == 8

    def test_middle_straight_bonus(self):
        hand = make_hand(
            ['2s', '3h', '4d'],
            ['5s', '6h', '7d', '8c', '9s'],
            ['As', 'Ah', 'Ad', 'Ks', 'Kh'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.middle] == 4

    def test_middle_three_of_a_kind_bonus(self):
        hand = make_hand(
            ['2s', '3h', '4d'],
            ['As', 'Ah', 'Ad', '5c', '6d'],
            ['7s', '8h', '9d', 'Tc', 'Jh'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.middle] == 2

    def test_middle_no_bonus_for_two_pairs(self):
        hand = make_hand(
            ['2s', '3h', '4d'],
            ['As', 'Ah', 'Ks', 'Kh', '5c'],
            ['6s', '7h', '8d', '9c', 'Ts'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.middle] == 0

    # Front row bonuses
    def test_front_trips_aces_bonus(self):
        hand = Hand()
        hand.hands[HandId.front] = single_hand('As', 'Ah', 'Ad')
        hand.hands[HandId.middle] = single_hand('2c', '3s', '4h', '5d', '6c')
        hand.hands[HandId.back] = single_hand('7s', '8h', '9d', 'Tc', 'Jh')
        hand.compute_bonus()
        assert hand.bonus[HandId.front] == 22

    def test_front_trips_twos_bonus(self):
        hand = Hand()
        hand.hands[HandId.front] = single_hand('2s', '2h', '2d')
        hand.hands[HandId.middle] = single_hand('3c', '4s', '5h', '6d', '7c')
        hand.hands[HandId.back] = single_hand('8s', '9h', 'Td', 'Jc', 'Qh')
        hand.compute_bonus()
        assert hand.bonus[HandId.front] == 10

    def test_front_pair_aces_bonus(self):
        hand = make_hand(
            ['As', 'Ah', '2d'],
            ['3c', '4s', '5h', '6d', '7c'],
            ['8s', 'Ts', 'Js', 'Qs', 'Ks'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.front] == 9

    def test_front_pair_kings_bonus(self):
        hand = make_hand(
            ['Ks', 'Kh', '2d'],
            ['3c', '4s', '5h', '6d', '7c'],
            ['8s', 'Ts', 'Js', 'Qs', 'As'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.front] == 8

    def test_front_pair_queens_bonus(self):
        # Q int_height=10, bonus map: {10: 7}
        hand = make_hand(
            ['Qs', 'Qh', '2d'],
            ['3c', '4s', '5h', '6d', '7c'],
            ['8s', 'Ts', 'Js', 'As', 'Ks'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.front] == 7

    def test_front_pair_sixes_bonus(self):
        hand = make_hand(
            ['6s', '6h', '2d'],
            ['3c', '4s', '5h', '7d', '8c'],
            ['9s', 'Ts', 'Js', 'Qs', 'Ks'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.front] == 1

    def test_front_pair_fives_no_bonus(self):
        # Pair of 5s is below threshold (threshold is pair of 6s)
        hand = make_hand(
            ['5s', '5h', '2d'],
            ['3c', '4s', '6h', '7d', '8c'],
            ['9s', 'Ts', 'Js', 'Qs', 'Ks'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.front] == 0

    def test_front_pair_jacks_bonus(self):
        # J int_height=9, bonus map: {9: 6}
        hand = make_hand(
            ['Js', 'Jh', '2d'],
            ['3c', '4s', '5h', '6d', '7c'],
            ['8s', 'Ts', 'As', 'Qs', 'Ks'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.front] == 6

    def test_front_pair_fours_no_bonus(self):
        # 4 int_height=2, below the minimum bonus threshold (6s, int_height=4)
        hand = make_hand(
            ['4s', '4h', '2d'],
            ['3c', '5s', '6h', '7d', '8c'],
            ['9s', 'Ts', 'Js', 'Qs', 'Ks'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.front] == 0

    def test_front_high_card_no_bonus(self):
        hand = make_hand(
            ['As', 'Kh', '2d'],
            ['3c', '4s', '5h', '6d', '7c'],
            ['8s', 'Ts', 'Js', 'Qs', '9s'],
        )
        hand.compute_bonus()
        assert hand.bonus[HandId.front] == 0

    def test_compute_bonus_on_incomplete_raises(self):
        hand = Hand()
        with pytest.raises(ValueError):
            hand.compute_bonus()


# ============================================================
# Hand — score_versus
# ============================================================

class TestScoreVersus:

    def test_both_foul_zero_zero(self):
        # Both hands have front stronger than middle -> both foul
        h1 = make_hand(
            ['As', 'Ah', 'Ad'],
            ['2c', '4s', '6h', '8d', 'Tc'],
            ['3s', '5h', '7d', '9c', 'Jh'],
        )
        h2 = make_hand(
            ['Ks', 'Kh', 'Kd'],
            ['2h', '4c', '6d', '8c', 'Td'],
            ['3h', '5d', '7c', '9h', 'Jd'],
        )
        s1, s2 = h1.score_versus(h2)
        assert s1 == 0
        assert s2 == 0

    def test_one_foul_loses_all(self):
        # h1 valid, h2 fouls
        h1 = make_hand(
            ['2s', '3h', '4d'],
            ['5h', '6c', '7d', '8c', '9d'],
            ['Ts', 'Jh', 'Qd', 'Kc', 'As'],
        )
        h2 = make_hand(
            ['As', 'Ah', 'Ad'],
            ['2c', '4s', '6h', '8d', 'Tc'],
            ['3s', '5h', '7d', '9c', 'Jh'],
        )
        s1, s2 = h1.score_versus(h2)
        assert s2 == 0
        assert s1 > 0

    def test_scoop_adds_three_bonus_points(self):
        # h1 wins all three rows — scoop adds 3 to battle score (3 -> 6)
        h1 = make_hand(
            ['As', 'Ah', '2d'],       # pair aces > pair 2s
            ['5s', '6h', '7d', '8c', '9s'],  # straight > high card
            ['2h', '4h', '6h', '8h', 'Th'],  # flush > high card
        )
        h2 = make_hand(
            ['2c', '2h', '3d'],       # pair 2s
            ['Th', 'Jd', 'Qc', 'Ks', '2s'],  # high card (no straight - has pair? no... 2s is there but unique heights)
            ['3h', '5d', '7c', '9h', 'Jd'],  # high card
        )
        s1, s2 = h1.score_versus(h2)
        # h1 scoops: battle_score = 3 + 3 = 6
        # h1 also has bonuses: flush in back (+4), pair aces in front (+9), straight in middle (+4)
        assert s1 >= 6

    def test_split_result_both_score(self):
        # h1 wins front only, h2 wins middle and back
        # h1: pair aces <= straight <= full house  (valid, no foul)
        h1 = make_hand(
            ['As', 'Ah', '3d'],               # pair aces (strong front)
            ['5s', '6h', '7d', '8c', '9s'],   # straight
            ['Kc', 'Ks', 'Kd', 'Qh', 'Qd'],  # full house (back >= middle)
        )
        # h2: pair 2s <= four of a kind <= straight flush  (valid, no foul)
        h2 = make_hand(
            ['2c', '2h', '4d'],               # pair 2s (weak front)
            ['As', 'Ah', 'Ad', 'Ac', '5d'],   # four of a kind (beats h1 straight)
            ['3s', '4s', '5s', '6s', '7s'],   # straight flush (beats h1 full house)
        )
        s1, s2 = h1.score_versus(h2)
        assert s1 > 0  # h1 wins front + royalties
        assert s2 > 0  # h2 wins middle and back + big royalties

    def test_tied_row_neither_scores(self):
        # h1 and h2 have identical hand strength on all rows and no royalties.
        # In OFC, ties award neither player battle points, and without royalties
        # both scores must be 0.
        # Use all-high-card hands (no royalties) with non-consecutive, mixed-suit cards.
        # front val (2,1,0) <= middle val (11,9,7,5,3) <= back val (12,10,8,6,4)  => valid
        h1 = make_hand(
            ['2s', '3h', '4d'],
            ['5h', '7c', '9d', 'Js', 'Kh'],
            ['Ah', 'Qd', 'Tc', '8s', '6c'],
        )
        h2 = make_hand(
            ['2c', '3d', '4h'],
            ['5d', '7h', '9c', 'Jd', 'Kd'],
            ['Ad', 'Qh', 'Ts', '8h', '6s'],
        )
        s1, s2 = h1.score_versus(h2)
        # All rows tied, no royalties -> both scores 0
        assert s1 == 0
        assert s2 == 0

    def test_royalties_added_to_winner(self):
        # h1 has a flush on back (royalty 4) and wins
        h1 = make_hand(
            ['As', 'Ah', '2d'],       # pair aces (front royalty 9)
            ['3c', '4s', '5h', '6d', '7c'],  # straight (middle royalty 4)
            ['2s', '4s', '6s', '8s', 'Ts'],  # flush (back royalty 4)
        )
        h2 = make_hand(
            ['2c', '2h', '3d'],
            ['4h', '6c', '8d', 'Tc', 'Qh'],
            ['3s', '5h', '7d', '9c', 'Jh'],
        )
        s1, s2 = h1.score_versus(h2)
        # h1 scoops (6 battle) + 9 (AA front) + 4 (straight middle) + 4 (flush back) = 23
        assert s1 == 23


# ============================================================
# Game — play generation helpers
# ============================================================

class TestGeneratePlays:
    def test_initial_plays_no_discard(self):
        for play in generate_initial_plays():
            assert PlayId.discard not in play

    def test_initial_plays_max_3_front(self):
        for play in generate_initial_plays():
            assert play.count(PlayId.front) <= 3

    def test_initial_plays_all_length_5(self):
        for play in generate_initial_plays():
            assert len(play) == 5

    def test_initial_plays_no_duplicates(self):
        plays = generate_initial_plays()
        assert len(plays) == len(set(plays))

    def test_initial_plays_nonempty(self):
        assert len(generate_initial_plays()) > 0

    def test_non_initial_plays_exactly_one_discard(self):
        for play in generate_non_initial_plays():
            assert play.count(PlayId.discard) == 1

    def test_non_initial_plays_all_length_3(self):
        for play in generate_non_initial_plays():
            assert len(play) == 3

    def test_non_initial_plays_no_duplicates(self):
        plays = generate_non_initial_plays()
        assert len(plays) == len(set(plays))

    def test_non_initial_plays_nonempty(self):
        assert len(generate_non_initial_plays()) > 0

    def test_initial_plays_use_only_non_discard(self):
        valid_ids = {PlayId.front, PlayId.middle, PlayId.back}
        for play in generate_initial_plays():
            assert all(p in valid_ids for p in play)


# ============================================================
# Game — is_valid_play
# ============================================================

class TestGameIsValidPlay:
    def test_initial_valid_3_front_2_back(self):
        game = Game()
        cards = list(game.draw_five_cards())
        play = (PlayId.front, PlayId.front, PlayId.front, PlayId.back, PlayId.back)
        assert game.is_valid_play(PlayerId.player_1, cards, play)

    def test_initial_valid_3_front_2_middle(self):
        game = Game()
        cards = list(game.draw_five_cards())
        play = (PlayId.front, PlayId.front, PlayId.front, PlayId.middle, PlayId.middle)
        assert game.is_valid_play(PlayerId.player_1, cards, play)

    def test_initial_valid_2_front_3_back(self):
        game = Game()
        cards = list(game.draw_five_cards())
        play = (PlayId.front, PlayId.front, PlayId.back, PlayId.back, PlayId.back)
        assert game.is_valid_play(PlayerId.player_1, cards, play)

    def test_initial_discard_not_allowed(self):
        game = Game()
        cards = list(game.draw_five_cards())
        play = (PlayId.front, PlayId.front, PlayId.front, PlayId.back, PlayId.discard)
        assert not game.is_valid_play(PlayerId.player_1, cards, play)

    def test_initial_too_many_front_cards(self):
        game = Game()
        cards = list(game.draw_five_cards())
        play = (PlayId.front, PlayId.front, PlayId.front, PlayId.front, PlayId.back)
        assert not game.is_valid_play(PlayerId.player_1, cards, play)

    def test_mismatched_lengths_invalid(self):
        game = Game()
        cards = list(game.draw_five_cards())
        play = (PlayId.front, PlayId.front, PlayId.back)  # 3 ids for 5 cards
        assert not game.is_valid_play(PlayerId.player_1, cards, play)

    def test_four_cards_invalid(self):
        game = Game()
        cards = list(game.draw_five_cards())[:4]
        play = (PlayId.front, PlayId.front, PlayId.back, PlayId.back)
        assert not game.is_valid_play(PlayerId.player_1, cards, play)

    def test_non_initial_valid_with_discard(self):
        game = Game()
        cards5 = list(game.draw_five_cards())
        game.play(PlayerId.player_1, cards5,
                  (PlayId.front, PlayId.front, PlayId.front, PlayId.back, PlayId.back))
        cards3 = list(game.draw_three_cards())
        play = (PlayId.back, PlayId.middle, PlayId.discard)
        assert game.is_valid_play(PlayerId.player_1, cards3, play)

    def test_non_initial_no_discard_invalid(self):
        game = Game()
        cards5 = list(game.draw_five_cards())
        game.play(PlayerId.player_1, cards5,
                  (PlayId.front, PlayId.front, PlayId.front, PlayId.back, PlayId.back))
        cards3 = list(game.draw_three_cards())
        play = (PlayId.back, PlayId.middle, PlayId.middle)
        assert not game.is_valid_play(PlayerId.player_1, cards3, play)

    def test_non_initial_two_discards_invalid(self):
        game = Game()
        cards5 = list(game.draw_five_cards())
        game.play(PlayerId.player_1, cards5,
                  (PlayId.front, PlayId.front, PlayId.front, PlayId.back, PlayId.back))
        cards3 = list(game.draw_three_cards())
        play = (PlayId.discard, PlayId.discard, PlayId.back)
        assert not game.is_valid_play(PlayerId.player_1, cards3, play)

    def test_non_initial_overflow_front_invalid(self):
        # front already has 3 cards; cannot add more
        game = Game()
        cards5 = list(game.draw_five_cards())
        game.play(PlayerId.player_1, cards5,
                  (PlayId.front, PlayId.front, PlayId.front, PlayId.back, PlayId.back))
        cards3 = list(game.draw_three_cards())
        play = (PlayId.front, PlayId.back, PlayId.discard)
        assert not game.is_valid_play(PlayerId.player_1, cards3, play)

    def test_completed_hand_is_invalid(self):
        random.seed(0)
        game = Game()
        player = RandomPlayer()
        # Play until player_1's hand is complete
        cards5 = list(game.draw_five_cards())
        play = player.get_play(game, PlayerId.player_1, cards5, initial=True)
        game.play(PlayerId.player_1, cards5, play)
        while not game.hands[PlayerId.player_1].is_hand_complete():
            cards3 = list(game.draw_three_cards())
            play = player.get_play(game, PlayerId.player_1, cards3, initial=False)
            game.play(PlayerId.player_1, cards3, play)
        # Hand is complete — any play must be invalid
        leftover = list(game.draw_three_cards())
        play = (PlayId.back, PlayId.back, PlayId.discard)
        assert not game.is_valid_play(PlayerId.player_1, leftover, play)


# ============================================================
# Game — play execution
# ============================================================

class TestGamePlay:
    def test_play_places_cards_in_front(self):
        game = Game()
        cards = list(game.draw_five_cards())
        play = (PlayId.front, PlayId.front, PlayId.front, PlayId.back, PlayId.back)
        game.play(PlayerId.player_1, cards, play)
        assert len(game.hands[PlayerId.player_1].hands[HandId.front]) == 3

    def test_play_places_cards_in_middle(self):
        game = Game()
        cards = list(game.draw_five_cards())
        play = (PlayId.middle, PlayId.middle, PlayId.middle, PlayId.back, PlayId.back)
        game.play(PlayerId.player_1, cards, play)
        assert len(game.hands[PlayerId.player_1].hands[HandId.middle]) == 3

    def test_play_places_cards_in_back(self):
        game = Game()
        cards = list(game.draw_five_cards())
        play = (PlayId.front, PlayId.front, PlayId.front, PlayId.back, PlayId.back)
        game.play(PlayerId.player_1, cards, play)
        assert len(game.hands[PlayerId.player_1].hands[HandId.back]) == 2

    def test_play_invalid_raises(self):
        game = Game()
        cards = list(game.draw_five_cards())
        play = (PlayId.front, PlayId.front, PlayId.front, PlayId.front, PlayId.back)
        with pytest.raises(ValueError):
            game.play(PlayerId.player_1, cards, play)

    def test_discarded_card_tracked(self):
        game = Game()
        cards5 = list(game.draw_five_cards())
        game.play(PlayerId.player_1, cards5,
                  (PlayId.front, PlayId.front, PlayId.front, PlayId.back, PlayId.back))
        cards3 = list(game.draw_three_cards())
        discarded = cards3[2]
        game.play(PlayerId.player_1, cards3,
                  (PlayId.back, PlayId.middle, PlayId.discard))
        assert discarded in game.discarded_cards[PlayerId.player_1]

    def test_discards_for_both_players_tracked_separately(self):
        game = Game()
        # Player 1 initial
        c5_p1 = list(game.draw_five_cards())
        game.play(PlayerId.player_1, c5_p1,
                  (PlayId.front, PlayId.front, PlayId.front, PlayId.back, PlayId.back))
        # Player 2 initial
        c5_p2 = list(game.draw_five_cards())
        game.play(PlayerId.player_2, c5_p2,
                  (PlayId.front, PlayId.front, PlayId.front, PlayId.back, PlayId.back))
        # Player 1 discards
        c3_p1 = list(game.draw_three_cards())
        game.play(PlayerId.player_1, c3_p1,
                  (PlayId.back, PlayId.middle, PlayId.discard))
        # Player 2 discards
        c3_p2 = list(game.draw_three_cards())
        game.play(PlayerId.player_2, c3_p2,
                  (PlayId.back, PlayId.middle, PlayId.discard))
        assert len(game.discarded_cards[PlayerId.player_1]) == 1
        assert len(game.discarded_cards[PlayerId.player_2]) == 1

    def test_game_draw_five_reduces_deck(self):
        game = Game()
        game.draw_five_cards()
        assert len(game.deck) == 47

    def test_game_draw_three_reduces_deck(self):
        game = Game()
        game.draw_three_cards()
        assert len(game.deck) == 49

    def test_game_repr_is_string(self):
        game = Game()
        assert isinstance(repr(game), str)


# ============================================================
# RandomPlayer
# ============================================================

class TestRandomPlayer:
    def test_initial_play_is_valid(self):
        game = Game()
        player = RandomPlayer()
        cards = list(game.draw_five_cards())
        play = player.get_play(game, PlayerId.player_1, cards, initial=True)
        assert game.is_valid_play(PlayerId.player_1, cards, play)

    def test_non_initial_play_is_valid(self):
        game = Game()
        player = RandomPlayer()
        cards5 = list(game.draw_five_cards())
        game.play(PlayerId.player_1, cards5,
                  (PlayId.front, PlayId.front, PlayId.front, PlayId.back, PlayId.back))
        cards3 = list(game.draw_three_cards())
        play = player.get_play(game, PlayerId.player_1, cards3, initial=False)
        assert game.is_valid_play(PlayerId.player_1, cards3, play)

    def test_play_returns_tuple_of_play_ids(self):
        game = Game()
        player = RandomPlayer()
        cards = list(game.draw_five_cards())
        play = player.get_play(game, PlayerId.player_1, cards, initial=True)
        assert isinstance(play, tuple)
        assert all(isinstance(p, PlayId) for p in play)

    def test_initial_play_length_5(self):
        game = Game()
        player = RandomPlayer()
        cards = list(game.draw_five_cards())
        play = player.get_play(game, PlayerId.player_1, cards, initial=True)
        assert len(play) == 5

    def test_non_initial_play_length_3(self):
        game = Game()
        player = RandomPlayer()
        cards5 = list(game.draw_five_cards())
        game.play(PlayerId.player_1, cards5,
                  (PlayId.front, PlayId.front, PlayId.front, PlayId.back, PlayId.back))
        cards3 = list(game.draw_three_cards())
        play = player.get_play(game, PlayerId.player_1, cards3, initial=False)
        assert len(play) == 3

    def test_multiple_plays_not_always_identical(self):
        # With enough samples, a random player should produce varied plays
        plays = set()
        for seed in range(50):
            random.seed(seed)
            game = Game()
            player = RandomPlayer()
            cards = list(game.draw_five_cards())
            plays.add(player.get_play(game, PlayerId.player_1, cards, initial=True))
        assert len(plays) > 1


# ============================================================
# GameLoop
# ============================================================

class TestGameLoop:
    def test_run_returns_two_ints(self):
        random.seed(42)
        loop = GameLoop(RandomPlayer(), RandomPlayer(), verbose=False)
        s1, s2 = loop.run()
        assert isinstance(s1, int)
        assert isinstance(s2, int)

    def test_run_completes_both_hands(self):
        random.seed(42)
        game = Game()
        loop = GameLoop(RandomPlayer(), RandomPlayer(), game=game, verbose=False)
        loop.run()
        assert game.hands[PlayerId.player_1].is_hand_complete()
        assert game.hands[PlayerId.player_2].is_hand_complete()

    def test_run_with_provided_game(self):
        random.seed(7)
        game = Game()
        loop = GameLoop(RandomPlayer(), RandomPlayer(), game=game, verbose=False)
        result = loop.run()
        assert result is not None

    def test_multiple_runs_vary(self):
        results = set()
        for seed in range(20):
            random.seed(seed)
            loop = GameLoop(RandomPlayer(), RandomPlayer(), verbose=False)
            results.add(loop.run())
        assert len(results) > 1

    def test_deck_depleted_correctly(self):
        # After a full game: 5 + 5 = 10 initial + 4*3 = 12 each player's subsequent draws
        # Total drawn = 5 + 5 + 4*3 + 4*3 = 34, leaving 52 - 34 = 18 cards
        random.seed(42)
        game = Game()
        loop = GameLoop(RandomPlayer(), RandomPlayer(), game=game, verbose=False)
        loop.run()
        assert len(game.deck) == 18

    def test_run_scores_are_nonneg_when_no_foul(self):
        # Run many games — scores should always be non-negative
        # (fouling produces 0 score, never negative)
        for seed in range(30):
            random.seed(seed)
            loop = GameLoop(RandomPlayer(), RandomPlayer(), verbose=False)
            s1, s2 = loop.run()
            assert s1 >= 0
            assert s2 >= 0


# ============================================================
# play_id_to_hand_id mapping
# ============================================================

class TestPlayIdToHandId:
    def test_front_mapping(self):
        assert play_id_to_hand_id[PlayId.front] == HandId.front

    def test_middle_mapping(self):
        assert play_id_to_hand_id[PlayId.middle] == HandId.middle

    def test_back_mapping(self):
        assert play_id_to_hand_id[PlayId.back] == HandId.back

    def test_discard_not_in_mapping(self):
        assert PlayId.discard not in play_id_to_hand_id


# ============================================================
# Enums
# ============================================================

class TestEnums:
    def test_suit_members(self):
        assert set(Suit) == {Suit.d, Suit.c, Suit.s, Suit.h}

    def test_hand_id_members(self):
        assert set(HandId) == {HandId.front, HandId.middle, HandId.back}

    def test_player_id_members(self):
        assert set(PlayerId) == {PlayerId.player_1, PlayerId.player_2}

    def test_play_id_members(self):
        assert set(PlayId) == {PlayId.front, PlayId.middle, PlayId.back, PlayId.discard}

    def test_hand_rank_ordering(self):
        assert HandRank.HIGH_CARD < HandRank.ONE_PAIR < HandRank.TWO_PAIRS
        assert HandRank.TWO_PAIRS < HandRank.THREE_OF_A_KIND < HandRank.STRAIGHT
        assert HandRank.STRAIGHT < HandRank.FLUSH < HandRank.FULL_HOUSE
        assert HandRank.FULL_HOUSE < HandRank.FOUR_OF_A_KIND < HandRank.STRAIGHT_FLUSH

    def test_hand_rank_values(self):
        assert HandRank.HIGH_CARD == 0
        assert HandRank.STRAIGHT_FLUSH == 8


# ============================================================
# bonus_map structure
# ============================================================

class TestBonusMapStructure:
    def test_all_hand_ids_present(self):
        for hand_id in HandId:
            assert hand_id in bonus_map

    def test_back_has_straight_flush_map(self):
        assert HandRank.STRAIGHT_FLUSH in bonus_map[HandId.back]
        assert isinstance(bonus_map[HandId.back][HandRank.STRAIGHT_FLUSH], dict)

    def test_back_royal_flush_highest(self):
        sf_map = bonus_map[HandId.back][HandRank.STRAIGHT_FLUSH]
        assert sf_map[12] == 25  # Royal flush

    def test_middle_royal_flush_double_back(self):
        back_royal = bonus_map[HandId.back][HandRank.STRAIGHT_FLUSH][12]
        middle_royal = bonus_map[HandId.middle][HandRank.STRAIGHT_FLUSH][12]
        assert middle_royal == 2 * back_royal

    def test_front_trips_aces_highest_front_bonus(self):
        trips_map = bonus_map[HandId.front][HandRank.THREE_OF_A_KIND]
        assert trips_map[12] == 22  # Aces

    def test_front_pair_aces_highest_pair_bonus(self):
        pair_map = bonus_map[HandId.front][HandRank.ONE_PAIR]
        assert pair_map[12] == 9  # Aces
