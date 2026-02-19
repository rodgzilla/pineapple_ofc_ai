/* ─────────────────────────────────────────────────────────────────────────
   Pineapple OFC – frontend game logic
   ───────────────────────────────────────────────────────────────────────── */
'use strict';

/* ── State ─────────────────────────────────────────────────────────────── */
let gameId            = null;
let currentCards      = [];   // [{height, suit}] – cards in the current hand
let currentServerBoard = null; // board from server (already-placed cards)
let boardPlacements   = { front: [], middle: [], back: [] }; // current-round placements (indices)
let isInitial         = false;
let isActionMode      = false;

/* ── Global running score (persisted in localStorage) ────────────────────── */
let globalScore = { player: 0, ai: 0 };

function loadGlobalScore() {
  try {
    const saved = localStorage.getItem('ofc_score');
    if (saved) globalScore = JSON.parse(saved);
  } catch (_) {}
  renderGlobalScore();
}

function addToGlobalScore(playerDelta, aiDelta) {
  globalScore.player += playerDelta;
  globalScore.ai     += aiDelta;
  try { localStorage.setItem('ofc_score', JSON.stringify(globalScore)); } catch (_) {}
  renderGlobalScore();
}

function resetGlobalScore() {
  globalScore = { player: 0, ai: 0 };
  try { localStorage.removeItem('ofc_score'); } catch (_) {}
  renderGlobalScore();
}

function renderGlobalScore() {
  $('score-player').textContent = globalScore.player;
  $('score-ai').textContent     = globalScore.ai;
}

/* ── SVG sprite map ─────────────────────────────────────────────────────── */
const CARD_SPRITE = '/static/svg-cards.svg';
const SUIT_NAME   = { d: 'diamond', c: 'club', s: 'spade', h: 'heart' };
const HEIGHT_NAME = {
  A: '1', '2': '2', '3': '3', '4': '4', '5': '5',
  '6': '6', '7': '7', '8': '8', '9': '9', T: '10',
  J: 'jack', Q: 'queen', K: 'king',
};

/* ── DOM helper ─────────────────────────────────────────────────────────── */
const $ = id => document.getElementById(id);

/* ── API entry points ───────────────────────────────────────────────────── */
async function newGame() {
  hideGameOver();
  showLoading();
  $('welcome').classList.add('hidden');
  try {
    const state = await fetch('/api/new_game', { method: 'POST' }).then(r => r.json());
    applyState(state);
  } catch (e) {
    setStatus('Error starting game: ' + e.message);
  } finally {
    hideLoading();
  }
}

async function submitPlay() {
  const placements = [];
  ['front', 'middle', 'back'].forEach(row => {
    boardPlacements[row].forEach(idx => placements.push({ card_idx: idx, row }));
  });

  // Auto-discard: for 3-card rounds, the single unplaced card is discarded
  if (!isInitial) {
    const placed = getAllPlacedIndices();
    for (let i = 0; i < currentCards.length; i++) {
      if (!placed.has(i)) { placements.push({ card_idx: i, row: 'discard' }); break; }
    }
  }

  showLoading();
  $('btn-confirm').disabled = true;
  isActionMode = false;
  disableBoardDrop();

  try {
    const resp  = await fetch('/api/play', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId, placements }),
    });
    const state = await resp.json();
    if (state.error) {
      setStatus('Error: ' + state.error);
      $('btn-confirm').disabled = false;
      isActionMode = true;
      enableBoardDrop();
      return;
    }
    applyState(state);
  } catch (e) {
    setStatus('Network error: ' + e.message);
    $('btn-confirm').disabled = false;
    isActionMode = true;
    enableBoardDrop();
  } finally {
    hideLoading();
  }
}

/* ── State renderer ─────────────────────────────────────────────────────── */
function applyState(state) {
  gameId             = state.game_id;
  currentServerBoard = state.player_board;
  renderAIBoard(state.ai_board);
  $('table').classList.remove('hidden');

  if (state.phase === 'init_human' || state.phase === 'human_turn') {
    isInitial       = (state.phase === 'init_human');
    isActionMode    = true;
    currentCards    = state.cards;
    boardPlacements = { front: [], middle: [], back: [] };
    refreshUI();
    showActionArea(
      isInitial
        ? 'Your Cards — drag up to place (Front ≤ 3 cards)'
        : 'Your Cards — drag 2 to the board; the last card is discarded automatically'
    );
    if (isInitial) {
      setStatus(state.ai_goes_first ? 'AI goes first this game.' : 'You go first this game.');
    } else {
      setStatus(null);
    }
    enableBoardDrop();
  } else if (state.phase === 'game_over') {
    isActionMode = false;
    currentServerBoard = state.player_board;
    disableBoardDrop();
    hideActionArea();
    refreshUI();
    showGameOver(state);
    setStatus('Game over!');
  }
}

