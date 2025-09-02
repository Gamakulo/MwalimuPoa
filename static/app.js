const el = (sel) => document.querySelector(sel);
const els = (sel) => Array.from(document.querySelectorAll(sel));

let state = {
  cards: [],
};

function renderCards() {
  const container = el('#cards');
  container.innerHTML = '';
  if (state.cards.length === 0) return;

  state.cards.forEach((c, idx) => {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div class="card-inner">
        <div class="face front"><p>${c.question || '(No question)'}</p></div>
        <div class="face back"><p>${c.answer || 'Think through your answer!'}</p></div>
      </div>
    `;
    card.addEventListener('click', () => card.classList.toggle('flipped'));
    container.appendChild(card);
  });
}

async function generate() {
  const notes = el('#notes').value.trim();
  const num = parseInt(el('#num').value || '5', 10);
  const model = el('#model').value.trim() || undefined;
  if (!notes) { alert('Please paste your notes first.'); return; }

  const btn = el('#generate');
  btn.disabled = true; btn.textContent = 'Generating…';

  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ notes, num_questions: num, model })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to generate');
    state.cards = data.cards || [];
    renderCards();
  } catch (e) {
    alert(e.message);
  } finally {
    btn.disabled = false; btn.textContent = 'Generate';
  }
}

async function saveSet() {
  if (state.cards.length === 0) { alert('Generate some cards first!'); return; }
  const title = el('#set-title').value.trim() || 'My Flashcards';
  const source_text = el('#notes').value.trim();

  const btn = el('#save');
  btn.disabled = true; btn.textContent = 'Saving…';
  try {
    const res = await fetch('/api/save', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ title, cards: state.cards, source_text })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to save');
    await refreshSaved();
    alert('Saved!');
  } catch (e) {
    alert(e.message);
  } finally {
    btn.disabled = false; btn.textContent = 'Save Set';
  }
}

async function refreshSaved() {
  const list = el('#saved-list');
  list.innerHTML = '<li class="muted">Loading…</li>';
  try {
    const res = await fetch('/api/sets');
    const data = await res.json();
    const sets = data.sets || [];
    list.innerHTML = '';
    sets.forEach(s => {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = '#';
      a.textContent = `${s.title} — ${new Date(s.created_at).toLocaleString()}`;
      a.addEventListener('click', async () => {
        const r = await fetch(`/api/sets/${s.id}`);
        const d = await r.json();
        state.cards = d.cards || [];
        renderCards();
      });
      li.appendChild(a);
      list.appendChild(li);
    });
    if (sets.length === 0) list.innerHTML = '<li class="muted">No sets yet.</li>';
  } catch (e) {
    list.innerHTML = '<li class="muted">Failed to load saved sets.</li>';
  }
}

el('#generate').addEventListener('click', generate);
el('#save').addEventListener('click', saveSet);
window.addEventListener('DOMContentLoaded', refreshSaved);
