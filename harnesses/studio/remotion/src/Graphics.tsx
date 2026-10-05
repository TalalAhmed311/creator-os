import React from 'react';
import {Easing, Sequence, interpolate, spring, useCurrentFrame} from 'remotion';
import {FONTS} from './fonts';
import type {Brand, Graphic, Preset} from './types';

type GP = {g: Graphic; brand: Brand; fps: number; width: number; height: number; style: Preset};

// Safe zone: nothing important in the top 12% or the bottom 20% (platform UI).
const TOP = 0.13;

const useIn = (fps: number, instant = false) => {
  const f = useCurrentFrame();
  return instant ? 1 : spring({frame: f, fps, config: {damping: 16, stiffness: 180}});
};

/** Hook text must be fully visible on frame 0 (critic rule), so it only "settles", never fades in. */
const HookText: React.FC<GP> = ({g, brand, fps, width, height, style}) => {
  const f = useCurrentFrame();
  const s = interpolate(f, [0, 6], [1.06, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const heavy = style === 'bip-raw';
  if (g.look) {
    // collage title: bare outlined text over the images (theme's title style)
    const L = g.look;
    return (
      <div style={{position: 'absolute', top: height * L.top, left: 50, right: 50, display: 'flex', justifyContent: 'center'}}>
        <div
          style={{
            transform: `scale(${s})`, color: L.color, fontFamily: L.font === 'heavy' ? FONTS.heavy : FONTS.clean, fontWeight: L.weight,
            fontSize: L.size, lineHeight: 1.12, textAlign: 'center', maxWidth: width - 100, textTransform: L.upper ? 'uppercase' : 'none',
            WebkitTextStroke: L.stroke ? `${L.stroke}px #000` : undefined, paintOrder: 'stroke fill', textShadow: '0 4px 18px rgba(0,0,0,.7)',
          }}
        >
          {g.text}
        </div>
      </div>
    );
  }
  return (
    // sits below the badge / series-tag row
    <div style={{position: 'absolute', top: height * (TOP + 0.065), left: 50, right: 50, display: 'flex', justifyContent: 'center'}}>
      <div
        style={{
          transform: `scale(${s})`, background: heavy ? brand.accent : 'rgba(255,255,255,0.95)', color: heavy ? '#0b0b0b' : '#111',
          fontFamily: heavy ? FONTS.heavy : FONTS.clean, fontWeight: 900, fontSize: 70, lineHeight: 1.1, padding: '20px 34px',
          borderRadius: 22, textAlign: 'center', maxWidth: width - 100, boxShadow: '0 14px 44px rgba(0,0,0,.35)',
          textTransform: heavy ? 'uppercase' : 'none',
        }}
      >
        {g.text}
      </div>
    </div>
  );
};

const Pill: React.FC<GP & {side: 'left' | 'right'}> = ({g, brand, fps, height, side}) => {
  const p = useIn(fps, g.start === 0);
  return (
    <div
      style={{
        position: 'absolute', top: height * TOP, [side]: 44, transform: `translateY(${(1 - p) * -30}px)`, opacity: p,
        background: side === 'left' ? brand.primary : 'rgba(0,0,0,0.6)', color: '#fff', fontFamily: FONTS.heavy, fontWeight: 900,
        fontSize: 44, padding: '10px 24px', borderRadius: 999, border: side === 'right' ? `3px solid ${brand.accent}` : undefined,
        letterSpacing: 1,
      }}
    >
      {g.text}
    </div>
  );
};

const Callout: React.FC<GP> = ({g, brand, fps, width, height}) => {
  const p = useIn(fps);
  return (
    <div style={{position: 'absolute', top: height * (TOP + 0.08), left: 0, right: 0, display: 'flex', justifyContent: 'center'}}>
      <div
        style={{
          transform: `scale(${interpolate(p, [0, 1], [0.6, 1])}) rotate(-2deg)`, opacity: p, background: brand.primary, color: '#fff',
          fontFamily: FONTS.heavy, fontWeight: 900, fontSize: 58, padding: '16px 30px', borderRadius: 18, maxWidth: width - 140,
          textAlign: 'center', boxShadow: `8px 8px 0 ${brand.accent}`,
        }}
      >
        {g.text}
      </div>
    </div>
  );
};

const LowerThird: React.FC<GP> = ({g, brand, fps, height}) => {
  const p = useIn(fps);
  return (
    <div style={{position: 'absolute', bottom: height * 0.24, left: 50, transform: `translateX(${(1 - p) * -500}px)`}}>
      <div style={{background: 'rgba(0,0,0,.72)', borderLeft: `10px solid ${brand.accent}`, color: '#fff', fontFamily: FONTS.clean, fontWeight: 700, fontSize: 44, padding: '14px 26px'}}>
        {g.text}
      </div>
    </div>
  );
};

const EmojiPop: React.FC<GP> = ({g, fps, width, height}) => {
  const p = useIn(fps);
  return (
    <div style={{position: 'absolute', top: height * 0.3, left: width * 0.66, fontSize: 150, transform: `scale(${p}) rotate(${(1 - p) * 40}deg)`}}>
      {g.text}
    </div>
  );
};

/** Full-screen series sting, ≤1.5 s. */
const IntroSting: React.FC<GP> = ({g, brand, fps, width, height}) => {
  const f = useCurrentFrame();
  const dur = Math.round((g.end - g.start) * fps);
  const wipe = interpolate(f, [0, 8, dur - 8, dur], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const [title, ep] = (g.text ?? 'AI Explained').split('#');
  return (
    <div style={{position: 'absolute', inset: 0, background: brand.primary, clipPath: `inset(0 ${(1 - wipe) * 100}% 0 0)`, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
      <div style={{fontFamily: FONTS.heavy, fontWeight: 900, color: '#fff', fontSize: 110, textAlign: 'center', width: width - 120}}>{title.trim()}</div>
      {ep && <div style={{marginTop: 20, fontFamily: FONTS.mono, fontWeight: 700, color: brand.accent, fontSize: 80}}>#{ep.trim()}</div>}
      <div style={{position: 'absolute', bottom: height * 0.25, height: 10, width: interpolate(f, [0, dur], [0, width - 200]), background: brand.accent, borderRadius: 5}} />
    </div>
  );
};

// ---------- diagrams: "request -> model -> response; model -> tools" ----------

type Node = {id: string; level: number; col: number};

export function parseDiagram(spec: string) {
  const edges: [string, string, string?][] = [];
  const order: string[] = [];
  const add = (n: string) => {
    if (!order.includes(n)) order.push(n);
  };
  spec.split(/[;\n]+/).forEach((chain) => {
    const parts = chain.split(/\s*-(?:\[([^\]]*)\])?>\s*/);
    // split with a capture group interleaves labels: [a, label?, b, label?, c]
    const nodes: string[] = [];
    const labels: (string | undefined)[] = [];
    parts.forEach((p, i) => (i % 2 === 0 ? nodes.push((p ?? '').trim()) : labels.push(p)));
    nodes.filter(Boolean).forEach(add);
    for (let i = 0; i + 1 < nodes.length; i++) if (nodes[i] && nodes[i + 1]) edges.push([nodes[i], nodes[i + 1], labels[i]]);
  });
  const level: Record<string, number> = {};
  order.forEach((n) => (level[n] = 0));
  for (let k = 0; k < order.length; k++) edges.forEach(([a, b]) => (level[b] = Math.max(level[b], level[a] + 1)));
  const byLevel: Record<number, string[]> = {};
  order.forEach((n) => (byLevel[level[n]] ??= []).push(n));
  const nodes: Node[] = order.map((id) => ({id, level: level[id], col: byLevel[level[id]].indexOf(id)}));
  return {nodes, edges, levels: Object.keys(byLevel).length, byLevel};
}

const Diagram: React.FC<GP> = ({g, brand, fps, width, height}) => {
  const f = useCurrentFrame();
  const dur = Math.max(1, Math.round((g.end - g.start) * fps));
  const {nodes, edges, levels, byLevel} = parseDiagram(g.spec ?? g.text ?? '');
  if (!nodes.length) return null;
  // panel sits in the upper-middle so the speaker's face often stays visible below
  const panel = {x: 60, y: height * TOP, w: width - 120, h: height * 0.4}; // ends above the caption band (~60%)
  const rowH = panel.h / Math.max(levels, 1);
  const pos = (n: Node) => {
    const cols = byLevel[n.level].length;
    return {x: panel.x + (panel.w / cols) * (n.col + 0.5), y: panel.y + rowH * (n.level + 0.5)};
  };
  const buildEnd = Math.min(dur * 0.6, levels * fps * 0.6);
  const appear = (lvl: number) => spring({frame: f - (buildEnd / Math.max(levels, 1)) * lvl, fps, config: {damping: 14}});
  const bg = interpolate(f, [0, 8, dur - 8, dur], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const boxW = Math.min(560, panel.w / Math.max(...Object.values(byLevel).map((l) => l.length)) - 40);
  const boxH = Math.min(120, rowH * 0.5);
  const pulse = ((f - buildEnd) % fps) / fps;

  return (
    <div style={{position: 'absolute', inset: 0, opacity: bg}}>
      <div style={{position: 'absolute', left: panel.x - 20, top: panel.y - 20, width: panel.w + 40, height: panel.h + 40, background: 'rgba(8,10,20,0.82)', borderRadius: 36, border: `2px solid ${brand.primary}`}} />
      <svg width={width} height={height} style={{position: 'absolute', inset: 0}}>
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill={brand.accent} />
          </marker>
        </defs>
        {edges.map(([a, b, label], i) => {
          const na = nodes.find((n) => n.id === a)!;
          const nb = nodes.find((n) => n.id === b)!;
          const pa = pos(na);
          const pb = pos(nb);
          const p = appear(nb.level);
          const y1 = pa.y + boxH / 2 + 6;
          const y2 = pb.y - boxH / 2 - 10;
          const x2 = pa.x + (pb.x - pa.x) * p;
          const yy = y1 + (y2 - y1) * p;
          return (
            <g key={i}>
              <line x1={pa.x} y1={y1} x2={x2} y2={yy} stroke={brand.accent} strokeWidth={6} markerEnd={p > 0.95 ? 'url(#arrow)' : undefined} />
              {f > buildEnd && <circle cx={pa.x + (pb.x - pa.x) * pulse} cy={y1 + (y2 - y1) * pulse} r={10} fill="#fff" />}
              {label && p > 0.9 && (
                <text x={(pa.x + pb.x) / 2 + 18} y={(y1 + y2) / 2} fill="#fff" fontFamily={FONTS.mono} fontSize={30}>{label}</text>
              )}
            </g>
          );
        })}
      </svg>
      {nodes.map((n) => {
        const {x, y} = pos(n);
        const p = appear(n.level);
        return (
          <div
            key={n.id}
            style={{
              position: 'absolute', left: x - boxW / 2, top: y - boxH / 2, width: boxW, height: boxH, transform: `scale(${p})`,
              display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fff', color: '#0b0b12',
              borderRadius: 20, border: `5px solid ${brand.primary}`, fontFamily: FONTS.clean, fontWeight: 800,
              fontSize: Math.min(52, boxH * 0.42), textAlign: 'center', padding: '0 14px', boxShadow: `6px 6px 0 ${brand.accent}`,
            }}
          >
            {n.id}
          </div>
        );
      })}
    </div>
  );
};

const COMPONENTS: Record<Graphic['type'], React.FC<GP>> = {
  hook_text: HookText,
  badge: (p) => <Pill {...p} side="left" />,
  series_tag: (p) => <Pill {...p} side="right" />,
  callout: Callout,
  diagram: Diagram,
  intro_sting: IntroSting,
  lower_third: LowerThird,
  emoji_pop: EmojiPop,
};

// Draw order: diagrams under text overlays, sting on top of everything.
const Z: Record<Graphic['type'], number> = {diagram: 1, lower_third: 2, emoji_pop: 2, callout: 3, badge: 4, series_tag: 4, hook_text: 5, intro_sting: 9};

export const GraphicsLayer: React.FC<{graphics: Graphic[]; brand: Brand; fps: number; width: number; height: number; style: Preset}> = ({graphics, ...rest}) => (
  <>
    {[...graphics]
      .sort((a, b) => Z[a.type] - Z[b.type])
      .map((g, i) => {
        const C = COMPONENTS[g.type];
        return (
          <Sequence key={i} from={Math.round(g.start * rest.fps)} durationInFrames={Math.max(1, Math.round((g.end - g.start) * rest.fps))} layout="none">
            <C g={g} {...rest} />
          </Sequence>
        );
      })}
  </>
);
