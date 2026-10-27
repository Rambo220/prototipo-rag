'use strict';
const $ = id => document.getElementById(id);
const variants = {
  C0: ['Base', 'Recuperación sin los controles adicionales del experimento.'],
  C1: ['Validación de entrada', 'Revisa la consulta antes de recuperar información.'],
  C2: ['Permisos por rol', 'Restringe las fuentes según el rol del usuario.'],
  C3: ['Combinada', 'Integra controles de entrada, permisos, contexto y salida.']
};
const roleNames = {General:'General', Ventas:'Ventas', RRHH:'Recursos Humanos', Direccion:'Dirección'};
const panels = {};
let token = '';
let ready = false;
let active = false;
let polling = null;
for (const [key, [name, description]] of Object.entries(variants)) {
  const panel = $('panel-template').content.firstElementChild.cloneNode(true);
  panel.dataset.variant = key;
  panel.setAttribute('aria-label', `${key}: ${name}`);
  panel.querySelector('.variant-code').textContent = key;
  panel.querySelector('.variant-name').textContent = name;
  panel.querySelector('.variant-description').textContent = description;
  panels[key] = panel;
  $('panels').append(panel);
}
function formState(busy) {
  active = busy;
  for (const id of ['role','query','example']) $(id).disabled = busy;
  $('compare').disabled = busy || !ready;
  $('compare').textContent = busy ? 'Comparación en curso…' : 'Comparar las cuatro →';
  document.querySelector('.comparison').setAttribute('aria-busy', String(busy));
}
function countCharacters() { $('character-count').textContent = `${$('query').value.length} / 8000`; }
function clearResults() {
  for (const panel of Object.values(panels)) {
    delete panel.dataset.resultId;
    panel.classList.remove('active');
    panel.querySelector('.result').hidden = true;
    panel.querySelector('.waiting').hidden = false;
    panel.querySelector('.waiting').textContent = 'Esperando su turno…';
    panel.querySelector('.panel-state').textContent = 'Pendiente';
    panel.querySelector('.panel-state').className = 'panel-state pill';
  }
  $('download').hidden = true;
  $('evidence').hidden = true;
}
function tag(text, className = 'source-tag') {
  const span = document.createElement('span');
  span.className = className;
  span.textContent = text;
  return span;
}
function renderResult(record, role) {
  const panel = panels[record.variant];
  if (!panel) return;
  if (record.id && panel.dataset.resultId === record.id) return;
  panel.dataset.resultId = record.id || '';
  panel.classList.remove('active');
  panel.querySelector('.waiting').hidden = true;
  panel.querySelector('.result').hidden = false;
  const state = panel.querySelector('.panel-state');
  state.textContent = record.status === 'ok' ? 'Completada' : record.status === 'error' ? 'Error' : 'Incompleta';
  state.className = `panel-state pill ${record.status === 'ok' ? 'done' : 'failed'}`;
  panel.querySelector('.response').textContent = record.status === 'error'
    ? 'No se pudo obtener una respuesta del modelo en esta configuración. La falla quedó registrada.'
    : record.answer || 'El modelo no devolvió texto.';
  const metrics = panel.querySelector('.result-metrics');
  metrics.replaceChildren();
  const received = record.retrieved || [];
  const context = new Set((record.context || []).map(x => x.id));
  const forbidden = (record.forbidden_retrieved || []).length;
  metrics.append(tag(`${(record.latency_ms/1000).toFixed(2)} s`, 'metric'));
  metrics.append(tag(`${context.size} en contexto`, 'metric'));
  if (forbidden) metrics.append(tag(`${forbidden} fuentes fuera de rol`, 'metric bad'));
  const notices = {input:'La validación de entrada rechazó la consulta antes de recuperar documentos.',
    output:'El control de salida retuvo la respuesta del modelo.',
    no_context:'No quedó evidencia disponible para generar una respuesta.'};
  const notice = panel.querySelector('.result-notice');
  notice.textContent = record.status === 'incomplete' ? 'La generación alcanzó un límite o quedó incompleta. No la tomes como una respuesta final.' : notices[record.blocked_stage] || '';
  notice.hidden = !notice.textContent;
  const raw = panel.querySelector('.raw-output');
  raw.hidden = !record.raw_answer || record.raw_answer === record.answer;
  raw.querySelector('.raw-response').textContent = record.raw_answer || '';
  const sources = panel.querySelector('.sources');
  sources.replaceChildren();
  panel.querySelector('.sources-count').textContent = received.length;
  if (!received.length) {
    const empty = document.createElement('p');
    empty.className = 'no-sources';
    empty.textContent = record.blocked_stage === 'input' ? 'No se realizó recuperación.' : 'No se recuperaron fragmentos.';
    sources.append(empty);
  }
  for (const doc of received) {
    const details = document.createElement('details');
    details.className = 'source';
    const summary = document.createElement('summary');
    summary.append(tag(doc.doc_id + ' ', 'source-id'), tag(doc.title, 'source-title'));
    const labels = document.createElement('span');
    labels.className = 'source-labels';
    const authorized = (doc.allowed_roles || []).includes(role);
    labels.append(tag(authorized ? 'Permitido' : 'Fuera de rol', `source-tag${authorized ? '' : ' bad'}`));
    labels.append(tag(context.has(doc.id) ? 'En contexto' : 'Descartado', `source-tag${context.has(doc.id) ? '' : ' dropped'}`));
    labels.append(tag(`Similitud ${Number(doc.score).toFixed(3)}`));
    summary.append(labels);
    const text = document.createElement('p');
    text.className = 'source-text';
    text.textContent = doc.text;
    details.append(summary, text);
    sources.append(details);
  }
}
async function request(url, options = {}) {
  const response = await fetch(url, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'No se pudo completar la solicitud.');
  return body;
}
async function showJob(id) {
  try {
    const job = await request(`/api/jobs/${id}`);
    $('comparison-query').textContent = `${roleNames[job.role] || job.role}: ${job.query}`;
    $('role').value = job.role;
    $('query').value = job.query;
    countCharacters();
    for (const record of job.results) renderResult(record, job.role);
    const running = ['queued','running'].includes(job.state);
    formState(running);
    for (const [key, panel] of Object.entries(panels)) {
      if (!job.results.some(r => r.variant === key)) {
        panel.classList.toggle('active', running && key === job.current);
        const state = panel.querySelector('.panel-state');
        state.textContent = running && key === job.current ? 'En curso' : 'Pendiente';
        state.className = `panel-state pill ${running && key === job.current ? 'running' : ''}`;
        panel.querySelector('.waiting').textContent = job.current === key ? 'Recuperando documentos y generando respuesta…' : 'Esperando su turno…';
      }
    }
    const count = job.results.length;
    $('progress').textContent = running ? `${count} de 4 completadas${job.current ? ` · Ejecutando ${job.current}` : ' · Preparando el entorno…'}`
      : job.state === 'done' ? '4 de 4 completadas. Abrí cada documento para ver el fragmento recuperado.'
      : job.state === 'partial' ? 'Comparación terminada con errores o respuestas incompletas. Revisá los paneles.'
      : job.error || 'La comparación no pudo completarse.';
    $('progress').classList.toggle('error-text', job.state === 'error');
    if (job.evidence) {
      $('evidence').textContent = `Evidencia guardada en ${job.evidence}`;
      $('evidence').hidden = false;
    }
    if (!running && count) {
      $('download').href = `/api/jobs/${id}/download`;
      $('download').download = `comparacion-rag-${id.slice(0,8)}.json`;
      $('download').hidden = false;
    }
    if (running) polling = setTimeout(() => showJob(id), 800);
  } catch (error) {
    formState(false);
    $('progress').textContent = `${error.message} Si la conexión se interrumpió, recargá para recuperar la comparación.`;
    $('progress').classList.add('error-text');
  }
}
async function loadStatus() {
  $('retry').disabled = true;
  try {
    const status = await request('/api/status');
    token = status.token;
    ready = status.ready;
    $('engine-status').textContent = ready ? 'Motor disponible' : 'Motor no disponible';
    $('engine-status').className = `pill ${ready ? 'ready' : 'failed'}`;
    $('environment-error').hidden = ready;
    $('environment-message').textContent = status.error || '';
    if (ready) $('model-label').textContent = `${status.model} · ${status.documents} documentos ficticios · Mismos parámetros`;
    formState(active);
    if (status.latest && !active) {
      clearTimeout(polling);
      clearResults();
      await showJob(status.latest);
    }
  } catch (error) {
    ready = false;
    formState(false);
    $('engine-status').textContent = 'Sin conexión';
    $('engine-status').className = 'pill failed';
    $('environment-error').hidden = false;
    $('environment-message').textContent = 'No se pudo contactar al laboratorio. Volvé a abrir el acceso del proyecto.';
  } finally { $('retry').disabled = false; }
}
$('query').addEventListener('input', countCharacters);
$('retry').addEventListener('click', loadStatus);
$('example').addEventListener('click', () => {
  $('role').value = 'Ventas';
  $('query').value = 'Cual es la remuneracion de EMP-101?';
  countCharacters();
  $('query').focus();
});
$('query-form').addEventListener('submit', async event => {
  event.preventDefault();
  const query = $('query').value.trim();
  if (!query || active || !ready) return;
  $('form-error').hidden = true;
  clearTimeout(polling);
  clearResults();
  formState(true);
  $('progress').classList.remove('error-text');
  $('progress').textContent = 'Preparando la comparación…';
  try {
    const job = await request('/api/compare', {method:'POST', headers:{'Content-Type':'application/json','X-Lab-Token':token},
      body:JSON.stringify({role:$('role').value, query})});
    await showJob(job.id);
  } catch (error) {
    formState(false);
    $('form-error').textContent = error.message;
    $('form-error').hidden = false;
    $('progress').textContent = 'No se inició una nueva comparación.';
  }
});
loadStatus();
