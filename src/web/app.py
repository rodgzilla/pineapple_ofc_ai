import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from flask import Flask, request, jsonify, render_template
from src.engine.game import (
    Game, PlayerId, PlayId, HandId, HandRank,
    MonteCarloPlayer, UCTPlayer, Card, Suit,
)

app = Flask(__name__)
app.secret_key = 'pineapple-ofc-secret'

# In-memory game store: game_id -> game_state dict
games = {}

# Tracks how many games have been started (used to alternate first player)
game_count = 0

# Simulations per AI turn for UCTPlayer (lower = faster response, weaker AI).
# UCTPlayer with HeuristicPlayer rollouts produces much stronger play than
# the old MonteCarloPlayer at the same simulation budget, because:
#   1. UCT focuses simulations on promising moves (not round-robin)
#   2. HeuristicPlayer rollouts are far more accurate than random play
N_SIMULATIONS = 20000

HAND_RANK_NAMES = {
    HandRank.HIGH_CARD:       'High Card',
    HandRank.ONE_PAIR:        'One Pair',
    HandRank.TWO_PAIRS:       'Two Pair',
    HandRank.THREE_OF_A_KIND: 'Three of a Kind',
    HandRank.STRAIGHT:        'Straight',
    HandRank.FLUSH:           'Flush',
    HandRank.FULL_HOUSE:      'Full House',
    HandRank.FOUR_OF_A_KIND:  'Four of a Kind',
    HandRank.STRAIGHT_FLUSH:  'Straight Flush',
}

ROW_TO_PLAY_ID = {
    'front':   PlayId.front,
    'middle':  PlayId.middle,
    'back':    PlayId.back,
    'discard': PlayId.discard,
}


def card_to_dict(card):
    return {'height': card.height, 'suit': card.suit.name}


def hand_to_dict(hand):
    return {
        hand_id.name: [card_to_dict(c) for c in hand.hands[hand_id].cards]
        for hand_id in HandId
    }


def build_response(game_id, game_state):
    game  = game_state['game']
    phase = game_state['phase']

    resp = {
        'game_id':      game_id,
        'phase':        phase,
        'player_board': hand_to_dict(game.hands[PlayerId.player_1]),
        'ai_board':     hand_to_dict(game.hands[PlayerId.player_2]),
        'cards':        [card_to_dict(c) for c in game_state.get('current_cards', [])],
        'ai_goes_first': game_state.get('ai_goes_first', False),
    }

    if phase == 'game_over':
        resp.update(game_state['result'])

    return resp


def run_ai_turns(game_state):
    """Run exactly one AI turn (to keep card counts equal) then deal the human's next hand.

    The flow is: human acts → AI acts → human acts → AI acts …
    This keeps both players synchronised at the same card count when the
    MonteCarloPlayer kicks off its GameLoop simulations, preventing the
    IndexError that occurs when one side is already complete inside the loop.
    """
    game = game_state['game']
    ai   = game_state['ai_player']
    p1   = game.hands[PlayerId.player_1]
    p2   = game.hands[PlayerId.player_2]

    # Run one AI turn whenever the human is ahead (or equal when AI goes first).
    ai_goes_first = game_state.get('ai_goes_first', False)
    should_play_ai = (
        not p2.is_hand_complete() and
        (len(p2) <= len(p1) if ai_goes_first else len(p2) < len(p1))
    )
    if should_play_ai:
        is_initial = (len(p2) == 0)
        cards      = list(
            game.draw_five_cards() if is_initial else game.draw_three_cards()
        )
        play_ids = ai.get_play(
            game=game,
            player_id=PlayerId.player_2,
            cards=cards,
            initial=is_initial,
        )
        game.play(PlayerId.player_2, cards, play_ids)

    if p1.is_hand_complete() and p2.is_hand_complete():
        _finalize_game(game_state)
        return

    # Deal the human's next hand.
    if not p1.is_hand_complete():
        cards = list(game.draw_three_cards())
        game_state['current_cards'] = cards
        game_state['phase']         = 'human_turn'


def _finalize_game(game_state):
    game = game_state['game']
    h1   = game.hands[PlayerId.player_1]
    h2   = game.hands[PlayerId.player_2]

    score_p1, score_p2 = h1.score_versus(h2)

    hand_results = {}
    for hand_id in HandId:
        s1 = h1.strength[hand_id]
        s2 = h2.strength[hand_id]
        winner = 'player' if s1 > s2 else ('ai' if s2 > s1 else 'tie')
        hand_results[hand_id.name] = {
            'player':       HAND_RANK_NAMES.get(s1.rank, ''),
            'ai':           HAND_RANK_NAMES.get(s2.rank, ''),
            'winner':       winner,
            'player_bonus': h1.bonus.get(hand_id, 0),
            'ai_bonus':     h2.bonus.get(hand_id, 0),
        }

    game_state['phase']  = 'game_over'
    game_state['result'] = {
        'scores':       {'player': score_p1, 'ai': score_p2},
        'is_foul':      {'player': bool(h1.is_foul()), 'ai': bool(h2.is_foul())},
        'hand_results': hand_results,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/new_game', methods=['POST'])
def new_game():
    global game_count
    ai_goes_first = (game_count % 2 == 1)
    game_count   += 1

    game_id  = str(uuid.uuid4())
    game     = Game()
    ai_player = UCTPlayer(
        player_id=PlayerId.player_2,
        n_run=N_SIMULATIONS,
        cheating=False,
    )

    game_state = {
        'game':          game,
        'ai_player':     ai_player,
        'phase':         'init_human',
        'current_cards': [],
        'ai_goes_first': ai_goes_first,
    }

    if ai_goes_first:
        # AI plays its opening five first, then deal to the human
        ai_cards = list(game.draw_five_cards())
        play_ids = ai_player.get_play(
            game=game,
            player_id=PlayerId.player_2,
            cards=ai_cards,
            initial=True,
        )
        game.play(PlayerId.player_2, ai_cards, play_ids)

    # Deal the human's opening five cards
    cards = list(game.draw_five_cards())
    game_state['current_cards'] = cards

    games[game_id] = game_state
    return jsonify(build_response(game_id, game_state))


@app.route('/api/play', methods=['POST'])
def play():
    data       = request.get_json(force=True)
    game_id    = data.get('game_id')
    placements = data.get('placements')   # [{card_idx, row}, …]

    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404

    game_state = games[game_id]

    if game_state['phase'] not in ('init_human', 'human_turn'):
        return jsonify({'error': 'Not the human\'s turn'}), 400

    game          = game_state['game']
    current_cards = game_state['current_cards']

    if len(placements) != len(current_cards):
        return jsonify({'error': f'Expected {len(current_cards)} placements'}), 400

    try:
        sorted_placements = sorted(placements, key=lambda p: p['card_idx'])
        play_ids = tuple(ROW_TO_PLAY_ID[p['row']] for p in sorted_placements)
        cards    = [current_cards[p['card_idx']] for p in sorted_placements]
    except (KeyError, IndexError, TypeError) as exc:
        return jsonify({'error': f'Invalid placement data: {exc}'}), 400

    if not game.is_valid_play(PlayerId.player_1, cards, play_ids):
        return jsonify({'error': 'Invalid move — check row capacity and discard rules'}), 400

    game.play(PlayerId.player_1, cards, play_ids)
    game_state['current_cards'] = []

    run_ai_turns(game_state)

    return jsonify(build_response(game_id, game_state))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