/* ── Board rendering ────────────────────────────────────────────────────── */
function renderAIBoard(board) {
  ['front', 'middle', 'back'].forEach(row => {
    const max = row === 'front' ? 3 : 5;
    const el  = $(`ai-${row}`);
    el.innerHTML = '';
    (board[row] || []).forEach(c => el.appendChild(makeCard(c)));
    for (let i = (board[row] || []).length; i < max; i++) {
      const slot = document.createElement('div');
      slot.className = 'card-slot';
      el.appendChild(slot);
    }
  });
}

function renderPlayerBoard() {
  ['front', 'middle', 'back'].forEach(row => {
    const max = row === 'front' ? 3 : 5;
    const el  = $(`player-${row}`);
    el.innerHTML = '';

    // Permanent cards placed in previous rounds
    (currentServerBoard[row] || []).forEach(c => el.appendChild(makeCard(c)));

    // Cards placed this round (draggable, gold-highlighted)
    boardPlacements[row].forEach(idx => {
      const card = makeCard(currentCards[idx], true, idx);
      card.classList.add('newly-placed');
      el.appendChild(card);
    });

    // Empty slots
    const filled = (currentServerBoard[row] || []).length + boardPlacements[row].length;
    for (let i = filled; i < max; i++) {
      const slot = document.createElement('div');
      slot.className = 'card-slot';
      el.appendChild(slot);
    }
  });
}

function renderHandArea() {
  const pool   = $('hand-pool');
  pool.innerHTML = '';
  const placed = getAllPlacedIndices();
  const unplacedCount = currentCards.length - placed.size;

  currentCards.forEach((card, idx) => {
    if (!placed.has(idx)) {
      const el = makeCard(card, true, idx);
      el.classList.add('hand-card'); // larger size in the hand pool
      // Mark as auto-discard when exactly one card remains in a 3-card round
      if (!isInitial && unplacedCount === 1) el.classList.add('will-discard');
      pool.appendChild(el);
    }
  });
}

function refreshUI() {
  renderPlayerBoard();
  if (isActionMode) renderHandArea();
  updateConfirmButton();
}

/* ── Card DOM builder (SVG sprite) ──────────────────────────────────────── */
// Always creates at board size. Caller adds 'hand-card' class for the
// larger hand-pool size. 'draggable' class is added when isDraggable=true.
function makeCard(c, isDraggable = false, idx = null) {
  const suitName   = SUIT_NAME[c.suit];
  const heightName = HEIGHT_NAME[c.height];
  const spriteId   = `${suitName}_${heightName}`;

  const wrap = document.createElement('div');
  wrap.className = 'card-wrap';

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 169.075 244.640');
  svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');

  const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
  use.setAttribute('href', `${CARD_SPRITE}#${spriteId}`);
  svg.appendChild(use);
  wrap.appendChild(svg);

  if (isDraggable && idx !== null) {
    wrap.classList.add('draggable');
    wrap.setAttribute('draggable', 'true');
    wrap.dataset.idx = idx;
    wrap.addEventListener('dragstart', e => {
      e.dataTransfer.setData('text/plain', String(idx));
      e.dataTransfer.effectAllowed = 'move';
      setTimeout(() => wrap.classList.add('dragging'), 0);
    });
    wrap.addEventListener('dragend', () => wrap.classList.remove('dragging'));
  }

  return wrap;
}

/* ── Drag-and-drop – board rows ─────────────────────────────────────────── */
function enableBoardDrop() {
  ['front', 'middle', 'back'].forEach(row => {
    const el = $(`player-${row}`);
    el.classList.add('drop-row');
    el.addEventListener('dragover',  onRowDragOver);
    el.addEventListener('dragleave', onRowDragLeave);
    el.addEventListener('drop',      onRowDrop);
  });
  // Hand pool also accepts drops (return card to hand)
  const pool = $('hand-pool');
  pool.addEventListener('dragover', e => e.preventDefault());
  pool.addEventListener('drop', onPoolDrop);
}

function disableBoardDrop() {
  ['front', 'middle', 'back'].forEach(row => {
    const el = $(`player-${row}`);
    el.classList.remove('drop-row', 'drag-over');
    el.removeEventListener('dragover',  onRowDragOver);
    el.removeEventListener('dragleave', onRowDragLeave);
    el.removeEventListener('drop',      onRowDrop);
  });
}

