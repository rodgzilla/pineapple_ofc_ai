/* ─────────────────────────────────────────────────────────────────────────
   Pineapple OFC – frontend game logic
   ───────────────────────────────────────────────────────────────────────── */
'use strict';

/* ── State ─────────────────────────────────────────────────────────────── */
let gameId       = null;
let currentCards = [];      // [{height, suit}, …] – the cards in the current hand
let assignments  = {};      // card_idx → zone name ('front'|'middle'|'back'|'discard')
let isInitial    = false;

/* ── Card appearance helpers ───────────────────────────────────────────── */
const SUIT_SYMBOL = { d: '♦', c: '♣', s: '♠', h: '♥' };
const SUIT_COLOR  = { d: 'red', c: 'black', s: 'black', h: 'red' };

// Pip positions: [top%, left%, invert(0=up,1=down)] within the pip area
const PIP_LAYOUTS = {
  '2': [[18,50,0],[82,50,1]],
  '3': [[18,50,0],[50,50,0],[82,50,1]],
  '4': [[18,30,0],[18,70,0],[82,30,1],[82,70,1]],
  '5': [[18,30,0],[18,70,0],[50,50,0],[82,30,1],[82,70,1]],
  '6': [[20,30,0],[20,70,0],[50,30,0],[50,70,0],[80,30,1],[80,70,1]],
  '7': [[18,30,0],[18,70,0],[34,50,0],[52,30,0],[52,70,0],[82,30,1],[82,70,1]],
  '8': [[18,30,0],[18,70,0],[34,50,0],[52,30,0],[52,70,0],[66,50,1],[82,30,1],[82,70,1]],
  '9': [[18,30,0],[18,70,0],[35,30,0],[35,70,0],[50,50,0],[65,30,1],[65,70,1],[82,30,1],[82,70,1]],
  'T': [[18,30,0],[18,70,0],[30,50,0],[42,30,0],[42,70,0],[58,30,1],[58,70,1],[70,50,1],[82,30,1],[82,70,1]],
};
const FACE_LABELS = { J: 'J', Q: 'Q', K: 'K' };

/* ── DOM helper ─────────────────────────────────────────────────────────── */
const $ = id => document.getElementById(id);

/* ── API – entry points ─────────────────────────────────────────────────── */
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
  if (!validateAssignments()) return;

  const placements = Object.entries(assignments).map(([idx, row]) => ({
    card_idx: parseInt(idx), row,
  }));

  showLoading();
  $('btn-confirm').disabled = true;
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
    isInitial    = (state.phase === 'init_human');
    currentCards = state.cards;
    assignments  = {};
    buildDragDropUI(currentCards);
    showActionArea(isInitial ? 'Place Your Opening 5 Cards' : 'Place Your Cards');
    setStatus(isInitial
      ? 'Drag your cards into Front, Middle, or Back. Front gets at most 3 cards.'
      : 'Drag 2 cards into a row and 1 card into Discard.');
  } else if (state.phase === 'game_over') {
    hideActionArea();
    showGameOver(state);
    setStatus('Game over!');
  }
}

/* ── Board rendering (already-placed cards) ─────────────────────────────── */
function renderBoard(who, board) {
  ['front', 'middle', 'back'].forEach(row => {
    const max  = row === 'front' ? 3 : 5;
    const el   = $(`${who}-${row}`);
    el.innerHTML = '';
    (board[row] || []).forEach(c => el.appendChild(makeCard(c)));
    for (let i = (board[row] || []).length; i < max; i++) {
      const slot = document.createElement('div');
      slot.className = 'card-slot';
      el.appendChild(slot);
    }
  });
}

/* ── Drag-and-drop UI ───────────────────────────────────────────────────── */
function buildDragDropUI(cards) {
  const area = $('hand-area');
  area.innerHTML = '';

  /* ---- Row drop zones ---- */
  const zonesRow = document.createElement('div');
  zonesRow.className = 'zones-row';

  const rowNames = isInitial ? ['front', 'middle', 'back'] : ['front', 'middle', 'back', 'discard'];
  rowNames.forEach(name => {
    zonesRow.appendChild(makeZone(name));
  });
  area.appendChild(zonesRow);

  /* ---- Unassigned pool ---- */
  const pool = makeZone('pool', 'Your Cards (drag to a row above)');
  area.appendChild(pool);
  cards.forEach((card, idx) => {
    $('zone-pool-cards').appendChild(makeDraggableCard(card, idx));
  });

  updateConfirmButton();
}

function makeZone(name, customLabel) {
  const wrap = document.createElement('div');
  wrap.className = 'drop-zone' + (name === 'discard' ? ' discard-zone' : '') + (name === 'pool' ? ' pool-zone' : '');
  wrap.id = `zone-${name}`;

  const hdr = document.createElement('div');
  hdr.className = 'zone-header';
  const cap = { front: 3, middle: 5, back: 5, discard: 1 }[name];
  hdr.textContent = customLabel || (name.charAt(0).toUpperCase() + name.slice(1));
  if (cap && !customLabel) hdr.textContent += ` (${cap})`;

  const cards = document.createElement('div');
  cards.className = 'zone-cards';
  cards.id = `zone-${name}-cards`;

  wrap.appendChild(hdr);
  wrap.appendChild(cards);

  // Both the wrapper and the cards container are drop targets
  [wrap, cards].forEach(el => {
    el.addEventListener('dragover', e => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      wrap.classList.add('drag-over');
    });
    el.addEventListener('dragleave', e => {
      if (!wrap.contains(e.relatedTarget)) wrap.classList.remove('drag-over');
    });
    el.addEventListener('drop', e => {
      e.preventDefault();
      wrap.classList.remove('drag-over');
      const idx = parseInt(e.dataTransfer.getData('text/plain'));
      if (!isNaN(idx)) moveCard(idx, name);
    });
  });

  return wrap;
}

