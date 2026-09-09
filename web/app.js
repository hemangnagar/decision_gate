const $ = id => document.getElementById(id);
let currentLedger = null;
const esc = value => String(value ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
const nice = value => esc(String(value ?? '').replace(/_/g, ' ').toLowerCase());

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

const ORDER = ['FATAL', 'BLOCKING', 'MATERIAL', 'NON_BLOCKING'];
function tally(ledger) {
  const asked = {}, open = {};
  ORDER.forEach(m => { asked[m] = 0; open[m] = 0; });
  let legacy = ledger.challenges.length > 0, capped = 0, byBuilder = 0, byHuman = 0, withdrawn = 0;
  ledger.challenges.forEach(c => {
    if ('requested_materiality' in c) legacy = false;
    const r = c.requested_materiality || c.materiality;
    if (r in asked) asked[r]++;
    if (c.status === 'UNRESOLVED' && c.materiality in open) open[c.materiality]++;
    if (c.materiality_rule === 'MISSING_EVIDENCE_CAPPED') capped++;
    if (c.status === 'RESOLVED') { if (c.resolution?.by === 'HUMAN') byHuman++; else byBuilder++; }
    if (c.status === 'WITHDRAWN') withdrawn++;
  });
  const fmt = o => ORDER.filter(m => o[m]).map(m => `<b>${o[m]}</b> ${esc(m.replace('_', ' '))}`).join(', ') || 'none';
  if (!ledger.challenges.length) return '';
  if (legacy) {
    return `<div><span class="k">Adversary rated</span> ${fmt(asked)}. This ledger predates the materiality rule, so those ratings are what the gate read.</div>`;
  }
  const moves = [];
  if (capped) moves.push(`${capped} capped by rule`);
  if (byBuilder) moves.push(`${byBuilder} resolved by the Builder`);
  if (byHuman) moves.push(`${byHuman} resolved by you`);
  if (withdrawn) moves.push(`${withdrawn} withdrawn`);
  return `<div><span class="k">Adversary asked for</span> ${fmt(asked)}.</div>
    <div><span class="k">Standing after the rule and the answers</span> ${fmt(open)} open${moves.length ? ` <span class="moves">· ${moves.join(' · ')}</span>` : ''}.</div>`;
}

function openLedgerFile(file) {
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const ledger = JSON.parse(reader.result);
      if (!Array.isArray(ledger.claims) || !Array.isArray(ledger.challenges) || !ledger.commitment) {
        throw new Error('Not a Decision Gate ledger: expected claims, challenges, and a commitment.');
      }
      ledger.mode = 'file';
      ledger.source_file = file.name;
      $('error').classList.add('hidden');
      render(ledger);
      $('map').scrollIntoView({behavior: 'smooth'});
    } catch (err) {
      $('error').textContent = `Could not open ${file.name}: ${err.message}`;
      $('error').classList.remove('hidden');
    }
  };
  reader.readAsText(file);
}
$('openLedger').onchange = ev => { if (ev.target.files[0]) openLedgerFile(ev.target.files[0]); ev.target.value = ''; };

function ratingLine(c) {
  if (c.materiality_rule === 'MISSING_EVIDENCE_CAPPED') {
    return `<p class="rule-note"><b>Basis:</b> missing evidence. The Adversary asked for ${esc(c.requested_materiality)}; the rule capped it at ${esc(c.materiality)} because a claim that is merely unproven cannot ${c.materiality === 'MATERIAL' ? 'block' : 'kill'} the decision.</p>`;
  }
  if (c.basis === 'CONTRARY_EVIDENCE') {
    return `<p><b>Basis:</b> contrary evidence. <i>${esc(c.evidence)}</i></p>`;
  }
  if (c.basis === 'MISSING_EVIDENCE') {
    return `<p><b>Basis:</b> missing evidence${c.materiality === 'BLOCKING' ? ', on a DEPENDENCY, so it may block' : ''}.</p>`;
  }
  return '';
}

function answerLine(c) {
  const r = c.rebuttal;
  let out = '';
  if (r) {
    if (r.response === 'RESOLVED') out += `<p class="answer resolved"><b>Builder:</b> resolved by quoting the record: <i>“${esc(r.evidence)}”</i></p>`;
    else if (r.response === 'DISPUTED') out += `<p class="answer"><b>Builder:</b> disputed. ${esc(r.argument)}${r.rejected_evidence ? ` <span class="rule-note">(Claimed to resolve it with “${esc(r.rejected_evidence)}”, which is not in the context. Rejected.)</span>` : ''}</p>`;
    else if (r.response === 'CONCEDED') out += `<p class="answer"><b>Builder:</b> conceded. ${esc(r.argument)}</p>`;
    else out += `<p class="answer muted">Builder did not answer.</p>`;
  }
  if (c.withdrawal) out += `<p class="answer resolved"><b>Adversary:</b> withdrew this challenge. ${esc(c.withdrawal.reason)}</p>`;
  if (c.resolution && c.resolution.by === 'HUMAN') out += `<p class="answer resolved"><b>Resolved by you</b> (${esc(c.resolution.evidence_id)}): <i>${esc(c.resolution.evidence)}</i></p>`;
  return out;
}

function resolveForm(c) {
  if (c.status !== 'UNRESOLVED') return '';
  return `<div class="resolve"><textarea placeholder="Evidence that resolves ${esc(c.id)}. It goes on the record and the gate runs again." data-for="${esc(c.id)}"></textarea><button class="secondary small" data-resolve="${esc(c.id)}">Resolve with evidence</button></div>`;
}

