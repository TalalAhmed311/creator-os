/* Web Studio — vanilla JS, no build step.
   Views: #/ (projects) · #/reel/<id> (video editor) · #/carousel/<id> (slide editor)
   Edits go straight into the project's edl.json / carousel.json (autosaved), the same files the agents use. */
'use strict';

// ------------------------------------------------------------------ utils
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const r3 = (v) => Math.round(v * 1000) / 1000;
const fmt = (t) => { t = Math.max(0, t || 0); const m = Math.floor(t / 60); return `${m}:${(t % 60).toFixed(2).padStart(5, '0')}`; };
const media = (id, p, bust) => `/media/${encodeURIComponent(id)}/${p}${bust ? `?v=${bust}` : ''}`;

function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else if (k === 'html') el.innerHTML = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k in el && typeof v !== 'string') el[k] = v;
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const k of kids.flat(9)) if (k != null && k !== false) el.append(k.nodeType ? k : document.createTextNode(k));
  return el;
}

async function api(url, opts = {}) {
  const res = await fetch(url, {
    method: opts.method || 'GET',
    headers: opts.body ? { 'Content-Type': 'application/json' } : {},
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

let toastT;
function toast(msg, bad = false) {
  const t = $('#toast');
  t.textContent = msg;
  t.className = 'on' + (bad ? ' bad' : '');
  clearTimeout(toastT);
  toastT = setTimeout(() => (t.className = ''), bad ? 5000 : 2200);
}

function modal(title, body, buttons) {
  const bg = h('div', { class: 'modal-bg', onclick: (e) => e.target === bg && bg.remove() },
    h('div', { class: 'modal' }, h('h2', {}, title), body, h('div', { class: 'row', style: { marginTop: '16px', justifyContent: 'flex-end' } }, buttons(() => bg.remove()))));
  document.body.append(bg);
  return bg;
}

// ------------------------------------------------------------------ jobs
function trackJob(job, label, onDone) {
  const box = h('div', { class: 'job' }, h('div', { class: 'k' }, h('span', { class: 'spin' }), label), h('div', { class: 's' }, 'starting…'));
  box.onclick = () => modal(label, h('pre', { class: 'log' }, job.log || '…'), (close) => [h('button', { onclick: close }, 'Close')]);
  $('#jobs').append(box);
  const poll = async () => {
    try {
      job = await api(`/api/jobs/${job.id}`);
    } catch { return setTimeout(poll, 1500); }
    const last = (job.log || '').trim().split('\n').pop();
    $('.s', box).textContent = last || 'working…';
    if (job.status === 'running') return setTimeout(poll, 900);
    box.querySelector('.k').innerHTML = `${job.status === 'done' ? '✅' : '❌'} ${esc(label)}`;
    box.onclick = () => modal(label, h('pre', { class: 'log' }, job.log || ''), (close) => [h('button', { onclick: close }, 'Close')]);
    setTimeout(() => box.remove(), job.status === 'done' ? 4000 : 15000);
    if (job.status !== 'done') toast(`${label} failed — click the job card for the log`, true);
    onDone && onDone(job);
  };
  poll();
}

// ------------------------------------------------------------------ router
let cleanup = null;
function route() {
  if (cleanup) { cleanup(); cleanup = null; }
  const [, view, id] = (location.hash || '#/').split('/');
  $('#crumbs').innerHTML = '';
  $('#actions').innerHTML = '';
  $('#app').innerHTML = '';
  if (view === 'reel' && id) return reelEditor(decodeURIComponent(id));
  if (view === 'carousel' && id) return carouselEditor(decodeURIComponent(id));
  projectsView();
}
window.addEventListener('hashchange', route);
window.addEventListener('DOMContentLoaded', route);

// ================================================================== PROJECTS
async function projectsView() {
  const app = $('#app');
  const page = h('div', { class: 'page' },
    h('h1', {}, 'Projects'),
    h('div', { class: 'muted' }, 'Everything in projects/. Open a reel to edit the cut, captions, graphics and audio; open a carousel to edit slides.'),
    h('div', { class: 'toolbar' },
      h('button', { class: 'primary', onclick: importDialog }, '＋ Import footage'),
      h('button', { onclick: newCarouselDialog }, '＋ New carousel'),
      h('button', { class: 'ghost', onclick: route }, '↻ Refresh')),
    h('div', { class: 'grid', id: 'grid' }, h('div', { class: 'muted' }, 'Loading…')));
  app.append(page);
  const rows = await api('/api/projects');
  const grid = $('#grid');
  grid.innerHTML = '';
  if (!rows.length) grid.append(h('div', { class: 'muted' }, 'No projects yet — import some footage or create a carousel.'));
  for (const p of rows) {
    const kind = p.kind === 'carousel' ? 'carousel' : 'reel';
    grid.append(h('a', { class: 'card', href: `#/${kind}/${encodeURIComponent(p.id)}` },
      h('div', { class: 'thumb', style: { backgroundImage: p.thumb ? `url('${media(p.id, p.thumb, Math.round(p.mtime))}')` : 'none' } },
        h('span', { class: 'chip kind' }, kind === 'carousel' ? '▦ carousel' : '▶ reel')),
      h('div', { class: 'body' },
        h('div', { class: 'title' }, p.title || p.id.split('_').slice(1).join(' ')),
        h('div', { class: 'id' }, p.id),
        h('div', { class: 'row' },
          p.pillar && h('span', { class: 'chip' }, p.pillar),
          p.status === 'working' && h('span', { class: 'chip warn' }, 'in progress'),
          p.outputs.length ? h('span', { class: 'chip good' }, p.outputs.includes('final.mp4') || p.outputs.includes('carousel.pdf') ? 'rendered' : 'partial') : null))));
  }
}

function importDialog() {
  const f = { video: h('input', { placeholder: '/Users/you/Movies/clip.mp4', style: { width: '100%' } }),
    audio: h('input', { placeholder: 'optional — separate mic .wav/.m4a', style: { width: '100%' } }),
    slug: h('input', { placeholder: 'day-12-onboarding', style: { width: '100%' } }),
    pillar: h('select', {}, ['build-in-public', 'ai-explained', 'resources'].map((p) => h('option', { value: p }, p))) };
  modal('Import footage', h('div', {},
    h('p', { class: 'muted', style: { marginTop: 0 } }, 'Paste file paths (tip: drag a file from Finder into the box). The studio copies them into a new project and prepares a draft edit: sync → clean audio → transcribe → cut dead air, fillers and retakes.'),
    h('div', { class: 'form-grid' },
      h('label', {}, 'Video'), f.video, h('label', {}, 'Mic audio'), f.audio,
      h('label', {}, 'Pillar'), f.pillar, h('label', {}, 'Name'), f.slug)),
  (close) => [h('button', { onclick: close }, 'Cancel'), h('button', { class: 'primary', onclick: async () => {
    try {
      const job = await api('/api/import', { method: 'POST', body: { video: f.video.value.trim().replace(/^'|'$/g, ''), audio: f.audio.value.trim().replace(/^'|'$/g, ''), slug: f.slug.value.trim(), pillar: f.pillar.value } });
      close();
      trackJob(job, 'Import + auto edit', (j) => { if (j.result?.project) location.hash = `#/reel/${encodeURIComponent(j.result.project)}`; });
    } catch (e) { toast(e.message, true); }
  } }, 'Import & auto-edit')]);
  // Finder drag-and-drop gives a file:// URL in some browsers — normalise it
  for (const inp of [f.video, f.audio]) inp.addEventListener('drop', (e) => {
    const t = e.dataTransfer.getData('text/uri-list') || e.dataTransfer.getData('text/plain');
    if (t) { e.preventDefault(); inp.value = decodeURIComponent(t.replace(/^file:\/\//, '')).trim(); }
  });
}

async function newCarouselDialog() {
  const assets = await api('/api/assets');
  const slug = h('input', { placeholder: 'ai-agents-resources', style: { width: '100%' } });
  const theme = h('select', {}, assets.themes.map((t) => h('option', { value: t }, t)));
  modal('New carousel', h('div', { class: 'form-grid' }, h('label', {}, 'Name'), slug, h('label', {}, 'Theme'), theme),
    (close) => [h('button', { onclick: close }, 'Cancel'), h('button', { class: 'primary', onclick: async () => {
      try {
        const r = await api('/api/new-carousel', { method: 'POST', body: { slug: slug.value || 'resources', theme: theme.value } });
        close();
        location.hash = `#/carousel/${encodeURIComponent(r.project)}`;
      } catch (e) { toast(e.message, true); }
    } }, 'Create')]);
}

// ================================================================== REEL EDITOR
const BEAT_COLORS = { hook: 'var(--beat-hook)', context: 'var(--beat-context)', value: 'var(--beat-value)', payoff: 'var(--beat-payoff)', cta: 'var(--beat-cta)' };
const beatColor = (b) => BEAT_COLORS[b] || (b && b.startsWith('value') ? BEAT_COLORS.value : 'var(--beat-none)');
const EASE = { linear: (t) => t, easeIn: (t) => t * t * t, easeOut: (t) => 1 - (1 - t) ** 3, easeInOut: (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2), snap: (t) => t };
const GFX_TYPES = ['hook_text', 'badge', 'callout', 'diagram', 'series_tag', 'intro_sting', 'lower_third', 'emoji_pop'];

async function reelEditor(id) {
  const d = await api(`/api/projects/${encodeURIComponent(id)}`);
  if (!d.edl) {
    $('#app').append(h('div', { class: 'page' }, h('h1', {}, id), h('p', { class: 'muted' }, 'This project has no edl.json yet. Import footage (or run ./studio edit) to create a draft edit.')));
    return;
  }
  const assets = await api('/api/assets');
  const S = {
    id, d, assets, edl: d.edl, lay: [], t: 0, cur: 0, mode: 'cut', playing: false, selSeg: null, selGfx: null,
    tab: 'segments', view: 'live', hist: [], fut: [], sel: null, version: 0, saveT: null, pxs: 60, raf: 0, overlayKey: '',
    fps: d.edl.output.fps || 30, W: d.edl.output.width || 1080, H: d.edl.output.height || 1920,
  };
  const cam = d.media?.cam || { width: 1080, height: 1920, duration: 0 };
  S.srcDur = cam.duration || Math.max(...d.edl.segments.map((s) => s.out));

  // ---------- layout
  const snap = (t) => Math.round(Math.round(t * S.fps) / S.fps * 1e6) / 1e6;
  function relayout() {
    let cur = 0;
    S.lay = S.edl.segments.map((s, i) => {
      const a = snap(s.in); let b = snap(s.out); if (b <= a) b = a + 1 / S.fps;
      const r = { ...s, i, in: a, out: b, dur: b - a, os: cur, oe: cur + (b - a) }; cur += b - a; return r;
    });
    S.total = cur;
  }
  relayout();
  const segIndexAt = (t) => { for (let i = 0; i < S.lay.length; i++) if (t < S.lay[i].oe - 1e-6) return i; return S.lay.length - 1; };
  const srcToOut = (t) => { for (const s of S.lay) if (s.src === 'cam' && t >= s.in - 1e-6 && t < s.out) return s.os + (t - s.in); return null; };
  const isKept = (w) => srcToOut((w.start + w.end) / 2) != null;

  // ---------- top bar
  $('#crumbs').append(h('a', { href: '#/' }, 'Projects'), '›', h('b', {}, id));
  const saveEl = h('span', { id: 'savestate' }, 'Saved');
  const undoB = h('button', { class: 'ghost', title: 'Undo (⌘Z)', onclick: () => undo() }, '↶');
  const redoB = h('button', { class: 'ghost', title: 'Redo (⇧⌘Z)', onclick: () => redo() }, '↷');
  $('#actions').append(saveEl, undoB, redoB,
    h('button', { title: 'Half-res render with the real renderer + QC report', onclick: () => render('preview') }, '▶ Render preview'),
    h('button', { class: 'primary', onclick: () => render('final') }, '⬆ Render final'),
    h('button', { class: 'ghost', title: 'Show outputs in Finder', onclick: () => api(`/api/projects/${encodeURIComponent(id)}/reveal`, { method: 'POST', body: {} }) }, '📂'));

  // ---------- skeleton
  const video = h('video', { playsInline: true, preload: 'auto' });
  const overlay = h('div', { style: { position: 'absolute', inset: 0 } });
  const stage = h('div', { class: 'stage' }, video, overlay);
  const stageWrap = h('div', { class: 'stage-wrap' }, stage);
  const renderedBox = h('div', { style: { display: 'none', width: '100%' } });
  const scrub = h('input', { type: 'range', class: 'scrub', min: 0, max: 1000, value: 0 });
  const timeEl = h('span', { class: 'time' }, '0:00.00');
  const playB = h('button', { title: 'Play / pause (space)' }, '▶');
  const modeB = h('button', { class: 'small', title: 'Cut = play the edit · Source = play the raw footage' }, 'Cut view');
  const viewTabs = h('div', { class: 'tabs' });
  const playerCol = h('div', { class: 'col' },
    h('div', { class: 'col-head' }, h('h3', {}, 'Preview'), h('span', { class: 'grow' }), viewTabs),
    h('div', { class: 'scroll' }, h('div', { class: 'player' }, stageWrap, renderedBox,
      h('div', { class: 'transport' }, playB, scrub, timeEl), h('div', { class: 'row', style: { width: '100%' } }, modeB,
        h('span', { class: 'muted', style: { fontSize: '12px' } }, 'Live preview approximates the render — use ▶ Render preview for the exact result.')))));
  const selbar = h('div', { class: 'col-head selbar' });
  const transcriptEl = h('div', { class: 'transcript' });
  const midCol = h('div', { class: 'col' }, h('div', { class: 'col-head' }, h('h3', {}, 'Transcript'),
    h('span', { class: 'muted', style: { fontSize: '12px' } }, d.transcriber ? `· ${d.transcriber}` : '')), selbar, h('div', { class: 'scroll' }, transcriptEl));
  const inspTabs = h('div', { class: 'tabs' });
  const inspBody = h('div', { class: 'scroll inspector' });
  const rightCol = h('div', { class: 'col' }, h('div', { class: 'col-head' }, inspTabs), inspBody);
  const tlBody = h('div', { class: 'tl-body' });
  const zoomIn = h('input', { type: 'range', min: 10, max: 400, value: 60, style: { width: '140px' } });
  const timeline = h('div', { class: 'timeline' },
    h('div', { class: 'tl-head' }, h('b', { style: { fontSize: '12px' } }, 'Timeline'),
      h('span', { class: 'muted', style: { fontSize: '12px' } }, 'drag segment edges to trim · click to select · '), h('kbd', {}, 'S'), h('span', { class: 'muted', style: { fontSize: '12px' } }, 'split at playhead'),
      h('span', { class: 'grow' }), h('label', {}, 'zoom'), zoomIn),
    tlBody);
  const editor = h('div', { class: 'editor' }, playerCol, midCol, rightCol, timeline);
  $('#app').append(editor);

  // stage scale: fit 9:16 into the column
  function fitStage() {
    const w = Math.min(playerCol.clientWidth - 24, (window.innerHeight - 52 - 210 - 140) * 9 / 16);
    const k = Math.max(0.12, w / S.W);
    stage.style.transform = `scale(${k})`;
    stageWrap.style.width = `${S.W * k}px`; stageWrap.style.height = `${S.H * k}px`;
  }
  const ro = new ResizeObserver(fitStage); ro.observe(playerCol);

  // video source: proxy if ready (small H.264 + cleaned voice), else the camera file
  function setVideoSrc() {
    const p = S.d.proxy || S.d.media?.cam?.path;
    if (p) video.src = media(id, p);
  }
  setVideoSrc();
  if (!d.proxy) {
    const pj = (d.jobs || []).find((j) => j.kind === 'proxy');
    if (pj) trackJob(pj, 'Preparing preview proxy', async () => { S.d = await api(`/api/projects/${encodeURIComponent(id)}`); const t = S.t; setVideoSrc(); video.addEventListener('loadedmetadata', () => seek(t), { once: true }); renderTimeline(); });
  }

  // ================================================================ history + save
  const snapshot = () => { S.hist.push(JSON.stringify(S.edl)); if (S.hist.length > 150) S.hist.shift(); S.fut = []; updUndo(); };
  function updUndo() { undoB.disabled = !S.hist.length; redoB.disabled = !S.fut.length; }
  function undo() { if (!S.hist.length) return; S.fut.push(JSON.stringify(S.edl)); S.edl = JSON.parse(S.hist.pop()); changed(); updUndo(); }
  function redo() { if (!S.fut.length) return; S.hist.push(JSON.stringify(S.edl)); S.edl = JSON.parse(S.fut.pop()); changed(); updUndo(); }
  updUndo();
  function changed(opts = {}) {
    relayout();
    S.t = clamp(S.t, 0, S.total);
    if (!opts.keepInspector) renderInspector();
    renderTranscript(); renderTimeline(); S.overlayKey = '';
    scheduleSave();
  }
  function scheduleSave() {
    S.version++; saveEl.textContent = 'Unsaved'; clearTimeout(S.saveT); S.saveT = setTimeout(saveNow, 600);
  }
  async function saveNow() {
    const v = S.version; saveEl.textContent = 'Saving…';
    try {
      const r = await api(`/api/projects/${encodeURIComponent(id)}/edl?refresh=1`, { method: 'PUT', body: S.edl });
      if (v === S.version) {
        S.edl = r.edl; relayout();
        if (!inspBody.contains(document.activeElement)) renderInspector();
        renderTimeline(); S.overlayKey = '';
      }
      saveEl.textContent = r.warnings?.length ? '⚠ saved' : 'Saved';
      saveEl.title = (r.warnings || []).join('\n');
    } catch (e) { saveEl.textContent = 'Not saved'; toast(e.message, true); }
  }
  async function flushSave() { if (saveEl.textContent !== 'Saved') { clearTimeout(S.saveT); await saveNow(); } }

  async function render(mode) {
    await flushSave();
    try {
      const job = await api(`/api/projects/${encodeURIComponent(id)}/render`, { method: 'POST', body: { mode } });
      trackJob(job, mode === 'final' ? 'Final render (+ cover, fcpxml)' : 'Preview render + QC', async (j) => {
        if (j.status !== 'done') return;
        S.d = await api(`/api/projects/${encodeURIComponent(id)}`);
        S.view = mode === 'final' ? 'final' : 'preview'; S.bust = Date.now();
        renderViewTabs(); showView(); if (S.tab === 'info') renderInspector();
        toast(mode === 'final' ? 'Final render ready — out/final.mp4' : 'Preview ready');
      });
    } catch (e) { toast(e.message, true); }
  }

  // ================================================================ player
  function seek(t) {
    S.t = clamp(t, 0, Math.max(0, S.total - 0.001));
    if (S.mode === 'cut') {
      S.cur = segIndexAt(S.t);
      const s = S.lay[S.cur];
      if (s) video.currentTime = s.in + (S.t - s.os);
    }
    S.overlayKey = '';
  }
  function play() {
    if (S.mode === 'cut') { if (S.t >= S.total - 0.05) seek(0); else seek(S.t); }
    video.play().catch(() => {}); S.playing = true; playB.textContent = '❚❚';
  }
  function pause() { video.pause(); S.playing = false; playB.textContent = '▶'; }
  playB.onclick = () => (S.playing ? pause() : play());
  modeB.onclick = () => {
    pause();
    if (S.mode === 'cut') { const s = S.lay[segIndexAt(S.t)]; S.mode = 'source'; modeB.textContent = 'Source view'; if (s) video.currentTime = s.in + (S.t - s.os); }
    else { S.mode = 'cut'; modeB.textContent = 'Cut view'; const o = srcToOut(video.currentTime); seek(o ?? S.t); }
    modeB.classList.toggle('primary', S.mode === 'source'); S.overlayKey = '';
  };
  scrub.oninput = () => {
    const f = scrub.value / 1000;
    if (S.mode === 'cut') seek(f * S.total); else video.currentTime = f * S.srcDur;
  };
  video.addEventListener('loadedmetadata', () => seek(S.t));

  function tick() {
    if (S.mode === 'cut' && S.playing) {
      let s = S.lay[S.cur];
      if (!s) pause();
      else if (video.currentTime >= s.out - 0.012) {
        const n = S.lay[S.cur + 1];
        if (!n) { pause(); S.t = s.oe; }
        else { S.cur++; if (Math.abs(n.in - video.currentTime) > 0.04) video.currentTime = n.in; }
      }
      s = S.lay[S.cur];
      if (s && S.playing) S.t = s.os + clamp(video.currentTime - s.in, 0, s.dur);
    }
    const pos = S.mode === 'cut' ? S.t / (S.total || 1) : video.currentTime / (S.srcDur || 1);
    if (document.activeElement !== scrub) scrub.value = Math.round(pos * 1000);
    timeEl.textContent = S.mode === 'cut' ? `${fmt(S.t)} / ${fmt(S.total)}` : `src ${fmt(video.currentTime)}`;
    drawStage(); movePlayhead(); markTranscript();
    S.raf = requestAnimationFrame(tick);
  }

  // ---------- stage drawing (mirrors harnesses/studio/remotion/src/Reel.tsx)
  const cropPts = d.crop?.points || [];
  function cropAt(t) {
    if (!cropPts.length) return { cx: 0.5, cy: 0.42 };
    if (t <= cropPts[0].t) return cropPts[0];
    const last = cropPts[cropPts.length - 1]; if (t >= last.t) return last;
    let i = 0; while (i < cropPts.length - 2 && cropPts[i + 1].t < t) i++;
    const a = cropPts[i], b = cropPts[i + 1], k = (t - a.t) / Math.max(1e-6, b.t - a.t);
    return { cx: a.cx + (b.cx - a.cx) * k, cy: a.cy + (b.cy - a.cy) * k };
  }
  function drawStage() {
    const W = S.W, H = S.H, cover = Math.max(W / cam.width, H / cam.height);
    let zoom = 1, cx = 0.5, cy = 0.42, seg = null;
    if (S.mode === 'cut') {
      seg = S.lay[S.cur];
      if (seg) {
        const p = clamp((S.t - seg.os) / (seg.dur || 1), 0, 1);
        if (seg.zoom) zoom = seg.zoom.from + (seg.zoom.to - seg.zoom.from) * (EASE[seg.zoom.ease] || EASE.linear)(p);
        if ((seg.reframe || 'face_track') === 'face_track') ({ cx, cy } = cropAt(seg.in + (S.t - seg.os)));
      }
    }
    const vw = cam.width * cover * zoom, vh = cam.height * cover * zoom;
    Object.assign(video.style, { width: `${vw}px`, height: `${vh}px`, left: `${clamp(W / 2 - cx * vw, W - vw, 0)}px`, top: `${clamp(H * 0.4 - cy * vh, H - vh, 0)}px` });
    // overlays: rebuild only when what's visible changes
    const t = S.t;
    if (S.mode === 'source') {
      if (S.overlayKey !== 'src') { overlay.innerHTML = '<div class="src-badge">SOURCE</div>'; S.overlayKey = 'src'; }
      return;
    }
    const gfx = S.edl.graphics.map((g, i) => ({ ...g, i })).filter((g) => t >= g.start && t < g.end);
    const chunk = captionChunk(t);
    const active = chunk ? chunk.words.findIndex((w) => t >= w.start && t < w.end + 0.05) : -1;
    const broll = seg?.overlay_broll ? `${seg.i}` : '';
    const key = JSON.stringify([gfx.map((g) => g.i), chunk?.start, active, broll, S.edl.captions.style, S.edl.captions.size]);
    if (key === S.overlayKey) return;
    S.overlayKey = key;
    overlay.innerHTML = (seg?.overlay_broll ? brollHtml(seg) : '') + gfx.map(gfxHtml).join('') + (chunk && S.edl.captions.enabled !== false ? captionHtml(chunk, active) : '');
  }
  function brollHtml(seg) {
    const b = seg.overlay_broll, mode = b.mode || 'full';
    const st = mode === 'split_top' ? 'left:0;top:0;width:1080px;height:960px' : mode === 'pip' ? 'top:269px;right:40px;width:454px;height:807px;border-radius:28px' : 'inset:0;width:1080px;height:1920px';
    return `<div style="position:absolute;${st};background:#223 linear-gradient(135deg,#334,#112);display:flex;align-items:center;justify-content:center;color:#aab;font:700 40px Inter;border:4px dashed #556">B-ROLL<br>${esc(b.file.split('/').pop())}</div>`;
  }

  // captions (mirrors harnesses/studio/remotion/src/Captions.tsx)
  const CAP = { 'bip-raw': { size: 88, upper: true, font: 'Montserrat', weight: 900, stroke: 14 }, 'ai-explained': { size: 70, upper: false, font: 'Inter', weight: 800, stroke: 0 }, 'talking-head-basic': { size: 76, upper: false, font: 'Inter', weight: 800, stroke: 10 } };
  function chunkWords(words, maxWords) {
    const chunks = []; let cur = [];
    const push = () => { if (cur.length) chunks.push({ words: cur, start: cur[0].start, end: cur[cur.length - 1].end }); cur = []; };
    words.forEach((w, i) => { const p = words[i - 1]; if (cur.length && (cur.length >= maxWords || (p && w.start - p.end > 0.3))) push(); cur.push(w); if (/[.!?]$/.test(w.text)) push(); });
    push();
    chunks.forEach((c, i) => { const n = chunks[i + 1]; if (n && n.start - c.end < 0.4) c.end = n.start; else c.end += 0.15; });
    return chunks;
  }
  let chunkCache = { key: '', chunks: [] };
  function captionChunk(t) {
    const c = S.edl.captions, key = `${S.version}:${c.max_words}:${c.words.length}`;
    if (chunkCache.key !== key) chunkCache = { key, chunks: chunkWords(c.words, c.max_words || 3) };
    return chunkCache.chunks.find((ch) => t >= ch.start && t < ch.end);
  }
  const cleanWord = (s) => s.replace(/^[^\w$€£#@"'(]+/, '').replace(/[,.;:…]+$/, '');
  function captionHtml(chunk, active) {
    const style = S.edl.captions.style || 'bip-raw', c = CAP[style], fs = c.size * (S.edl.captions.size || 1);
    const accent = 'var(--accent2)';
    const words = chunk.words.map((w, i) => {
      const txt = c.upper ? cleanWord(w.text).toUpperCase() : cleanWord(w.text);
      const stroke = c.stroke ? `-webkit-text-stroke:${c.stroke}px #000;paint-order:stroke fill;` : 'text-shadow:0 3px 12px rgba(0,0,0,.6);';
      const scale = style === 'bip-raw' && i === active ? 'transform:scale(1.08);' : '';
      return `<span style="display:inline-block;color:${w.highlight ? accent : '#fff'};${stroke}${scale}">${esc(txt)}</span>`;
    }).join('');
    const pill = style === 'ai-explained' ? 'background:rgba(0,0,0,.55);padding:14px 26px;border-radius:20px;' : '';
    return `<div style="position:absolute;left:60px;right:60px;top:${S.H * 0.6}px;display:flex;justify-content:center">
      <div style="display:flex;flex-wrap:wrap;justify-content:center;column-gap:${fs * 0.34 + c.stroke}px;max-width:960px;text-align:center;font-family:${c.font};font-weight:${c.weight};font-size:${fs}px;line-height:1.08;${pill}">${words}</div></div>`;
  }

  // graphics (simplified mirrors of harnesses/studio/remotion/src/Graphics.tsx)
  function parseDiagram(spec) {
    const order = [], edges = [];
    (spec || '').split(/[;\n]+/).forEach((chain) => {
      const nodes = chain.split(/\s*-(?:\[[^\]]*\])?>\s*/).map((s) => s.trim()).filter(Boolean);
      nodes.forEach((n) => !order.includes(n) && order.push(n));
      for (let i = 0; i + 1 < nodes.length; i++) edges.push([nodes[i], nodes[i + 1]]);
    });
    const lvl = Object.fromEntries(order.map((n) => [n, 0]));
    for (let k = 0; k < order.length; k++) edges.forEach(([a, b]) => (lvl[b] = Math.max(lvl[b], lvl[a] + 1)));
    const rows = [];
    order.forEach((n) => (rows[lvl[n]] ||= []).push(n));
    return rows;
  }
  function gfxHtml(g) {
    const TOP = S.H * 0.13, heavy = S.edl.captions.style === 'bip-raw';
    const T = esc(g.text || '');
    switch (g.type) {
      case 'hook_text': return `<div style="position:absolute;top:${S.H * 0.195}px;left:50px;right:50px;display:flex;justify-content:center"><div style="background:${heavy ? 'var(--accent2)' : 'rgba(255,255,255,.95)'};color:#111;font:900 70px/1.1 ${heavy ? 'Montserrat' : 'Inter'};padding:20px 34px;border-radius:22px;text-align:center;${heavy ? 'text-transform:uppercase;' : ''}">${T}</div></div>`;
      case 'badge': return `<div style="position:absolute;top:${TOP}px;left:44px;background:var(--accent);color:#fff;font:900 44px Montserrat;padding:10px 24px;border-radius:99px">${T}</div>`;
      case 'series_tag': return `<div style="position:absolute;top:${TOP}px;right:44px;background:rgba(0,0,0,.6);color:#fff;font:900 44px Montserrat;padding:10px 24px;border-radius:99px;border:3px solid var(--accent2)">${T}</div>`;
      case 'callout': return `<div style="position:absolute;top:${S.H * 0.21}px;left:0;right:0;display:flex;justify-content:center"><div style="background:var(--accent);color:#fff;font:900 58px Montserrat;padding:16px 30px;border-radius:18px;transform:rotate(-2deg);box-shadow:8px 8px 0 var(--accent2);max-width:940px;text-align:center">${T}</div></div>`;
      case 'lower_third': return `<div style="position:absolute;bottom:${S.H * 0.24}px;left:50px;background:rgba(0,0,0,.72);border-left:10px solid var(--accent2);color:#fff;font:700 44px Inter;padding:14px 26px">${T}</div>`;
      case 'emoji_pop': return `<div style="position:absolute;top:${S.H * 0.3}px;left:${S.W * 0.66}px;font-size:150px">${T}</div>`;
      case 'intro_sting': { const [a, ep] = (g.text || 'AI Explained').split('#'); return `<div style="position:absolute;inset:0;background:var(--accent);display:flex;flex-direction:column;align-items:center;justify-content:center;color:#fff;font:900 110px Montserrat;text-align:center">${esc(a.trim())}${ep ? `<div style="font:700 80px 'JetBrains Mono';color:var(--accent2);margin-top:20px">#${esc(ep.trim())}</div>` : ''}</div>`; }
      case 'diagram': {
        const rows = parseDiagram(g.spec || g.text);
        const boxes = rows.map((r) => `<div style="display:flex;gap:30px;justify-content:center">${r.map((n) => `<div style="background:#fff;color:#0b0b12;border:5px solid var(--accent);border-radius:20px;font:800 44px Inter;padding:18px 30px;box-shadow:6px 6px 0 var(--accent2)">${esc(n)}</div>`).join('')}</div>`).join('<div style="text-align:center;color:var(--accent2);font-size:60px;line-height:1">↓</div>');
        return `<div style="position:absolute;left:40px;right:40px;top:${TOP - 20}px;height:${S.H * 0.4 + 40}px;background:rgba(8,10,20,.82);border:2px solid var(--accent);border-radius:36px;display:flex;flex-direction:column;justify-content:center;gap:10px">${boxes}</div>`;
      }
      default: return '';
    }
  }

  // ================================================================ transcript (text-based editing)
  const fillerIdx = new Set((d.fillers || []).map((f) => f.i));
  function renderTranscript() {
    const words = d.words || [];
    transcriptEl.innerHTML = '';
    if (!words.length) {
      transcriptEl.append(h('div', { class: 'empty' },
        h('p', {}, 'No transcript for this project (transcriber: ', h('b', {}, d.transcriber || 'none'), ').'),
        h('p', {}, 'You can still edit on the timeline. For word-level editing and captions: install transcription (', h('code', {}, 'scripts/setup.sh --with transcribe'), ') or drop ', h('code', {}, 'raw/transcript.srt'), ' into the project, then re-run ', h('code', {}, `./studio edit ${id}`), '.')));
      return;
    }
    const frag = document.createDocumentFragment();
    let lastBeat;
    words.forEach((w, i) => {
      const prev = words[i - 1];
      if (prev && w.start - prev.end > 0.5) frag.append(h('span', { class: 'gap' }, `${(w.start - prev.end).toFixed(1)}s`));
      const o = srcToOut((w.start + w.end) / 2);
      if (o != null) {
        const beat = S.lay[segIndexAt(o)]?.beat;
        if (beat && beat !== lastBeat) frag.append(h('span', { class: 'beat', style: { background: beatColor(beat) } }, beat));
        lastBeat = beat;
      }
      frag.append(h('span', { class: 'w' + (o == null ? ' cut' : '') + (fillerIdx.has(i) ? ' filler' : ''), 'data-i': i, title: `${w.start.toFixed(2)}s${fillerIdx.has(i) ? ' · marked as filler/retake' : ''}` }, w.text), ' ');
    });
    transcriptEl.append(frag);
    S.nowWord = null;
  }
  function markTranscript() {
    const words = d.words || []; if (!words.length) return;
    const src = S.mode === 'cut' ? (S.lay[S.cur] ? S.lay[S.cur].in + (S.t - S.lay[S.cur].os) : 0) : video.currentTime;
    let lo = 0, hi = words.length - 1, idx = -1;
    while (lo <= hi) { const m = (lo + hi) >> 1; if (words[m].start <= src) { idx = m; lo = m + 1; } else hi = m - 1; }
    if (idx >= 0 && src > words[idx].end + 0.3) idx = -1;
    if (idx === S.nowWord) return;
    transcriptEl.querySelector('.w.now')?.classList.remove('now');
    S.nowWord = idx;
    if (idx >= 0) {
      const el = transcriptEl.querySelector(`.w[data-i="${idx}"]`);
      if (el) { el.classList.add('now'); if (S.playing) el.scrollIntoView({ block: 'nearest' }); }
    }
  }
  transcriptEl.addEventListener('click', (e) => {
    const w = e.target.closest('.w'); if (!w || !window.getSelection().isCollapsed) return;
    const word = d.words[+w.dataset.i];
    const o = srcToOut((word.start + word.end) / 2);
    if (o != null) { if (S.mode !== 'cut') modeB.click(); seek(o - ((word.start + word.end) / 2 - word.start)); }
    else { if (S.mode !== 'source') modeB.click(); video.currentTime = word.start; }
  });
  function readSelection() {
    const sel = window.getSelection();
    if (sel.isCollapsed || !transcriptEl.contains(sel.anchorNode)) { S.sel = null; return renderSelbar(); }
    const node = (n) => (n.nodeType === 3 ? n.parentElement : n);
    let a = node(sel.anchorNode).closest?.('.w'), b = node(sel.focusNode).closest?.('.w');
    const all = [...transcriptEl.querySelectorAll('.w')].filter((el) => sel.containsNode(el, true));
    if (!all.length) { S.sel = null; return renderSelbar(); }
    a = all[0]; b = all[all.length - 1];
    S.sel = [+a.dataset.i, +b.dataset.i].sort((x, y) => x - y);
    renderSelbar();
  }
  document.addEventListener('selectionchange', readSelection);
  function renderSelbar() {
    selbar.innerHTML = '';
    if (!S.sel) {
      selbar.append(h('span', { class: 'muted', style: { fontSize: '12px' } }, 'Select words to cut or restore them · click a word to jump there · ', h('span', { style: { textDecoration: 'line-through' } }, 'struck'), ' = cut, red = filler/retake'));
      return;
    }
    const [i0, i1] = S.sel, n = i1 - i0 + 1;
    selbar.append(h('b', { style: { fontSize: '12px' } }, `${n} word${n > 1 ? 's' : ''} selected`),
      h('button', { class: 'small danger', onclick: () => cutWords(i0, i1) }, '✂ Cut  ⌫'),
      h('button', { class: 'small', onclick: () => restoreWords(i0, i1) }, '↺ Restore  R'));
  }
  renderSelbar();

  function wordBounds(i0, i1, pad) {
    const ws = d.words, a = ws[i0], b = ws[i1], p = ws[i0 - 1], n = ws[i1 + 1];
    return [Math.max(p ? (p.end + a.start) / 2 : 0, a.start - pad), Math.min(n ? (b.end + n.start) / 2 : S.srcDur, b.end + pad)];
  }
  function cutWords(i0, i1) {
    const [a, b] = wordBounds(i0, i1, 0.02);
    snapshot();
    const out = [];
    for (const s of S.edl.segments) {
      if (s.src !== 'cam' || s.out <= a || s.in >= b) { out.push(s); continue; }
      if (s.in < a) out.push({ ...s, out: r3(a) });
      if (s.out > b) out.push({ ...s, in: r3(b), beat: s.beat });
    }
    S.edl.segments = out.filter((s) => s.out - s.in >= 0.08);
    if (!S.edl.segments.length) { S.edl = JSON.parse(S.hist.pop()); return toast('Can’t cut everything', true); }
    window.getSelection().removeAllRanges(); changed(); toast(`Cut ${i1 - i0 + 1} words`);
  }
  function restoreWords(i0, i1) {
    const [a, b] = wordBounds(i0, i1, 0.08);
    snapshot();
    const segs = S.edl.segments.slice();
    let pos = segs.findIndex((s) => s.src === 'cam' && s.in > a);
    if (pos < 0) pos = segs.length;
    const near = segs[pos - 1] || segs[pos];
    segs.splice(pos, 0, { src: 'cam', in: r3(a), out: r3(b), beat: near?.beat ?? null, reframe: 'face_track', zoom: near?.zoom ? { ...near.zoom } : null, overlay_broll: null });
    // merge neighbours that now overlap/touch in source time
    const merged = [];
    for (const s of segs) {
      const p = merged[merged.length - 1];
      if (p && p.src === s.src && s.in <= p.out + 0.05 && s.in >= p.in - 0.001) p.out = Math.max(p.out, s.out);
      else merged.push({ ...s });
    }
    S.edl.segments = merged;
    window.getSelection().removeAllRanges(); changed(); toast(`Restored ${i1 - i0 + 1} words`);
  }
  function splitAtPlayhead() {
    const i = segIndexAt(S.t), s = S.lay[i]; if (!s) return;
    const at = r3(s.in + (S.t - s.os)); if (at - s.in < 0.1 || s.out - at < 0.1) return toast('Too close to an edge to split');
    snapshot();
    const orig = S.edl.segments[i];
    S.edl.segments.splice(i, 1, { ...orig, out: at }, { ...orig, in: at, zoom: orig.zoom ? { ...orig.zoom } : null });
    S.selSeg = i + 1; changed(); toast('Split');
  }

  // ================================================================ timeline
  function renderTimeline() {
    const pxs = S.pxs, W = Math.max(tlBody.clientWidth, S.total * pxs + 80);
    const inner = h('div', { class: 'tl-inner', style: { width: `${W}px` } });
    // ruler
    const ruler = h('div', { class: 'ruler', onmousedown: (e) => { const r = inner.getBoundingClientRect(); if (S.mode !== 'cut') modeB.click(); seek((e.clientX - r.left) / pxs); } });
    const step = pxs > 120 ? 0.5 : pxs > 40 ? 1 : pxs > 15 ? 5 : 10;
    for (let t = 0; t <= S.total + step; t += step) { ruler.append(h('i', { style: { left: `${t * pxs}px` } })); if (Math.abs(t - Math.round(t)) < 1e-6) ruler.append(h('span', { style: { left: `${t * pxs}px` } }, `${Math.round(t)}s`)); }
    inner.append(ruler);
    // segments
    const wave = S.d.waveform ? media(id, S.d.waveform) : null;
    S.lay.forEach((s, i) => {
      const el = h('div', { class: 'seg' + (S.selSeg === i ? ' sel' : ''), style: { left: `${s.os * pxs}px`, width: `${Math.max(3, s.dur * pxs - 1)}px`, background: beatColor(s.beat) },
        title: `#${i + 1} ${s.beat || ''}  src ${s.in.toFixed(2)}–${s.out.toFixed(2)}s (${s.dur.toFixed(2)}s)`,
        onmousedown: (e) => { if (e.target.classList.contains('h')) return; S.selSeg = i; S.tab = 'segments'; if (S.mode !== 'cut') modeB.click(); const r = inner.getBoundingClientRect(); seek((e.clientX - r.left) / pxs); renderInspector(); renderTimeline(); } },
      h('div', { class: 'lbl' }, `${s.beat || '—'}${s.zoom && Math.max(s.zoom.from, s.zoom.to) > 1.01 ? ` · ${Math.max(s.zoom.from, s.zoom.to).toFixed(2)}×` : ''}${s.overlay_broll ? ' · b-roll' : ''}`),
      wave && h('div', { class: 'wave', style: { backgroundImage: `url('${wave}')`, backgroundSize: `${S.srcDur * pxs}px 32px`, backgroundPosition: `${-s.in * pxs}px 0` } }),
      h('div', { class: 'h l', onmousedown: (e) => dragEdge(e, i, 'in') }),
      h('div', { class: 'h r', onmousedown: (e) => dragEdge(e, i, 'out') }));
      inner.append(el);
    });
    // graphics rows (stacked when they overlap)
    const rows = [];
    S.edl.graphics.map((g, i) => ({ ...g, i })).sort((a, b) => a.start - b.start).forEach((g) => {
      let r = rows.findIndex((end) => end <= g.start + 1e-6); if (r < 0) { r = rows.length; rows.push(0); } rows[r] = g.end;
      inner.append(h('div', { class: 'gfx' + (S.selGfx === g.i ? ' sel' : ''), style: { left: `${g.start * pxs}px`, width: `${Math.max(8, (g.end - g.start) * pxs - 1)}px`, top: `${84 + Math.min(r, 2) * 22}px` },
        title: `${g.type}: ${g.text || g.spec || ''}`, onmousedown: () => { S.selGfx = g.i; S.tab = 'graphics'; seek(g.start); renderInspector(); renderTimeline(); } }, `${g.type.replace('_', ' ')} · ${g.text || g.spec || ''}`));
    });
    // caption chunks
    if (S.edl.captions.enabled !== false) chunkWords(S.edl.captions.words, S.edl.captions.max_words || 3).forEach((c) => {
      inner.append(h('div', { class: 'capblk', style: { left: `${c.start * pxs}px`, width: `${Math.max(4, (c.end - c.start) * pxs - 1)}px`, top: '154px' } }, c.words.map((w) => w.text).join(' ')));
    });
    S.playheadEl = h('div', { class: 'playhead' });
    inner.append(S.playheadEl);
    const sl = tlBody.scrollLeft; tlBody.innerHTML = ''; tlBody.append(inner); tlBody.scrollLeft = sl;
    S.tlInner = inner;
  }
  function movePlayhead() {
    if (!S.playheadEl) return;
    const x = (S.mode === 'cut' ? S.t : srcToOut(video.currentTime) ?? S.t) * S.pxs;
    S.playheadEl.style.left = `${x}px`;
    if (S.playing && (x > tlBody.scrollLeft + tlBody.clientWidth - 40 || x < tlBody.scrollLeft)) tlBody.scrollLeft = x - 80;
  }
  function dragEdge(e, i, side) {
    e.preventDefault(); e.stopPropagation(); pause();
    snapshot();
    const seg = S.edl.segments[i], x0 = e.clientX, v0 = seg[side];
    const move = (ev) => {
      const v = v0 + (ev.clientX - x0) / S.pxs;
      if (side === 'in') seg.in = r3(clamp(v, 0, seg.out - 0.1)); else seg.out = r3(clamp(v, seg.in + 0.1, S.srcDur));
      relayout(); renderTimeline();
      const s = S.lay[i]; S.cur = i; S.t = side === 'in' ? s.os : Math.max(s.os, s.oe - 0.04);
      video.currentTime = side === 'in' ? seg.in : seg.out - 0.04; S.overlayKey = '';
    };
    const up = () => { document.removeEventListener('mousemove', move); document.removeEventListener('mouseup', up); S.selSeg = i; changed(); };
    document.addEventListener('mousemove', move); document.addEventListener('mouseup', up);
  }
  zoomIn.oninput = () => { S.pxs = +zoomIn.value; renderTimeline(); };
  function fitTimeline() { S.pxs = clamp(Math.floor((tlBody.clientWidth - 60) / Math.max(1, S.total)), 10, 400); zoomIn.value = S.pxs; renderTimeline(); }

  // ================================================================ inspector
  const TABS = [['segments', 'Cuts'], ['captions', 'Captions'], ['graphics', 'Graphics'], ['audio', 'Audio'], ['info', 'Plan & QC']];
  function renderInspector() {
    inspTabs.innerHTML = '';
    TABS.forEach(([k, label]) => inspTabs.append(h('button', { class: S.tab === k ? 'on' : '', onclick: () => { S.tab = k; renderInspector(); } }, label)));
    inspBody.innerHTML = '';
    ({ segments: tabSegments, captions: tabCaptions, graphics: tabGraphics, audio: tabAudio, info: tabInfo })[S.tab]();
  }
  const num = (val, onchange, step = 0.01, attrs = {}) => h('input', { type: 'number', step, value: val, onchange: (e) => onchange(parseFloat(e.target.value)), ...attrs });
  const edit = (fn) => { snapshot(); fn(); changed(); };

  function tabSegments() {
    inspBody.append(h('div', { class: 'section row' },
      h('button', { class: 'small', onclick: splitAtPlayhead }, '✂ Split at playhead'),
      h('button', { class: 'small', onclick: fitTimeline }, '↔ Fit timeline'),
      h('span', { class: 'grow' }),
      h('button', { class: 'small danger', title: 'Rebuild edl.json from the transcript (overwrites your edits)', onclick: async () => {
        if (!confirm('Rebuild the automatic edit? This replaces your current cuts, captions and graphics.')) return;
        await flushSave();
        const job = await api(`/api/projects/${encodeURIComponent(id)}/auto-edl`, { method: 'POST', body: {} });
        trackJob(job, 'Rebuilding auto edit', (j) => j.status === 'done' && route());
      } }, '⟲ Auto edit')));
    inspBody.append(h('div', { class: 'section muted', style: { fontSize: '12px' } }, `${S.lay.length} cuts · ${S.total.toFixed(1)}s long (source ${S.srcDur.toFixed(1)}s)` +
      (S.d.plan?.target_length_s ? ` · target ${S.d.plan.target_length_s}s` : '')));
    S.lay.forEach((s, i) => {
      const seg = S.edl.segments[i];
      const z = seg.zoom || { from: 1, to: 1, ease: 'linear' };
      const brollSel = h('select', { onchange: (e) => edit(() => { seg.overlay_broll = e.target.value ? { file: e.target.value, in: 0, mode: seg.overlay_broll?.mode || 'full' } : null; }) },
        h('option', { value: '' }, 'no b-roll'), (S.d.broll || []).map((f) => h('option', { value: f, selected: seg.overlay_broll?.file === f }, f.split('/').pop())));
      inspBody.append(h('div', { class: 'item' + (S.selSeg === i ? ' sel' : ''), onclick: (e) => { if (e.target.closest('input,select,button')) return; S.selSeg = i; seek(s.os); renderTimeline(); inspBody.querySelectorAll('.item').forEach((el, k) => el.classList.toggle('sel', k === i)); } },
        h('div', { class: 'row' },
          h('span', { class: 'swatch', style: { background: beatColor(seg.beat) } }), h('b', {}, `#${i + 1}`),
          h('input', { value: seg.beat || '', placeholder: 'beat', style: { width: '90px' }, onchange: (e) => edit(() => { seg.beat = e.target.value.trim() || null; }) }),
          h('span', { class: 'muted time' }, `${fmt(s.os)} · ${s.dur.toFixed(2)}s`), h('span', { class: 'grow' }),
          h('button', { class: 'small ghost', title: 'Move earlier', disabled: i === 0, onclick: () => edit(() => { const a = S.edl.segments; [a[i - 1], a[i]] = [a[i], a[i - 1]]; S.selSeg = i - 1; }) }, '↑'),
          h('button', { class: 'small ghost', title: 'Move later', disabled: i === S.lay.length - 1, onclick: () => edit(() => { const a = S.edl.segments; [a[i + 1], a[i]] = [a[i], a[i + 1]]; S.selSeg = i + 1; }) }, '↓'),
          h('button', { class: 'small ghost danger', title: 'Delete cut', disabled: S.lay.length === 1, onclick: () => edit(() => { S.edl.segments.splice(i, 1); S.selSeg = null; }) }, '✕')),
        h('div', { class: 'row' }, h('label', {}, 'in'), num(seg.in, (v) => edit(() => { seg.in = r3(clamp(v, 0, seg.out - 0.1)); })),
          h('label', {}, 'out'), num(seg.out, (v) => edit(() => { seg.out = r3(clamp(v, seg.in + 0.1, S.srcDur)); })),
          h('button', { class: 'small ghost', title: 'Nudge both edges −50ms / +50ms', onclick: () => edit(() => { seg.in = r3(Math.max(0, seg.in - 0.05)); seg.out = r3(Math.min(S.srcDur, seg.out + 0.05)); }) }, '⟷ +0.1s')),
        h('div', { class: 'row' }, h('label', {}, 'zoom'), num(z.from, (v) => edit(() => { seg.zoom = { ...z, from: clamp(v, 0.5, 3) }; }), 0.01, { style: { width: '62px' } }), '→',
          num(z.to, (v) => edit(() => { seg.zoom = { ...z, to: clamp(v, 0.5, 3) }; }), 0.01, { style: { width: '62px' } }),
          h('select', { onchange: (e) => edit(() => { seg.zoom = { ...z, ease: e.target.value }; }) }, Object.keys(EASE).map((k) => h('option', { value: k, selected: z.ease === k }, k))),
          h('button', { class: 'small ghost', title: 'Punch-in on this cut', onclick: () => edit(() => { seg.zoom = { from: 1.18, to: 1.2, ease: 'snap' }; }) }, 'punch')),
        h('div', { class: 'row' }, h('label', {}, 'frame'),
          h('select', { onchange: (e) => edit(() => { seg.reframe = e.target.value; }) }, ['face_track', 'center', 'none'].map((k) => h('option', { value: k, selected: (seg.reframe || 'face_track') === k }, k))),
          brollSel,
          seg.overlay_broll && h('select', { onchange: (e) => edit(() => { seg.overlay_broll.mode = e.target.value; }) }, ['full', 'split_top', 'pip'].map((k) => h('option', { value: k, selected: seg.overlay_broll.mode === k }, k))))));
    });
    if (!(S.d.broll || []).length) inspBody.append(h('div', { class: 'section muted', style: { fontSize: '12px' } }, 'B-roll: add clips with ', h('code', {}, `./studio edit ${id} --broll clip.mov`), ' (they land in raw/broll/).'));
  }

  function tabCaptions() {
    const c = S.edl.captions;
    inspBody.append(h('div', { class: 'section' },
      h('div', { class: 'row' },
        h('label', {}, h('input', { type: 'checkbox', checked: c.enabled !== false, onchange: (e) => edit(() => { c.enabled = e.target.checked; }) }), ' captions on'),
        h('select', { onchange: (e) => edit(() => { c.style = e.target.value; S.edl.edit_preset = e.target.value; }) }, Object.keys(CAP).map((k) => h('option', { value: k, selected: c.style === k }, k))),
        h('label', {}, 'words'), num(c.max_words || 3, (v) => edit(() => { c.max_words = clamp(Math.round(v), 1, 6); }), 1, { style: { width: '52px' } })),
      h('div', { class: 'row', style: { marginTop: '8px' } }, h('label', {}, 'size'),
        h('input', { type: 'range', min: 0.5, max: 1.6, step: 0.05, value: c.size || 1, class: 'grow', onchange: (e) => edit(() => { c.size = +e.target.value; }), oninput: (e) => { c.size = +e.target.value; S.overlayKey = ''; } }),
        h('span', { class: 'muted' }, `${Math.round((c.size || 1) * 100)}%`)),
      h('div', { class: 'muted', style: { fontSize: '12px', marginTop: '6px' } }, 'Fix a word by typing over it; ★ highlights it in the accent colour. Edits survive re-cuts.')));
    if (!c.words.length) return inspBody.append(h('div', { class: 'section muted' }, 'No caption words (no transcript).'));
    chunkWords(c.words, c.max_words || 3).forEach((ch) => {
      inspBody.append(h('div', { class: 'cap-line' },
        h('span', { class: 't', title: 'Jump here', onclick: () => seek(ch.start) }, fmt(ch.start)),
        ch.words.map((w) => {
          const k = c.words.indexOf(w);
          return h('span', { class: 'cap-word' + (w.highlight ? ' hl' : '') },
            h('input', { value: w.text, size: Math.max(2, w.text.length), onchange: (e) => edit(() => { c.words[k].text = e.target.value; }) }),
            h('button', { title: 'Highlight', onclick: () => edit(() => { c.words[k].highlight = !c.words[k].highlight; }) }, '★'));
        })));
    });
  }

  function tabGraphics() {
    const addRow = h('div', { class: 'section row' }, h('span', { class: 'muted', style: { fontSize: '12px' } }, 'Add at playhead:'),
      ['hook_text', 'badge', 'callout', 'diagram', 'series_tag', 'intro_sting', 'lower_third', 'emoji_pop'].map((t) => h('button', { class: 'small', onclick: () => edit(() => {
        const start = t === 'hook_text' || t === 'badge' || t === 'series_tag' ? 0 : r3(S.t);
        const dur = { hook_text: 2.8, badge: 2.5, series_tag: 3, intro_sting: 1.2, diagram: 4 }[t] || 2.5;
        const g = { type: t, start, end: r3(Math.min(S.total, start + dur)), text: { hook_text: 'Your hook here', badge: 'Day 1', callout: 'Key point', series_tag: 'AI Explained #1', intro_sting: 'AI Explained #1', lower_third: 'Name — role', emoji_pop: '🔥' }[t] };
        if (t === 'diagram') { delete g.text; g.spec = 'input -> model -> output'; g.position = 'middle'; }
        S.edl.graphics.push(g); S.selGfx = S.edl.graphics.length - 1;
      }) }, t.replace('_', ' '))));
    inspBody.append(addRow);
    if (!S.edl.graphics.length) inspBody.append(h('div', { class: 'section muted' }, 'No graphics yet.'));
    S.edl.graphics.forEach((g, i) => {
      const isDiagram = g.type === 'diagram';
      inspBody.append(h('div', { class: 'item' + (S.selGfx === i ? ' sel' : '') },
        h('div', { class: 'row' },
          h('select', { onchange: (e) => edit(() => { g.type = e.target.value; }) }, GFX_TYPES.map((t) => h('option', { value: t, selected: g.type === t }, t))),
          h('span', { class: 'grow' }),
          h('button', { class: 'small ghost', title: 'Jump to start', onclick: () => seek(g.start) }, '▶'),
          h('button', { class: 'small ghost danger', onclick: () => edit(() => { S.edl.graphics.splice(i, 1); S.selGfx = null; }) }, '✕')),
        h('div', { class: 'row' }, isDiagram
          ? h('input', { class: 'grow', value: g.spec || '', placeholder: 'a -> b -> c; b -[label]-> d', onchange: (e) => edit(() => { g.spec = e.target.value; }) })
          : h('input', { class: 'grow', value: g.text || '', placeholder: 'text', onchange: (e) => edit(() => { g.text = e.target.value; }) })),
        h('div', { class: 'row' },
          h('label', {}, 'from'), num(g.start, (v) => edit(() => { g.start = r3(clamp(v, 0, g.end - 0.05)); })),
          h('button', { class: 'small ghost', title: 'Set start to playhead', onclick: () => edit(() => { g.start = r3(Math.min(S.t, g.end - 0.05)); }) }, '⤓'),
          h('label', {}, 'to'), num(g.end, (v) => edit(() => { g.end = r3(clamp(v, g.start + 0.05, S.total)); })),
          h('button', { class: 'small ghost', title: 'Set end to playhead', onclick: () => edit(() => { g.end = r3(Math.max(S.t, g.start + 0.05)); }) }, '⤓'),
          g.type === 'hook_text' && g.text && g.text.split(/\s+/).length > 7 ? h('span', { class: 'chip warn' }, '> 7 words') : null)));
    });
  }

  function tabAudio() {
    const a = S.edl.audio;
    const m = a.music;
    inspBody.append(h('div', { class: 'section' },
      h('div', { class: 'row' }, h('b', {}, 'Music'), h('span', { class: 'grow' }),
        h('select', { onchange: (e) => edit(() => { a.music = e.target.value ? { file: e.target.value, gain_db: m?.gain_db ?? -18, duck: m?.duck ?? true } : null; }) },
          h('option', { value: '' }, 'none'), [...new Set([...S.assets.music, ...(m ? [m.file] : [])])].map((f) => h('option', { value: f, selected: m?.file === f }, f.split('/').pop())))),
      m && h('div', { class: 'row', style: { marginTop: '8px' } }, h('label', {}, 'gain dB'), num(m.gain_db ?? -18, (v) => edit(() => { m.gain_db = clamp(v, -40, 0); }), 1),
        h('label', {}, h('input', { type: 'checkbox', checked: m.duck !== false, onchange: (e) => edit(() => { m.duck = e.target.checked; }) }), ' duck under voice'),
        h('audio', { controls: true, src: `/asset/${m.file}`, style: { width: '100%', height: '32px', marginTop: '6px' } })),
      !S.assets.music.length && h('div', { class: 'muted', style: { fontSize: '12px', marginTop: '6px' } }, 'Put royalty-free tracks in assets/music/ to choose them here.')));
    inspBody.append(h('div', { class: 'section' },
      h('div', { class: 'row' }, h('b', {}, 'Sound effects'), h('span', { class: 'grow' }),
        h('button', { class: 'small', disabled: !S.assets.sfx.length, onclick: () => edit(() => { (a.sfx ||= []).push({ file: S.assets.sfx[0], at: r3(S.t), gain_db: -8 }); }) }, '＋ at playhead')),
      (a.sfx || []).map((s, i) => h('div', { class: 'row', style: { marginTop: '6px' } },
        h('select', { onchange: (e) => edit(() => { s.file = e.target.value; }) }, [...new Set([...S.assets.sfx, s.file])].map((f) => h('option', { value: f, selected: s.file === f }, f.split('/').pop()))),
        h('label', {}, 'at'), num(s.at, (v) => edit(() => { s.at = r3(clamp(v, 0, S.total)); })),
        h('label', {}, 'dB'), num(s.gain_db ?? -8, (v) => edit(() => { s.gain_db = v; }), 1, { style: { width: '56px' } }),
        h('button', { class: 'small ghost danger', onclick: () => edit(() => { a.sfx.splice(i, 1); }) }, '✕'))),
      !S.assets.sfx.length && h('div', { class: 'muted', style: { fontSize: '12px', marginTop: '6px' } }, 'Put sound effects (e.g. whoosh.wav) in assets/sfx/.')));
    inspBody.append(h('div', { class: 'section row' }, h('b', {}, 'Loudness target'), h('span', { class: 'grow' }), num(a.loudness_lufs ?? -14, (v) => edit(() => { a.loudness_lufs = clamp(v, -30, -8); }), 0.5), h('span', { class: 'muted' }, 'LUFS')),
      h('div', { class: 'section muted', style: { fontSize: '12px' } }, 'The live preview plays the cleaned voice only; music, ducking and SFX are mixed in the rendered preview/final.'));
  }

  function tabInfo() {
    const p = S.d.plan, qc = S.d.qc;
    if (qc) inspBody.append(h('div', { class: 'section' }, h('b', {}, 'Last QC  '), qc.auto_fails.length ? h('span', { class: 'chip bad' }, `${qc.auto_fails.length} issue(s)`) : h('span', { class: 'chip good' }, 'auto checks passed'),
      h('ul', { style: { margin: '8px 0 0', paddingLeft: '18px' } }, qc.auto_fails.map((f) => h('li', {}, f))),
      h('div', { class: 'muted', style: { fontSize: '12px' } }, `length ${qc.checks.length_s}s · loudness ${qc.checks.integrated_lufs} LUFS · max gap ${qc.checks.max_gap_s}s · longest static ${qc.checks.max_static_s}s`)));
    if (p) {
      inspBody.append(h('div', { class: 'section' }, h('b', {}, 'Hooks'),
        p.hooks.map((hk, i) => h('div', { style: { margin: '6px 0', padding: '6px 8px', borderRadius: '8px', background: i === p.chosen_hook ? '#2a2d4a' : 'transparent' } },
          h('div', {}, i === p.chosen_hook ? '★ ' : '', h('b', {}, hk.on_screen), h('span', { class: 'chip', style: { marginLeft: '6px' } }, hk.type)),
          h('div', { class: 'muted', style: { fontSize: '12px' } }, `“${hk.spoken}”`),
          h('button', { class: 'small', style: { marginTop: '4px' }, onclick: () => edit(() => { const g = S.edl.graphics.find((x) => x.type === 'hook_text'); if (g) g.text = hk.on_screen; else S.edl.graphics.push({ type: 'hook_text', text: hk.on_screen, start: 0, end: Math.min(2.8, S.total), position: 'top' }); }) }, 'Use as on-screen hook')))));
      inspBody.append(h('div', { class: 'section' }, h('b', {}, 'Beats'), p.beats.map((b) => h('div', { style: { marginTop: '6px', fontSize: '13px' } }, h('span', { class: 'swatch', style: { background: beatColor(b.id) } }), ' ', h('b', {}, b.id), ' ', h('span', { class: 'muted' }, b.spoken)))));
    }
    if (S.d.critic) inspBody.append(h('div', { class: 'section' }, h('b', {}, 'Critic report'), h('pre', { class: 'log' }, S.d.critic)));
    if (S.d.script) inspBody.append(h('div', { class: 'section' }, h('b', {}, 'Script'), h('pre', { class: 'log' }, S.d.script)));
    if (!p && !qc && !S.d.critic) inspBody.append(h('div', { class: 'section muted' }, 'No plan or QC yet. Render a preview to get a QC report.'));
  }

  // ================================================================ rendered views
  function renderViewTabs() {
    viewTabs.innerHTML = '';
    [['live', 'Live edit'], ['preview', 'Rendered preview'], ['final', 'Final']].forEach(([k, label]) => {
      const avail = k === 'live' || S.d[k];
      viewTabs.append(h('button', { class: S.view === k ? 'on' : '', disabled: !avail, onclick: () => { S.view = k; renderViewTabs(); showView(); } }, label));
    });
  }
  function showView() {
    const live = S.view === 'live';
    stageWrap.style.display = live ? '' : 'none';
    playB.parentElement.style.display = live ? '' : 'none';
    modeB.parentElement.style.display = live ? '' : 'none';
    renderedBox.style.display = live ? 'none' : '';
    renderedBox.innerHTML = '';
    if (!live) { pause(); renderedBox.append(h('video', { controls: true, src: media(id, S.d[S.view], S.bust || Date.now()), style: { width: '100%', maxHeight: 'calc(100vh - 330px)', background: '#000', borderRadius: '8px' } })); }
  }

  // ================================================================ keys
  function onKey(e) {
    if (e.target.closest?.('input, textarea, select')) return;
    const meta = e.metaKey || e.ctrlKey;
    if (e.code === 'Space') { e.preventDefault(); S.playing ? pause() : play(); }
    else if (meta && e.key.toLowerCase() === 'z') { e.preventDefault(); e.shiftKey ? redo() : undo(); }
    else if ((e.key === 'Backspace' || e.key === 'Delete') && S.sel) { e.preventDefault(); cutWords(...S.sel); }
    else if (e.key.toLowerCase() === 'r' && S.sel && !meta) { e.preventDefault(); restoreWords(...S.sel); }
    else if (e.key.toLowerCase() === 's' && !meta) { e.preventDefault(); splitAtPlayhead(); }
    else if (e.key === 'ArrowLeft') { seek(S.t - (e.shiftKey ? 1 : 1 / S.fps)); }
    else if (e.key === 'ArrowRight') { seek(S.t + (e.shiftKey ? 1 : 1 / S.fps)); }
    else if (meta && e.key.toLowerCase() === 's') { e.preventDefault(); flushSave(); }
  }
  document.addEventListener('keydown', onKey);
  const beforeUnload = (e) => { if (saveEl.textContent !== 'Saved' && saveEl.textContent !== '⚠ saved') { e.preventDefault(); e.returnValue = ''; } };
  window.addEventListener('beforeunload', beforeUnload);

  cleanup = () => {
    cancelAnimationFrame(S.raf); video.pause(); ro.disconnect();
    document.removeEventListener('keydown', onKey); document.removeEventListener('selectionchange', readSelection);
    window.removeEventListener('beforeunload', beforeUnload);
    if (saveEl.textContent !== 'Saved') saveNow();
  };

  renderViewTabs(); renderInspector(); renderTranscript(); fitStage();
  requestAnimationFrame(() => { fitTimeline(); fitStage(); });
  S.raf = requestAnimationFrame(tick);
}

// ================================================================== CAROUSEL EDITOR
async function carouselEditor(id) {
  const d = await api(`/api/projects/${encodeURIComponent(id)}`);
  if (!d.carousel) { $('#app').append(h('div', { class: 'page' }, h('h1', {}, id), h('p', { class: 'muted' }, 'No carousel.json in this project.'))); return; }
  const assets = await api('/api/assets');
  const C = { d, car: d.carousel, sel: 0, version: 0, saveT: null };
  $('#crumbs').append(h('a', { href: '#/' }, 'Projects'), '›', h('b', {}, id));
  const saveEl = h('span', { id: 'savestate' }, 'Saved');
  $('#actions').append(saveEl,
    h('button', { onclick: verify }, '🔗 Verify links'),
    h('button', { class: 'primary', onclick: renderSlides }, '⬆ Render PNG + PDF'),
    h('button', { class: 'ghost', title: 'Show outputs in Finder', onclick: () => api(`/api/projects/${encodeURIComponent(id)}/reveal`, { method: 'POST', body: {} }) }, '📂'));
  const form = h('div', { class: 'scroll inspector' });
  const previews = h('div', { class: 'slides-grid' });
  $('#app').append(h('div', { class: 'car' }, h('div', { class: 'col' }, h('div', { class: 'col-head' }, h('h3', {}, 'Slides')), form),
    h('div', { class: 'col' }, h('div', { class: 'col-head' }, h('h3', {}, 'Live preview'), h('span', { class: 'muted', style: { fontSize: '12px' } }, '· exactly what gets rendered'),
      h('span', { class: 'grow' }), h('label', {}, 'size'), (() => { const r = h('input', { type: 'range', min: 0.15, max: 0.5, step: 0.01, value: 0.26, oninput: (e) => { C.scale = +e.target.value; renderPreviews(); } }); return r; })()),
    h('div', { class: 'scroll' }, previews))));
  C.scale = 0.26;

  function changed(rerenderForm = false) {
    if (rerenderForm) renderForm();
    C.version++; saveEl.textContent = 'Unsaved'; clearTimeout(C.saveT); C.saveT = setTimeout(save, 500);
  }
  async function save() {
    const v = C.version; saveEl.textContent = 'Saving…';
    try { await api(`/api/projects/${encodeURIComponent(id)}/carousel`, { method: 'PUT', body: C.car }); saveEl.textContent = 'Saved'; if (v === C.version) renderPreviews(); }
    catch (e) { saveEl.textContent = 'Not saved'; toast(e.message, true); }
  }
  async function verify() {
    await save();
    const job = await api(`/api/projects/${encodeURIComponent(id)}/verify`, { method: 'POST', body: {} });
    trackJob(job, 'Verifying links', async () => { C.car = (await api(`/api/projects/${encodeURIComponent(id)}`)).carousel; renderForm(); });
  }
  async function renderSlides() {
    await save();
    const job = await api(`/api/projects/${encodeURIComponent(id)}/carousel-render`, { method: 'POST', body: {} });
    trackJob(job, 'Rendering slides', (j) => j.status === 'done' && toast('Slides + PDF ready in out/ — 📂 to open'));
  }

  const FIELDS = { hook: [['title', 'Title'], ['subtitle', 'Kicker']], resource: [['name', 'Name'], ['value', 'Why it’s worth it'], ['for_who', 'For'], ['tag', 'Tag'], ['url', 'URL'], ['image', 'Image path']], cta: [['title', 'Title'], ['subtitle', 'Subtitle']] };
  function renderForm() {
    const car = C.car;
    form.innerHTML = '';
    form.append(h('div', { class: 'section' }, h('div', { class: 'form-grid' },
      h('label', {}, 'Theme'), h('select', { onchange: (e) => { car.theme = e.target.value; changed(); } }, assets.themes.map((t) => h('option', { value: t, selected: car.theme === t }, t))),
      h('label', {}, 'Size'), h('select', { onchange: (e) => { car.size = e.target.value; changed(); } }, ['1080x1350', '1080x1080'].map((s) => h('option', { value: s, selected: car.size === s }, s === '1080x1350' ? '1080×1350 (4:5)' : '1080×1080 (square)'))),
      h('label', {}, 'Handle'), h('input', { value: car.handle || '', placeholder: '@yourhandle', onchange: (e) => { car.handle = e.target.value; changed(); } }),
      h('label', {}, 'Background'), h('input', { value: car.background || '', placeholder: 'optional image path (in the project)', onchange: (e) => { car.background = e.target.value || null; changed(); } }))));
    car.slides.forEach((s, i) => {
      const v = s.verified;
      form.append(h('div', { class: 'item' + (C.sel === i ? ' sel' : ''), onclick: (e) => { if (!e.target.closest('input,select,button,textarea')) { C.sel = i; renderForm(); renderPreviews(); } } },
        h('div', { class: 'row' }, h('b', {}, `${i + 1}`),
          h('select', { onchange: (e) => { s.kind = e.target.value; changed(true); } }, ['hook', 'resource', 'cta'].map((k) => h('option', { value: k, selected: s.kind === k }, k))),
          v ? h('span', { class: 'chip ' + (v.ok && (v.repo?.maintained ?? true) ? 'good' : 'bad'), title: JSON.stringify(v) }, v.ok ? (v.repo ? `✓ live · pushed ${v.repo.pushed_at}` : '✓ live') : `✗ HTTP ${v.status}`) : null,
          h('span', { class: 'grow' }),
          h('button', { class: 'small ghost', disabled: i === 0, onclick: () => { [car.slides[i - 1], car.slides[i]] = [car.slides[i], car.slides[i - 1]]; C.sel = i - 1; changed(true); } }, '↑'),
          h('button', { class: 'small ghost', disabled: i === car.slides.length - 1, onclick: () => { [car.slides[i + 1], car.slides[i]] = [car.slides[i], car.slides[i + 1]]; C.sel = i + 1; changed(true); } }, '↓'),
          h('button', { class: 'small ghost', title: 'Duplicate', onclick: () => { car.slides.splice(i + 1, 0, JSON.parse(JSON.stringify({ ...s, verified: undefined }))); changed(true); } }, '⧉'),
          h('button', { class: 'small ghost danger', disabled: car.slides.length <= 2, onclick: () => { car.slides.splice(i, 1); C.sel = Math.max(0, i - 1); changed(true); } }, '✕')),
        FIELDS[s.kind].map(([k, label]) => h('div', { class: 'row' }, h('label', { style: { width: '92px' } }, label),
          k === 'value' ? h('textarea', { rows: 2, class: 'grow', oninput: (e) => { s[k] = e.target.value; changed(); } }, s[k] || '')
            : h('input', { class: 'grow', value: s[k] || '', oninput: (e) => { s[k] = e.target.value; if (k === 'url') delete s.verified; changed(); } })))));
    });
    form.append(h('div', { class: 'section row' },
      h('button', { class: 'small', onclick: () => { const at = car.slides.findLastIndex((x) => x.kind !== 'cta') + 1; car.slides.splice(at, 0, { kind: 'resource', name: 'New resource', value: 'Why it’s worth it, in one line.', for_who: '', tag: 'Free', url: '' }); C.sel = at; changed(true); } }, '＋ Resource slide')));
    form.append(h('div', { class: 'section' }, h('label', {}, 'Caption'), h('textarea', { rows: 4, oninput: (e) => { car.caption_draft = e.target.value; changed(); } }, car.caption_draft || ''),
      h('label', {}, 'Hashtags (space-separated)'), h('input', { style: { width: '100%' }, value: (car.hashtags || []).join(' '), onchange: (e) => { car.hashtags = e.target.value.split(/[\s,]+/).map((x) => x.replace(/^#/, '')).filter(Boolean); changed(); } })));
  }
  function renderPreviews() {
    const [w, hgt] = (C.car.size || '1080x1350').split('x').map(Number), k = C.scale;
    previews.innerHTML = '';
    C.car.slides.forEach((_, i) => {
      const fr = h('iframe', { src: `/api/projects/${encodeURIComponent(id)}/carousel/slide/${i + 1}?v=${C.version}`, width: w, height: hgt, style: { transform: `scale(${k})` }, loading: 'lazy' });
      previews.append(h('div', { class: 'slide-frame' + (C.sel === i ? ' sel' : ''), style: { width: `${w * k}px`, height: `${hgt * k}px` }, onclick: () => { C.sel = i; renderForm(); renderPreviews(); form.querySelectorAll('.item')[i]?.scrollIntoView({ block: 'nearest' }); } },
        fr, h('span', { class: 'n' }, `${i + 1}/${C.car.slides.length}`)));
    });
  }
  renderForm(); renderPreviews();
  cleanup = () => { if (saveEl.textContent !== 'Saved') save(); };
}