function makeDraggableCard(c, idx) {
  const el = makeCard(c, true);
  el.dataset.idx = idx;
  el.draggable = true;
  el.addEventListener('dragstart', e => {
    e.dataTransfer.setData('text/plain', String(idx));
    e.dataTransfer.effectAllowed = 'move';
    setTimeout(() => el.classList.add('dragging'), 0);
  });
  el.addEventListener('dragend', () => el.classList.remove('dragging'));
  return el;
}

/* ── Card movement ──────────────────────────────────────────────────────── */
function moveCard(idx, toZone) {
  const cardEl = document.querySelector(`.hand-card[data-idx="${idx}"]`);
  if (!cardEl) return;

  if (toZone === 'pool') {
    delete assignments[idx];
  } else {
    assignments[idx] = toZone;
  }

  const target = $(`zone-${toZone}-cards`);
  if (target) target.appendChild(cardEl);
  updateConfirmButton();
}

/* ── Card DOM builder ───────────────────────────────────────────────────── */
function makeCard(c, isHandCard = false) {
  const symbol = SUIT_SYMBOL[c.suit];
  const color  = SUIT_COLOR[c.suit];
  const rank   = c.height === 'T' ? '10' : c.height;

  const el = document.createElement('div');
  el.className = `card ${color}${isHandCard ? ' hand-card' : ''}`;

  /* Top-left corner */
  const tl = document.createElement('div');
  tl.className = 'corner tl';
  tl.innerHTML = `<span class="rank">${rank}</span><span class="suit-sym">${symbol}</span>`;

  /* Card face */
  const face = document.createElement('div');
  face.className = 'card-face';
  face.appendChild(buildFaceContent(c.height, symbol));

  /* Bottom-right corner (rotated 180°) */
  const br = document.createElement('div');
  br.className = 'corner br';
  br.innerHTML = `<span class="rank">${rank}</span><span class="suit-sym">${symbol}</span>`;

  el.append(tl, face, br);
  return el;
}

function buildFaceContent(height, symbol) {
  /* Ace: one large suit symbol */
  if (height === 'A') {
    const el = document.createElement('div');
    el.className = 'ace-center';
    el.textContent = symbol;
    return el;
  }

  /* Face card: large letter in a thin frame */
  if (height in FACE_LABELS) {
    const el = document.createElement('div');
    el.className = 'face-center';
    el.textContent = FACE_LABELS[height];
    return el;
  }

  /* Number card: pip grid */
  const pips = PIP_LAYOUTS[height] || [];
  const el = document.createElement('div');
  el.className = 'pips';
  pips.forEach(([t, l, inv]) => {
    const pip = document.createElement('span');
    pip.className = 'pip' + (inv ? ' inv' : '');
    pip.style.top  = t + '%';
    pip.style.left = l + '%';
    pip.textContent = symbol;
    el.appendChild(pip);
  });
  return el;
}

/* ── Validation ─────────────────────────────────────────────────────────── */
function validateAssignments() {
  if (Object.keys(assignments).length < currentCards.length) {
    setHint('Place all cards before confirming.');
    return false;
  }
  const counts = {};
  Object.values(assignments).forEach(r => { counts[r] = (counts[r] || 0) + 1; });

  if (isInitial) {
    if ((counts.front || 0) > 3) { setHint('Front takes at most 3 cards.'); return false; }
  } else {
    if ((counts.discard || 0) !== 1) { setHint('Discard exactly 1 card.'); return false; }
  }
  setHint('');
  return true;
}

function updateConfirmButton() {
  const n    = currentCards.length;
  const done = Object.keys(assignments).length === n;
  let valid  = done;

  if (done) {
    const counts = {};
    Object.values(assignments).forEach(r => { counts[r] = (counts[r] || 0) + 1; });
    if (isInitial && (counts.front || 0) > 3) {
      valid = false; setHint('Front takes at most 3 cards.');
    } else if (!isInitial && (counts.discard || 0) !== 1) {
      valid = false; setHint('Discard exactly 1 card.');
    } else {
      setHint('');
    }
  }
  $('btn-confirm').disabled = !valid;
}

/* ── Game-over screen ───────────────────────────────────────────────────── */
function showGameOver(state) {
  const { scores, is_foul: isFoul, hand_results: results } = state;
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
function showLoading()   { $('loading').classList.remove('hidden'); }
function hideLoading()   { $('loading').classList.add('hidden'); }
function showActionArea(t) { $('action-title').textContent = t; $('action-area').classList.remove('hidden'); }
function hideActionArea()  { $('action-area').classList.add('hidden'); }
function setStatus(msg)  {
  const bar = $('status-bar');
  if (msg) { bar.textContent = msg; bar.classList.remove('hidden'); }
  else     { bar.classList.add('hidden'); }
}
function setHint(msg) { $('placement-hint').textContent = msg; }
