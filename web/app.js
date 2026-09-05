const $ = id => document.getElementById(id);
let currentLedger = null;
const esc = value => String(value ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));

$('mode').onchange = () => {
  document.querySelectorAll('.model').forEach(el => el.classList.toggle('hidden', $('mode').value !== 'live'));
};

function badge(materiality, count) {
  const cls = materiality.toLowerCase();
  return `<span class="metric ${cls}">${count} ${esc(materiality.replace('_',' '))}</span>`;
}

function render(ledger) {
  currentLedger = ledger;
  $('decisionText').textContent = ledger.decision;
  $('claims').innerHTML = ledger.claims.map(c => `<div><b>${esc(c.id)}</b> ${esc(c.title)}<small>${esc(c.statement)}</small></div>`).join('');

  const counts = {FATAL:0,BLOCKING:0,MATERIAL:0,NON_BLOCKING:0};
  ledger.challenges.forEach(c => counts[c.materiality] = (counts[c.materiality] || 0) + 1);
  $('metrics').innerHTML = Object.entries(counts).filter(([,n]) => n).map(([k,n]) => badge(k,n)).join('') || '<span class="metric clear">No challenges</span>';
  $('rounds').textContent = ledger.review_rounds.map(r => `Round ${r.round}: ${r.new_challenges} new challenge${r.new_challenges===1?'':'s'}`).join(' · ');
  $('challenges').innerHTML = ledger.challenges.map(c => `
    <details><summary><span class="pill ${esc(c.materiality.toLowerCase())}">${esc(c.materiality)}</span> ${esc(c.title)}</summary>
      <p>${esc(c.argument)}</p><p><b>Resolves if:</b> ${esc(c.resolves_if)}</p><p><b>Target:</b> ${esc(c.target_claim)}</p>
    </details>`).join('');

  $('termination').textContent = ledger.termination?.reason || 'Review policy closed the loop.';
  $('action').textContent = ledger.commitment.action;
  $('action').className = ledger.commitment.action.toLowerCase();
  $('actionReason').textContent = (ledger.commitment.reasons || []).join(' ');
  const unresolved = ledger.challenges.filter(c => c.status === 'UNRESOLVED' && ['FATAL','BLOCKING'].includes(c.materiality));
  $('nextAction').innerHTML = unresolved.length
    ? `<b>What to do next</b>${unresolved.map(c => `<div>${esc(c.resolves_if)}</div>`).join('')}`
    : '<b>Review closed.</b> Proceed with the accepted risks recorded above.';
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
    $('review').textContent = 'Challenge My Decision';
  }
};
