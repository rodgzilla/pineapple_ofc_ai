/* ─────────────────────────────────────────────────────────────────────────
   Pineapple OFC – frontend game logic
   ───────────────────────────────────────────────────────────────────────── */

'use strict';

/* ── State ─────────────────────────────────────────────────────────────── */
let gameId        = null;
let currentCards  = [];       // [{height, suit}, …]  current hand being placed
let assignments   = {};       // card_idx → row string ('front'|'middle'|'back'|'discard')
let isInitialTurn = false;    // true when placing 5 cards at start

const SUIT_SYMBOL = { d: '♦', c: '♣', s: '♠', h: '♥' };
const SUIT_COLOR  = { d: 'red', c: 'black', s: 'black', h: 'red' };

/* ── DOM shortcuts ──────────────────────────────────────────────────────── */
const $ = id => document.getElementById(id);

/* ── Entry points ───────────────────────────────────────────────────────── */

async function newGame() {
  hideGameOver();
  showLoading();
  $('welcome').classList.add('hidden');

  try {
    const resp  = await fetch('/api/new_game', { method: 'POST' });
    const state = await resp.json();
    applyState(state);
  } catch (e) {
    setStatus('Error starting game: ' + e.message);
  } finally {
    hideLoading();
  }
}

async function submitPlay() {
  if (!validateAssignments()) return;

  const placements = Object.entries(assignments).map(([idx, row]) => ({
    card_idx: parseInt(idx),
    row,
  }));

  showLoading();
  $('btn-confirm').disabled = true;

  try {
    const resp  = await fetch('/api/play', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ game_id: gameId, placements }),
    });
    const state = await resp.json();

    if (state.error) {
      setStatus('Error: ' + state.error);
      $('btn-confirm').disabled = false;
      return;
    }

    applyState(state);
  } catch (e) {
    setStatus('Network error: ' + e.message);
    $('btn-confirm').disabled = false;
  } finally {
    hideLoading();
  }
}

/* ── State renderer ─────────────────────────────────────────────────────── */

function applyState(state) {
  gameId = state.game_id;

  renderBoard('player', state.player_board);
  renderBoard('ai',     state.ai_board);

  $('table').classList.remove('hidden');

  if (state.phase === 'init_human' || state.phase === 'human_turn') {
    isInitialTurn = (state.phase === 'init_human');
    currentCards  = state.cards;
    assignments   = {};
    renderHandArea(currentCards);
    showActionArea(
      isInitialTurn
        ? 'Place Your Opening 5 Cards'
        : 'Place Your Cards'
    );
    setStatus(
      isInitialTurn
        ? 'Opening hand: place 3 cards in Front and 2 in Middle/Back.'
        : 'Draw: place 2 cards and discard 1.'
    );
  } else if (state.phase === 'game_over') {
    hideActionArea();
    showGameOver(state);
    setStatus('Game over!');
  } else {
    hideActionArea();
    setStatus('Unexpected phase: ' + state.phase);
  }
}

/* ── Board rendering ────────────────────────────────────────────────────── */

function renderBoard(who, board) {
  ['front', 'middle', 'back'].forEach(row => {
    const max   = row === 'front' ? 3 : 5;
    const cards = board[row] || [];
    const el    = $(`${who}-${row}`);
    el.innerHTML = '';

    cards.forEach(c => el.appendChild(makeCard(c)));
    for (let i = cards.length; i < max; i++) {
      const slot = document.createElement('div');
      slot.className = 'card-slot';
      el.appendChild(slot);
    }
  });
}

/* ── Hand-area rendering (cards to place) ────────────────────────────────── */

function renderHandArea(cards) {
  const area = $('hand-area');
  area.innerHTML = '';

  cards.forEach((card, idx) => {
    const group = document.createElement('div');
    group.className = 'hand-card-group';
    group.dataset.idx = idx;

    group.appendChild(makeCard(card));
    group.appendChild(makeRowPicker(idx));
    area.appendChild(group);
  });

  updateConfirmButton();
}

function makeRowPicker(idx) {
  const picker = document.createElement('div');
  picker.className = 'row-picker';

  const rows = isInitialTurn
    ? ['front', 'middle', 'back']
    : ['front', 'middle', 'back', 'discard'];

  rows.forEach(row => {
    const btn = document.createElement('button');
    btn.className   = 'row-btn' + (row === 'discard' ? ' discard-btn' : '');
    btn.textContent = row.charAt(0).toUpperCase() + row.slice(1);
    btn.dataset.idx = idx;
    btn.dataset.row = row;
    btn.addEventListener('click', () => assignCard(idx, row));
    picker.appendChild(btn);
  });

  return picker;
}

/* ── Assignment logic ───────────────────────────────────────────────────── */

function assignCard(idx, row) {
  assignments[idx] = row;

  // Update button highlights for this card
  const group = document.querySelector(`.hand-card-group[data-idx="${idx}"]`);
  group.querySelectorAll('.row-btn').forEach(btn => {
    btn.classList.toggle('selected', btn.dataset.row === row);
  });

  updateConfirmButton();
}