function render(ledger) {
  currentLedger = ledger;
  $('demoBanner').classList.toggle('hidden', ledger.mode !== 'demo');
  $('fileBanner').classList.toggle('hidden', ledger.mode !== 'file');
  if (ledger.mode === 'file') $('fileBanner').textContent = `OPENED FROM FILE — ${ledger.source_file || 'ledger'} (${ledger.id || 'no id'}). Nothing was re-run. Resolving a challenge below posts to the local server and re-gates.`;
  $('decisionText').textContent = ledger.decision;
  $('contextText').textContent = ledger.context || '';

  $('claims').innerHTML = ledger.claims.map(c =>
    `<div><b>${esc(c.id)}</b> ${esc(c.title)} <em class="kind">${esc(c.kind)}</em><small>${esc(c.statement)}</small></div>`).join('');

  $('tally').innerHTML = tally(ledger);
  $('challenges').innerHTML = ledger.challenges.map(c => {
    const status = c.status === 'UNRESOLVED' ? '' : `<span class="status ${esc(c.status.toLowerCase())}">${esc(c.status)}</span>`;
    return `
    <details class="${c.status === 'UNRESOLVED' ? '' : 'closed'}"><summary><span class="pill ${esc(c.materiality.toLowerCase())}">${esc(c.materiality)}</span>${status} <b>${esc(c.id)}</b> ${esc(c.title)} <em class="kind">on ${esc(c.target_claim)}</em></summary>
      <p>${esc(c.argument)}</p>
      ${ratingLine(c)}
      <p><b>Resolves if:</b> ${esc(c.resolves_if)}</p>
      ${answerLine(c)}
      ${resolveForm(c)}
    </details>`;
  }).join('') || '<p class="muted">No challenges raised.</p>';

  $('rounds').textContent = ledger.review_rounds.map(r => {
    if (!r.new_challenges && !r.withdrawn) return `Round ${r.round}: nothing new`;
    const bits = [`${r.new_challenges} new`];
    if (r.capped_by_rule) bits.push(`${r.capped_by_rule} capped by rule`);
    if (r.resolved_by_builder) bits.push(`${r.resolved_by_builder} resolved by the Builder`);
    if (r.withdrawn) bits.push(`${r.withdrawn} withdrawn`);
    return `Round ${r.round}: ${bits.join(', ')}`;
  }).join(' · ');
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

  const history = ledger.commitment_history || [];
  $('history').classList.toggle('hidden', !history.length);
  if (history.length) {
    const last = (ledger.evidence || []).slice(-1)[0];
    $('history').textContent = `Was ${history.map(h => h.action).join(', then ')}. Re-gated after ${last ? `${last.id} resolved ${last.challenge}` : 'new evidence'}.`;
  }

  const risks = commit.accepted_risks || [];
  const after = commit.if_triggers_resolved;
  const retired = ledger.challenges.filter(c => c.status === 'RESOLVED' || c.status === 'WITHDRAWN');
  let next = '';
  if (commit.action === 'ACT') {
    next = risks.length
      ? `<b>Accepted risks carried into the action</b>${risks.map(r => `<div>${esc(r)}</div>`).join('')}`
      : '<b>No risks carried.</b> Every challenge was resolved, withdrawn, or never raised.';
  } else {
    const unresolved = ledger.challenges.filter(c => triggers.includes(c.id));
    next = `<b>What changes this</b>${unresolved.map(c => `<div><b>${esc(c.id)}</b> resolves if: ${esc(c.resolves_if)}</div>`).join('')}`;
    if (after) {
      next += `<div class="then">Then the gate returns <b>${esc(after.action)}</b>${after.accepted_risks?.length ? `, carrying ${after.accepted_risks.map(r => `“${esc(r)}”`).join(' and ')} as accepted risk${after.accepted_risks.length === 1 ? '' : 's'}` : ''}.</div>`;
    }
  }
  if (retired.length) {
    next += `<div class="then muted">Retired on the record: ${retired.map(c => `${esc(c.id)} (${c.status === 'WITHDRAWN' ? 'withdrawn by the Adversary' : c.resolution?.by === 'HUMAN' ? 'resolved by you' : 'resolved by the Builder quoting the context'})`).join(', ')}.</div>`;
  }
  $('nextAction').innerHTML = next;

  $('download').classList.remove('hidden');
  $('map').classList.remove('hidden');
}

$('challenges').addEventListener('click', async ev => {
  const button = ev.target.closest('button[data-resolve]');
  if (!button || !currentLedger) return;
  const id = button.dataset.resolve;
  const evidence = $('challenges').querySelector(`textarea[data-for="${id}"]`).value.trim();
  if (!evidence) return;
  button.disabled = true;
  try {
    const res = await fetch('/api/resolve', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ledger: currentLedger, challenge_id: id, evidence})});
    const body = await res.json();
    if (!res.ok) throw new Error(body.error || 'Resolve failed');
    render(body);
    $('map').querySelector('.action').scrollIntoView({behavior:'smooth'});
  } catch (err) {
    $('error').textContent = err.message;
    $('error').classList.remove('hidden');
    button.disabled = false;
  }
});

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
    $('map').scrollIntoView({behavior:'smooth'});
  } catch (err) {
    $('error').textContent = err.message;
    $('error').classList.remove('hidden');
  } finally {
    $('review').disabled = false;
    $('review').textContent = 'Run the review';
  }
};