function onRowDragOver(e)  { e.preventDefault(); this.classList.add('drag-over'); }
function onRowDragLeave(e) { if (!this.contains(e.relatedTarget)) this.classList.remove('drag-over'); }
function onRowDrop(e) {
  e.preventDefault();
  this.classList.remove('drag-over');
  const idx = parseInt(e.dataTransfer.getData('text/plain'));
  if (!isNaN(idx)) placeCardOnRow(idx, this.dataset.row);
}
function onPoolDrop(e) {
  e.preventDefault();
  const idx = parseInt(e.dataTransfer.getData('text/plain'));
  if (!isNaN(idx)) returnCardToHand(idx);
}

/* ── Card placement logic ───────────────────────────────────────────────── */
function placeCardOnRow(idx, row) {
  const max     = row === 'front' ? 3 : 5;
  const existing = (currentServerBoard[row] || []).length;
  const current  = boardPlacements[row].length;
  if (existing + current >= max) {
    setHint(`${row.charAt(0).toUpperCase() + row.slice(1)} row is full.`);
    return;
  }
  removeFromPlacements(idx); // move from wherever it was (idempotent)
  boardPlacements[row].push(idx);
  refreshUI();
}

function returnCardToHand(idx) {
  removeFromPlacements(idx);
  refreshUI();
}

function removeFromPlacements(idx) {
  ['front', 'middle', 'back'].forEach(row => {
    boardPlacements[row] = boardPlacements[row].filter(i => i !== idx);
  });
}

function getAllPlacedIndices() {
  return new Set([...boardPlacements.front, ...boardPlacements.middle, ...boardPlacements.back]);
}

/* ── Validation / confirm button ────────────────────────────────────────── */
function updateConfirmButton() {
  if (!isActionMode) { $('btn-confirm').disabled = true; return; }

  const totalPlaced = boardPlacements.front.length + boardPlacements.middle.length + boardPlacements.back.length;
  const required    = isInitial ? currentCards.length : currentCards.length - 1;
  $('btn-confirm').disabled = (totalPlaced !== required);

  if (!isInitial) {
    const unplaced = currentCards.length - totalPlaced;
    if (unplaced > 1) {
      setHint(`Place ${required - totalPlaced} more card${required - totalPlaced > 1 ? 's' : ''}.`);
    } else if (unplaced === 1) {
      setHint('The last card will be automatically discarded.');
    } else {
      setHint('');
    }
  } else {
    const unplaced = currentCards.length - totalPlaced;
    setHint(unplaced > 0 ? `Place ${unplaced} more card${unplaced > 1 ? 's' : ''}.` : '');
  }
}

/* ── Game-over screen ───────────────────────────────────────────────────── */
function showGameOver(state) {
  const { scores, is_foul: isFoul, hand_results: results } = state;
  addToGlobalScore(scores.player, scores.ai);
  const playerWon = scores.player > scores.ai;
  const aiWon     = scores.ai > scores.player;

  $('go-title').textContent = playerWon ? '🏆 You Win!' : (scores.player === scores.ai ? "It's a Tie" : 'AI Wins');
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
    const r = results[row]; if (!r) return;
    const pC = r.winner === 'player' ? 'go-winner' : r.winner === 'ai' ? 'go-loser' : 'go-tie';
    const aC = r.winner === 'ai'     ? 'go-winner' : r.winner === 'player' ? 'go-loser' : 'go-tie';
    const label = r.winner === 'player' ? '← You' : r.winner === 'ai' ? 'AI →' : 'Tie';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td style="color:#aaa;text-transform:capitalize">${row}</td>
      <td class="${pC}">${r.player}</td>
      <td class="${pC}">${r.player_bonus > 0 ? '+' + r.player_bonus : '—'}</td>
      <td class="winner-cell">${label}</td>
      <td class="${aC}">${r.ai}</td>
      <td class="${aC}">${r.ai_bonus > 0 ? '+' + r.ai_bonus : '—'}</td>`;
    tbody.appendChild(tr);
  });
  $('game-over').classList.remove('hidden');
}

function hideGameOver() { $('game-over').classList.add('hidden'); }

/* ── UI helpers ─────────────────────────────────────────────────────────── */
function showLoading()  { $('loading').classList.remove('hidden'); }
function hideLoading()  { $('loading').classList.add('hidden'); }
function showActionArea(label) {
  $('action-title').textContent = label;
  $('action-area').classList.remove('hidden');
}
function hideActionArea() { $('action-area').classList.add('hidden'); }
function setStatus(msg) {
  const bar = $('status-bar');
  if (msg) { bar.textContent = msg; bar.classList.remove('hidden'); }
  else     { bar.classList.add('hidden'); }
}
function setHint(msg) { $('placement-hint').textContent = msg || ''; }

/* ── Init ────────────────────────────────────────────────────────────────── */
loadGlobalScore();