function validateAssignments() {
  const n = currentCards.length;

  // All cards must be assigned
  if (Object.keys(assignments).length < n) {
    setHint('Assign all cards before confirming.');
    return false;
  }

  const counts = {};
  Object.values(assignments).forEach(r => {
    counts[r] = (counts[r] || 0) + 1;
  });

  if (isInitialTurn) {
    if ((counts['front'] || 0) > 3) {
      setHint('Front can hold at most 3 cards.');
      return false;
    }
  } else {
    if ((counts['discard'] || 0) !== 1) {
      setHint('You must discard exactly 1 card.');
      return false;
    }
  }

  setHint('');
  return true;
}

function updateConfirmButton() {
  const n       = currentCards.length;
  const allSet  = Object.keys(assignments).length === n;
  let   valid   = allSet;

  if (allSet) {
    const counts = {};
    Object.values(assignments).forEach(r => {
      counts[r] = (counts[r] || 0) + 1;
    });

    if (isInitialTurn && (counts['front'] || 0) > 3) {
      valid = false;
      setHint('Front can hold at most 3 cards.');
    } else if (!isInitialTurn && (counts['discard'] || 0) !== 1) {
      valid = false;
      setHint('Discard exactly 1 card.');
    } else {
      setHint('');
    }
  }

  $('btn-confirm').disabled = !valid;
}

/* ── Card DOM builder ───────────────────────────────────────────────────── */

function makeCard(c) {
  const symbol  = SUIT_SYMBOL[c.suit];
  const color   = SUIT_COLOR[c.suit];
  const display = c.height === 'T' ? '10' : c.height;

  const el = document.createElement('div');
  el.className = `card ${color}`;

  el.innerHTML = `
    <div class="card-corner">
      <span>${display}</span>
      <span>${symbol}</span>
    </div>
    <div class="card-suit-big">${symbol}</div>
    <div class="card-corner bottom">
      <span>${display}</span>
      <span>${symbol}</span>
    </div>`;

  return el;
}

/* ── Game-over screen ───────────────────────────────────────────────────── */

function showGameOver(state) {
  const scores  = state.scores;
  const isFoul  = state.is_foul;
  const results = state.hand_results;

  const playerWon = scores.player > scores.ai;
  const aiWon     = scores.ai > scores.player;
  const tied      = scores.player === scores.ai;

  $('go-title').textContent = playerWon ? '🏆 You Win!' : (tied ? "It's a Tie" : 'AI Wins');

  $('go-scores').innerHTML = `
    <div class="go-score-block">
      <div class="go-score-label">You</div>
      <div class="go-score-value ${playerWon ? 'winner' : 'loser'}">${scores.player}</div>
      ${isFoul.player ? '<div class="foul-badge">FOUL</div>' : ''}
    </div>
    <div class="go-score-block">
      <div class="go-score-label">AI</div>
      <div class="go-score-value ${aiWon ? 'winner' : 'loser'}">${scores.ai}</div>
      ${isFoul.ai ? '<div class="foul-badge">FOUL</div>' : ''}
    </div>`;

  const tbody = $('go-tbody');
  tbody.innerHTML = '';

  ['front', 'middle', 'back'].forEach(row => {
    const r = results[row];
    if (!r) return;

    const pClass = r.winner === 'player' ? 'go-winner' : (r.winner === 'ai' ? 'go-loser' : 'go-tie');
    const aClass = r.winner === 'ai'     ? 'go-winner' : (r.winner === 'player' ? 'go-loser' : 'go-tie');

    const winnerLabel = r.winner === 'player' ? '← You win'
                      : r.winner === 'ai'     ? 'AI wins →'
                      : 'Tie';

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td style="color:#aaa;text-transform:capitalize">${row}</td>
      <td class="${pClass}">${r.player}</td>
      <td class="${pClass}">${r.player_bonus > 0 ? '+' + r.player_bonus : '—'}</td>
      <td class="winner-cell">${winnerLabel}</td>
      <td class="${aClass}">${r.ai}</td>
      <td class="${aClass}">${r.ai_bonus > 0 ? '+' + r.ai_bonus : '—'}</td>`;
    tbody.appendChild(tr);
  });

  $('game-over').classList.remove('hidden');
}

function hideGameOver() {
  $('game-over').classList.add('hidden');
}

/* ── UI helpers ─────────────────────────────────────────────────────────── */

function showLoading()  { $('loading').classList.remove('hidden'); }
function hideLoading()  { $('loading').classList.add('hidden'); }

function showActionArea(title) {
  $('action-title').textContent = title;
  $('action-area').classList.remove('hidden');
}

function hideActionArea() {
  $('action-area').classList.add('hidden');
}

function setStatus(msg) {
  const bar = $('status-bar');
  if (msg) {
    bar.textContent = msg;
    bar.classList.remove('hidden');
  } else {
    bar.classList.add('hidden');
  }
}

function setHint(msg) {
  $('placement-hint').textContent = msg;
}
