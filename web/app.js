const $ = id => document.getElementById(id);
let currentLedger = null;
const esc = value => String(value ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));

async function applyMode() {
  const demo = $('mode').value === 'demo';
  document.querySelectorAll('.model').forEach(el => el.classList.toggle('hidden', demo));
  document.querySelector('.controls').classList.toggle('demo', demo);
  $('modeNote').classList.toggle('hidden', !demo);
  $('decision').readOnly = demo;
  $('context').readOnly = demo;
  if (demo) {
    try {
      const example = await (await fetch('/api/demo')).json();
      $('decision').value = example.decision;
      $('context').value = example.context;
    } catch (_) { /* server unreachable; the request below will surface the error */ }
  }
}
$('mode').onchange = applyMode;
applyMode();

const titleOf = (ledger, id) => (ledger.challenges.find(c => c.id === id) || {}).title || id;

function render(ledger) {
  currentLedger = ledger;
  $('demoBanner').classList.toggle('hidden', ledger.mode !== 'demo');
  $('decisionText').textContent = ledger.decision;
  $('contextText').textContent = ledger.context || '';

  $('claims').innerHTML = ledger.claims.map(c =>
    `<div><b>${esc(c.id)}</b> ${esc(c.title)} <em class="kind">${esc(c.kind)}</em><small>${esc(c.statement)}</small></div>`).join('');

  $('challenges').innerHTML = ledger.challenges.map(c => `
    <details><summary><span class="pill ${esc(c.materiality.toLowerCase())}">${esc(c.materiality)}</span> <b>${esc(c.id)}</b> ${esc(c.title)} <em class="kind">on ${esc(c.target_claim)}</em></summary>
      <p>${esc(c.argument)}</p><p><b>Resolves if:</b> ${esc(c.resolves_if)}</p>
    </details>`).join('') || '<p class="muted">No challenges raised.</p>';

  $('rounds').textContent = ledger.review_rounds.map(r =>
    `Round ${r.round}: ${r.new_challenges ? `${r.new_challenges} new challenge${r.new_challenges === 1 ? '' : 's'}` : 'nothing new'}`).join(' · ');
  const reason = ledger.termination?.reason || '';
  $('termination').textContent = /no new/i.test(reason)
    ? 'The last round added nothing that would change the gate. More argument will not move it. Only evidence can.'
    : reason;

  const commit = ledger.commitment;
  document.querySelectorAll('#ruleTable tr').forEach(tr => tr.classList.toggle('matched', tr.dataset.rule === commit.matched_rule));
  $('action').textContent = commit.action;
  $('action').className = commit.action.toLowerCase();

  const triggers = commit.triggering_challenges || [];
  $('trigger').innerHTML = triggers.length
    ? `Triggered by ${triggers.map(id => `<b>${esc(id)}</b> ${esc(titleOf(ledger, id))}`).join('; ')}.`
    : 'No unresolved FATAL or BLOCKING challenge.';

  const risks = commit.accepted_risks || [];
  const after = commit.if_triggers_resolved;
  let next = '';
  if (commit.action === 'ACT') {
    next = risks.length
      ? `<b>Accepted risks carried into the action</b>${risks.map(r => `<div>${esc(r)}</div>`).join('')}`
      : '<b>No risks carried.</b> Every challenge was resolved or none was raised.';
  } else {
    const unresolved = ledger.challenges.filter(c => triggers.includes(c.id));
    next = `<b>What changes this</b>${unresolved.map(c => `<div><b>${esc(c.id)}</b> resolves if: ${esc(c.resolves_if)}</div>`).join('')}`;
    if (after) {
      next += `<div class="then">Then the gate returns <b>${esc(after.action)}</b>${after.accepted_risks?.length ? `, carrying ${after.accepted_risks.map(r => `“${esc(r)}”`).join(' and ')} as accepted risk${after.accepted_risks.length === 1 ? '' : 's'}` : ''}.</div>`;
    }
  }
  $('nextAction').innerHTML = next;

  $('download').classList.remove('hidden');
  $('map').classList.remove('hidden');
  $('map').scrollIntoView({behavior:'smooth'});
}

$('download').onclick = () => {
  if (!currentLedger) return;
  const blob = new Blob([JSON.stringify(currentLedger, null, 2)], {type:'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = `${currentLedger.id || 'decision-gate'}.json`; a.click();
  URL.revokeObjectURL(url);
};

$('review').onclick = async () => {
  const decision = $('decision').value.trim();
  if (!decision) return;
  $('error').classList.add('hidden');
  $('review').disabled = true;
  $('review').textContent = 'Reviewing…';
  try {
    const payload = {decision, context:$('context').value, mode:$('mode').value, max_rounds:3};
    if (payload.mode === 'live') {
      payload.builder_model = $('builderModel').value.trim();
      payload.adversary_model = $('adversaryModel').value.trim();
    }
    const res = await fetch('/api/review', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
    const body = await res.json();
    if (!res.ok) throw new Error(body.error || 'Review failed');
    render(body);
  } catch (err) {
    $('error').textContent = err.message;
    $('error').classList.remove('hidden');
  } finally {
    $('review').disabled = false;
    $('review').textContent = 'Run the review';
  }
};
