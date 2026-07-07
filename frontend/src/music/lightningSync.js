// Port de window.LightningSync (ver ui/index.html, initLightning). Continua
// sendo um módulo imperativo de propósito — a animação é feita direto no
// DOM (paths SVG criados/removidos a cada raio), o mesmo approach do
// original, só que os elementos <svg>/container são "registrados" por um
// componente React (LightningCanvas) em vez de document.getElementById.
const SVG_NS = 'http://www.w3.org/2000/svg';

let canvas = null;      // <svg id="lightning-canvas">
let containerEl = null; // .menu-right (referência pra posicionar partículas de impacto)

function generateBolt(x1, y1, x2, y2, roughness, depth) {
  if (depth === 0) return [[x1, y1], [x2, y2]];
  const mx = (x1 + x2) / 2 + (Math.random() - 0.5) * roughness;
  const my = (y1 + y2) / 2 + (Math.random() - 0.5) * roughness * 0.5;
  const left = generateBolt(x1, y1, mx, my, roughness * 0.55, depth - 1);
  const right = generateBolt(mx, my, x2, y2, roughness * 0.55, depth - 1);
  return [...left.slice(0, -1), ...right];
}

function addBranches(points, svg, opacity) {
  const branchCount = 2 + Math.floor(Math.random() * 3);
  for (let b = 0; b < branchCount; b++) {
    const startIdx = Math.floor(points.length * 0.15 + Math.random() * points.length * 0.6);
    const [bx, by] = points[startIdx];
    const angle = (Math.random() - 0.5) * 1.4 + (Math.random() > 0.5 ? 0.5 : -0.5);
    const length = 30 + Math.random() * 80;
    const ex = bx + Math.cos(angle) * length;
    const ey = by + Math.sin(angle) * length + length * 0.4;
    const branchPts = generateBolt(bx, by, ex, ey, 18, 3);
    const d = 'M ' + branchPts.map((p) => p.join(' ')).join(' L ');
    const el = document.createElementNS(SVG_NS, 'path');
    el.setAttribute('d', d);
    el.setAttribute('stroke', 'rgba(246,179,51,' + opacity * 0.45 + ')');
    el.setAttribute('stroke-width', '0.8');
    el.setAttribute('fill', 'none');
    el.setAttribute('stroke-linecap', 'round');
    svg.appendChild(el);
  }
}

function spawnImpact(impactX, impactY) {
  if (!containerEl || !canvas) return;
  const rect = containerEl.getBoundingClientRect();
  const svgRect = canvas.getBoundingClientRect();
  const scaleX = svgRect.width / 600;
  const scaleY = svgRect.height / 700;
  const px = svgRect.left - rect.left + impactX * scaleX;
  const py = svgRect.top - rect.top + impactY * scaleY;

  const count = 18 + Math.floor(Math.random() * 14);
  for (let i = 0; i < count; i++) {
    const p = document.createElement('div');
    p.className = 'impact-particle';
    const angle = Math.random() * Math.PI * 2;
    const speed = 30 + Math.random() * 90;
    const tx = Math.cos(angle) * speed;
    const ty = Math.sin(angle) * speed - Math.random() * 60;
    const size = 1.5 + Math.random() * 4;
    const dur = 300 + Math.random() * 500;
    const isWhite = Math.random() > 0.4;
    p.style.cssText = `
      left:${px}px; top:${py}px;
      width:${size}px; height:${size}px;
      background:${isWhite ? 'rgba(255,255,255,.95)' : 'rgba(246,179,51,.9)'};
      box-shadow:0 0 ${size * 2}px ${isWhite ? 'rgba(255,255,255,.6)' : 'rgba(246,179,51,.5)'};
      --tx:${tx}px; --ty:${ty}px;
      animation-duration:${dur}ms;
      position:absolute; z-index:4;
    `;
    containerEl.appendChild(p);
    setTimeout(() => p.remove(), dur + 50);
  }

  const ring = document.createElementNS(SVG_NS, 'ellipse');
  ring.setAttribute('cx', impactX);
  ring.setAttribute('cy', impactY);
  ring.setAttribute('rx', '2');
  ring.setAttribute('ry', '1');
  ring.setAttribute('fill', 'none');
  ring.setAttribute('stroke', 'rgba(246,179,51,.9)');
  ring.setAttribute('stroke-width', '1.5');
  canvas.appendChild(ring);
  ring.animate(
    [
      { rx: '2', ry: '1', opacity: 1, strokeWidth: '1.5' },
      { rx: '80', ry: '20', opacity: 0, strokeWidth: '0.3' },
    ],
    { duration: 600, easing: 'ease-out', fill: 'forwards' }
  ).onfinish = () => ring.remove();
}

function strikeLightning() {
  if (!canvas) return;
  const startX = 180 + Math.random() * 240;
  const startY = 0;
  const endX = startX + (Math.random() - 0.5) * 120;
  const endY = 640 + Math.random() * 40;
  const roughness = 80 + Math.random() * 60;
  const points = generateBolt(startX, startY, endX, endY, roughness, 7);
  const d = 'M ' + points.map((p) => p.join(' ')).join(' L ');

  const group = document.createElementNS(SVG_NS, 'g');
  const glow = document.createElementNS(SVG_NS, 'path');
  glow.setAttribute('d', d);
  glow.setAttribute('stroke', 'rgba(246,179,51,.18)');
  glow.setAttribute('stroke-width', '8');
  glow.setAttribute('fill', 'none');
  glow.setAttribute('stroke-linecap', 'round');
  glow.setAttribute('filter', 'blur(3px)');

  const bolt = document.createElementNS(SVG_NS, 'path');
  bolt.setAttribute('d', d);
  bolt.setAttribute('stroke', 'rgba(255,255,230,.95)');
  bolt.setAttribute('stroke-width', '1.5');
  bolt.setAttribute('fill', 'none');
  bolt.setAttribute('stroke-linecap', 'round');

  group.appendChild(glow);
  group.appendChild(bolt);
  addBranches(points, group, 0.85);
  canvas.appendChild(group);

  const totalDur = 500 + Math.random() * 300;
  group.animate(
    [
      { opacity: 1 },
      { opacity: 1, offset: 0.25 },
      { opacity: 0.7, offset: 0.6 },
      { opacity: 0 },
    ],
    { duration: totalDur, easing: 'ease-in', fill: 'forwards' }
  ).onfinish = () => group.remove();

  setTimeout(() => spawnImpact(endX, endY), totalDur * 0.7);
}

const BPM = 84;
const BEAT_MS = 60000 / BPM;
const BEAT_S = BEAT_MS / 1000;
const BEAT_MASK = [1, 0, 0, 1, 1, 0, 1, 0];
const BEAT_INTENSITY = [2, 0, 0, 1, 2, 0, 1, 0];

let lastBeat = -1;
let rafId = null;
let audioEl = null;

function onFrame() {
  rafId = requestAnimationFrame(onFrame);

  if (!audioEl || audioEl.paused) {
    const now = performance.now();
    const beatNow = Math.floor(now / BEAT_MS);
    if (beatNow !== lastBeat && beatNow % 4 === 0) {
      lastBeat = beatNow;
      strikeLightning();
    }
    return;
  }

  const beatNow = Math.floor(audioEl.currentTime / BEAT_S);
  if (beatNow === lastBeat) return;
  lastBeat = beatNow;

  const slot = beatNow % BEAT_MASK.length;
  const intensity = BEAT_INTENSITY[slot];
  if (intensity === 0) return;

  strikeLightning();
  if (intensity >= 2) {
    if (Math.random() < 0.65) setTimeout(() => { if (rafId) strikeLightning(); }, BEAT_MS * 0.5);
    if (Math.random() < 0.25) setTimeout(() => { if (rafId) strikeLightning(); }, BEAT_MS * 0.75);
  } else if (Math.random() < 0.3) {
    setTimeout(() => { if (rafId) strikeLightning(); }, BEAT_MS * 0.5);
  }
}

export const lightningSync = {
  setCanvas(el) { canvas = el; },
  setContainer(el) { containerEl = el; },
  connect(el) { audioEl = el; },
  disconnect() { audioEl = null; },
  start() {
    if (rafId || !canvas) return;
    lastBeat = -1;
    strikeLightning();
    rafId = requestAnimationFrame(onFrame);
  },
  stop() {
    if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
    if (canvas) canvas.innerHTML = '';
  },
};
