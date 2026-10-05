import React from 'react';
import {AbsoluteFill, Audio, Easing, Img, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame} from 'remotion';
import {FONTS} from './fonts';
import world from '../../../../projects/2026-09-30_bip-day-1-laid-off-building/work/map/world_paths.json';
import timing from '../../../../projects/2026-09-30_bip-day-1-laid-off-building/work/animatic_timing.json';

/**
 * Day 1 intro animatic (project 2026-09-30_bip-day-1-laid-off-building).
 * Black "FACE" scenes are placeholders for the owner's camera takes; everything else is generated.
 * Images resolve against --public-dir = project root (work/shots/*.png).
 */

const FPS = 30;
const W = 1080;
const H = 1920;
const C = {bg: '#0A0A12', panel: '#14141F', primary: '#5B5BF7', accent: '#FFD23F', red: '#FF3B3B', green: '#3DDC84', dim: '#8A8AA0'};
const f = (sec: number) => Math.round(sec * FPS);
const clampOpts = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const pop = (frame: number, delay = 0) => spring({frame: frame - delay, fps: FPS, config: {damping: 14, stiffness: 200}});

// ---------- building blocks ----------

/** Screenshot with a push-in: keeps image point (focusY) centred while zooming. */
const Shot: React.FC<{src: string; focusY: number; zoom: [number, number]; drift?: number; dur: number}> = ({src, focusY, zoom, drift = 0, dur}) => {
  const fr = useCurrentFrame();
  const t = interpolate(fr, [0, dur], [0, 1], {...clampOpts, easing: Easing.out(Easing.quad)});
  const z = zoom[0] + (zoom[1] - zoom[0]) * t;
  const fy = focusY + drift * t;
  return (
    <AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
      <Img
        src={staticFile(src)}
        style={{position: 'absolute', width: W, left: 0, top: 0, transformOrigin: '0 0', transform: `translate(${W / 2 - (W / 2) * z}px, ${H * 0.45 - fy * z}px) scale(${z})`}}
      />
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,.55) 100%)'}} />
    </AbsoluteFill>
  );
};

type NewsSpec = {src: string; iw: number; ih: number; fx: [number, number]; fy: [number, number]; vw: [number, number]};

/** Landscape article screenshot on a blurred copy of itself; pans/pushes from (fx0,fy0,vw0) to (fx1,fy1,vw1). vw = visible width fraction. */
const NewsShot: React.FC<NewsSpec & {dur: number}> = ({src, iw, ih, fx, fy, vw, dur}) => {
  const fr = useCurrentFrame();
  const k = interpolate(fr, [0, dur], [0, 1], {...clampOpts, easing: Easing.out(Easing.quad)});
  const lerp = (p: [number, number]) => p[0] + (p[1] - p[0]) * k;
  const s = W / (lerp(vw) * iw);
  const left = W / 2 - lerp(fx) * iw * s;
  const top = H * 0.42 - lerp(fy) * ih * s;
  return (
    <AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
      <Img src={staticFile(src)} style={{position: 'absolute', inset: -80, width: W + 160, height: H + 160, objectFit: 'cover', filter: 'blur(40px) brightness(0.35)'}} />
      <Img src={staticFile(src)} style={{position: 'absolute', left, top, width: iw * s, height: ih * s, boxShadow: '0 40px 120px rgba(0,0,0,.7)'}} />
    </AbsoluteFill>
  );
};

/** 16:9 news clip in the 9:16 frame: blurred copy behind, sharp crop pushed in on (fx, fy). vw = visible width fraction. */
const NewsVideo: React.FC<{src: string; from: number; fx: [number, number]; fy: [number, number]; vw: [number, number]; dur: number; volume?: number}> = ({src, from, fx, fy, vw, dur, volume = 1}) => {
  const fr = useCurrentFrame();
  const k = interpolate(fr, [0, dur], [0, 1], {...clampOpts, easing: Easing.out(Easing.quad)});
  const lerp = (p: [number, number]) => p[0] + (p[1] - p[0]) * k;
  const iw = 1920;
  const ih = 1080;
  const s = W / (lerp(vw) * iw);
  const left = Math.min(0, Math.max(W - iw * s, W / 2 - lerp(fx) * iw * s));
  const top = ih * s >= H ? Math.min(0, Math.max(H - ih * s, H * 0.45 - lerp(fy) * ih * s)) : H * 0.42 - lerp(fy) * ih * s;
  const start = Math.round(from * FPS);
  return (
    <AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
      {ih * s < H ? (
        <OffthreadVideo muted src={staticFile(src)} startFrom={start} style={{position: 'absolute', inset: -80, width: W + 160, height: H + 160, objectFit: 'cover', filter: 'blur(40px) brightness(0.35)'}} />
      ) : null}
      <OffthreadVideo src={staticFile(src)} startFrom={start} volume={volume} style={{position: 'absolute', left, top, width: iw * s, height: ih * s, boxShadow: '0 40px 120px rgba(0,0,0,.7)'}} />
    </AbsoluteFill>
  );
};

/** Rolling "tech jobs lost in 2026" counter that sits over the montage. */
const JobsCounter: React.FC<{dur: number; from: number; to: number}> = ({dur, from, to}) => {
  const fr = useCurrentFrame();
  const n = Math.round(interpolate(fr, [0, dur], [from, to], {...clampOpts, easing: Easing.in(Easing.quad)}));
  const bump = fr % 6 < 2 ? 1.04 : 1;
  return (
    <div style={{position: 'absolute', top: H * 0.68, left: 0, right: 0, display: 'flex', justifyContent: 'center'}}>
      <div style={{background: 'rgba(10,10,10,.85)', border: `4px solid ${C.red}`, borderRadius: 20, padding: '14px 30px 18px', textAlign: 'center', transform: `scale(${bump})`, boxShadow: '0 20px 60px rgba(0,0,0,.6)'}}>
        <div style={{fontFamily: FONTS.clean, fontWeight: 800, fontSize: 28, letterSpacing: 5, color: C.red}}>● TECH JOBS LOST IN 2026</div>
        <div style={{fontFamily: FONTS.mono, fontWeight: 700, fontSize: 108, color: '#fff', lineHeight: 1.05}}>{n.toLocaleString('en-US')}</div>
      </div>
    </div>
  );
};

/** Hard cuts at variable lengths with a 2-frame white flash and a small shake on each cut. */
const NewsMontage: React.FC<{items: [React.ReactNode, number][]}> = ({items}) => {
  const fr = useCurrentFrame();
  const bounds: number[] = [];
  let acc = 0;
  for (const [, sec] of items) {
    bounds.push(f(acc));
    acc += sec;
  }
  let i = 0;
  while (i < items.length - 1 && fr >= bounds[i + 1]) i++;
  const local = fr - bounds[i];
  const shake = local < 4 ? (4 - local) * (i % 2 ? 7 : -7) : 0;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{transform: `translate(${shake}px, ${-shake / 2}px)`}}>
        <Sequence from={bounds[i]} durationInFrames={f(items[i][1])} layout="none">
          {items[i][0]}
        </Sequence>
      </AbsoluteFill>
      {local < 2 && i > 0 ? <AbsoluteFill style={{background: '#fff', opacity: 0.75}} /> : null}
    </AbsoluteFill>
  );
};

/** Placeholder for a face-camera take: pure black + a small label and the line to say. */
const Face: React.FC<{line: string; take: number}> = ({line, take}) => {
  const fr = useCurrentFrame();
  const blink = Math.floor(fr / 15) % 2 === 0;
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <div style={{position: 'absolute', top: H * 0.13, left: 56, display: 'flex', alignItems: 'center', gap: 16, fontFamily: FONTS.clean, fontWeight: 700, fontSize: 30, color: '#666'}}>
        <div style={{width: 22, height: 22, borderRadius: 11, background: blink ? C.red : '#400'}} />
        FACE {take} · replace with your take
      </div>
      <div style={{position: 'absolute', top: H * 0.36, left: 80, right: 80, textAlign: 'center', fontFamily: FONTS.clean, fontWeight: 500, fontSize: 40, color: '#5a5a5a', fontStyle: 'italic'}}>
        “{line}”
      </div>
    </AbsoluteFill>
  );
};

/** Owner's real take (raw/cam.mov, 1620×1080) cropped to 9:16 around the tracked face; audio from the cleaned work/voice.wav. */
const SRC = {w: 1620, h: 1080, fps: 30};
const FaceClip: React.FC<{parts: number[][]; cx: number}> = ({parts, cx}) => {
  const scale = H / SRC.h;
  const vw = SRC.w * scale;
  const left = Math.min(0, Math.max(W - vw, W / 2 - cx * vw));
  let at = 0;
  return (
    <AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
      {parts.map(([a, b], i) => {
        const from = f(at);
        const dur = Math.max(1, Math.round((b - a) * FPS));
        at += b - a;
        const z0 = i % 2 ? 1.08 : 1.0; // alternate framing on each cut to hide the jump
        return (
          <Sequence key={i} from={from} durationInFrames={dur}>
            <ZoomWrap from={z0} to={z0 + 0.03} dur={dur}>
              <OffthreadVideo muted src={staticFile('raw/cam.mov')} startFrom={Math.round(a * SRC.fps)} style={{position: 'absolute', top: 0, left, width: vw, height: H}} />
            </ZoomWrap>
            <Audio src={staticFile('work/voice.wav')} startFrom={Math.round(a * FPS)} endAt={Math.round(b * FPS)} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

const ZoomWrap: React.FC<{from: number; to: number; dur: number; children: React.ReactNode}> = ({from, to, dur, children}) => {
  const fr = useCurrentFrame();
  const z = interpolate(fr, [0, dur], [from, to], clampOpts);
  return <AbsoluteFill style={{transform: `scale(${z})`, transformOrigin: '50% 35%'}}>{children}</AbsoluteFill>;
};

/** Owner's face take, lip-synced to the voice track and enhanced (work/faces/build_faces.py). Muted: the voice comes from work/voice.wav. */
const SyncedFace: React.FC<{id: string}> = ({id}) => {
  const fr = useCurrentFrame();
  const z = interpolate(fr, [0, 150], [1.0, 1.04], clampOpts);
  return (
    <AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
      <AbsoluteFill style={{transform: `scale(${z})`, transformOrigin: '50% 35%'}}>
        <OffthreadVideo muted src={staticFile(`work/faces/${id}_sync.mp4`)} style={{width: W, height: H, objectFit: 'cover'}} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Window: React.FC<{title: string; children: React.ReactNode; top?: number; height?: number}> = ({title, children, top = 360, height = 900}) => (
  <div style={{position: 'absolute', left: 60, right: 60, top, height, background: C.panel, borderRadius: 26, overflow: 'hidden', boxShadow: '0 30px 90px rgba(0,0,0,.6)', border: '1px solid #26263a'}}>
    <div style={{height: 64, background: '#1C1C2B', display: 'flex', alignItems: 'center', padding: '0 24px', gap: 12}}>
      {['#FF5F57', '#FEBC2E', '#28C840'].map((c) => <div key={c} style={{width: 20, height: 20, borderRadius: 10, background: c}} />)}
      <div style={{marginLeft: 20, fontFamily: FONTS.mono, fontSize: 26, color: C.dim}}>{title}</div>
    </div>
    <div style={{padding: '30px 36px'}}>{children}</div>
  </div>
);

type Line = {text: string; color?: string};
/** Types lines out char by char at `cps` characters per second. */
const Typed: React.FC<{lines: Line[]; cps?: number; size?: number; delay?: number}> = ({lines, cps = 45, size = 34, delay = 0}) => {
  const fr = useCurrentFrame();
  let budget = Math.max(0, ((fr - delay) / FPS) * cps);
  const cursorOn = Math.floor(fr / 8) % 2 === 0;
  let cursorPlaced = false;
  return (
    <div style={{fontFamily: FONTS.mono, fontSize: size, lineHeight: 1.55, color: '#E6E6F0', whiteSpace: 'pre'}}>
      {lines.map((l, i) => {
        const shown = l.text.slice(0, Math.floor(budget));
        budget -= l.text.length;
        const typing = !cursorPlaced && shown.length < l.text.length;
        if (typing) cursorPlaced = true;
        if (!shown.length && !typing) return <div key={i}>&nbsp;</div>;
        return (
          <div key={i} style={{color: l.color}}>
            {shown}
            {typing && cursorOn ? <span style={{background: C.accent, color: C.accent}}>_</span> : null}
          </div>
        );
      })}
    </div>
  );
};

const Dark: React.FC<{children: React.ReactNode}> = ({children}) => (
  <AbsoluteFill style={{background: `radial-gradient(circle at 50% 35%, #1B1B3A 0%, ${C.bg} 70%)`}}>{children}</AbsoluteFill>
);

// ---------- scenes ----------

const WhatNext: React.FC = () => {
  const fr = useCurrentFrame();
  return (
    <Dark>
      <div style={{position: 'absolute', top: 700, left: 90, right: 90, background: '#fff', borderRadius: 60, padding: '34px 44px', display: 'flex', alignItems: 'center', gap: 24, transform: `scale(${interpolate(fr, [0, 90], [1, 1.06], clampOpts)})`}}>
        <div style={{width: 40, height: 40, border: '6px solid #999', borderRadius: 20}} />
        <div style={{fontFamily: FONTS.clean, fontWeight: 500, fontSize: 48, color: '#222'}}>
          <Typed lines={[{text: 'what do i do after getting laid off', color: '#222'}]} cps={22} size={36} delay={6} />
        </div>
      </div>
    </Dark>
  );
};

const WordStack: React.FC<{words: string[]; every: number}> = ({words, every}) => {
  const fr = useCurrentFrame();
  return (
    <Dark>
      <div style={{position: 'absolute', inset: 0, opacity: 0.12, padding: 60, fontFamily: FONTS.mono, fontSize: 26, color: C.primary, whiteSpace: 'pre', lineHeight: 1.6}}>
        {Array.from({length: 40}, (_, i) => ['const llm = new Client(model);', 'docs = retriever.search(query, k=5)', 'agent.run(tools=[search, code])', 'return {answer, sources}'][i % 4]).join('\n')}
      </div>
      <div style={{position: 'absolute', top: 440, left: 0, right: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 26}}>
        {words.map((w, i) => {
          const p = pop(fr, i * every);
          const last = i === words.length - 1;
          return (
            <div key={w} style={{opacity: p, transform: `translateY(${(1 - p) * 60}px) scale(${interpolate(p, [0, 1], [1.4, 1])})`, display: 'flex', alignItems: 'center', gap: 24}}>
              {i > 0 ? <span style={{color: C.dim, fontSize: 60, fontFamily: FONTS.heavy}}>↓</span> : null}
              <span style={{fontFamily: FONTS.heavy, fontWeight: 900, fontSize: last ? 120 : 100, color: last ? C.accent : '#fff', letterSpacing: 2}}>{w}</span>
            </div>
          );
        })}
      </div>
    </Dark>
  );
};

const SomeoneElses: React.FC = () => {
  const fr = useCurrentFrame();
  const strike = interpolate(fr, [30, 44], [0, 100], clampOpts);
  return (
    <Dark>
      <Window title="JIRA-4821 · assigned to: talal" top={520} height={520}>
        {['Build feature from spec', 'Ship Q3 roadmap item', 'Implement PM request', 'Fix ticket #4822'].map((t, i) => (
          <div key={t} style={{opacity: pop(fr, i * 3), fontFamily: FONTS.clean, fontWeight: 700, fontSize: 40, color: '#ddd', padding: '14px 0', borderBottom: '1px solid #2a2a3a'}}>☐ {t}</div>
        ))}
      </Window>
      <div style={{position: 'absolute', top: 1110, left: 0, right: 0, textAlign: 'center'}}>
        <span style={{position: 'relative', fontFamily: FONTS.heavy, fontWeight: 900, fontSize: 76, color: '#fff'}}>
          SOMEONE ELSE'S IDEAS
          <span style={{position: 'absolute', left: 0, top: '52%', height: 10, width: `${strike}%`, background: C.red}} />
        </span>
      </div>
    </Dark>
  );
};

const Ideas: React.FC = () => {
  const fr = useCurrentFrame();
  const ideas = ['AI tutor that actually remembers you', 'RAG for my own notes', 'agent that applies to jobs', 'voice journal → weekly summary', 'LLM eval dashboard', 'open-source reel editor', 'paper → 60s explainer', 'code review bot'];
  const n = Math.min(ideas.length, Math.floor(fr / 5) + 1);
  const count = Math.round(interpolate(fr, [0, 44], [1, 47], clampOpts));
  return (
    <Dark>
      <Window title="~/ideas.txt" top={380} height={1000}>
        {ideas.slice(0, n).map((t, i) => (
          <div key={t} style={{fontFamily: FONTS.mono, fontSize: 36, color: '#E6E6F0', padding: '10px 0'}}>
            <span style={{color: C.dim}}>{String(i + 1).padStart(2, '0')} </span>{t}
          </div>
        ))}
      </Window>
      <div style={{position: 'absolute', top: 1420, right: 90, background: C.accent, color: '#111', fontFamily: FONTS.heavy, fontWeight: 900, fontSize: 56, padding: '10px 28px', borderRadius: 16, transform: 'rotate(-3deg)'}}>
        {count} ideas. 0 built.
      </div>
    </Dark>
  );
};

const Waiting: React.FC<{dur: number}> = ({dur}) => {
  const fr = useCurrentFrame();
  const pct = Math.min(12, Math.floor(fr / 3));
  const cancelled = fr > dur - 22;
  return (
    <Dark>
      <div style={{position: 'absolute', top: 760, left: 110, right: 110}}>
        <div style={{fontFamily: FONTS.clean, fontWeight: 700, fontSize: 46, color: '#fff', marginBottom: 34, display: 'flex', alignItems: 'center', gap: 22}}>
          <div style={{width: 46, height: 46, border: `7px solid #333`, borderTopColor: C.primary, borderRadius: 23, transform: `rotate(${fr * 18}deg)`}} />
          Waiting for next opportunity…
        </div>
        <div style={{height: 36, background: '#222', borderRadius: 18, overflow: 'hidden'}}>
          <div style={{height: '100%', width: `${pct}%`, background: C.primary}} />
        </div>
        <div style={{fontFamily: FONTS.mono, fontSize: 32, color: C.dim, marginTop: 20}}>{pct}% · est. time remaining: unknown</div>
      </div>
      {cancelled ? (
        <div style={{position: 'absolute', top: 1160, left: 0, right: 0, display: 'flex', justifyContent: 'center'}}>
          <div style={{transform: `scale(${pop(fr, dur - 22)})`, background: C.red, color: '#fff', fontFamily: FONTS.heavy, fontWeight: 900, fontSize: 60, padding: '16px 44px', borderRadius: 16}}>✕ CANCEL</div>
        </div>
      ) : null}
    </Dark>
  );
};

const BuildRush: React.FC = () => (
  <Dark>
    <Window title="zsh · ~/projects" top={560} height={620}>
      <Typed
        cps={70}
        lines={[
          {text: '$ mkdir idea-01 && cd idea-01', color: C.green},
          {text: '$ git init'},
          {text: 'Initialized empty Git repository'},
          {text: '$ code .', color: C.green},
        ]}
      />
    </Window>
  </Dark>
);

const PillarTitle: React.FC<{num: string; title: string}> = ({num, title}) => {
  const fr = useCurrentFrame();
  const p = pop(fr);
  return (
    <AbsoluteFill style={{background: C.primary, justifyContent: 'center', alignItems: 'center'}}>
      <div style={{fontFamily: FONTS.heavy, fontWeight: 900, fontSize: 260, color: C.accent, lineHeight: 1, transform: `translateY(${(1 - p) * -80}px)`}}>{num}</div>
      <div style={{fontFamily: FONTS.heavy, fontWeight: 900, fontSize: 120, color: '#fff', letterSpacing: 4, opacity: p, transform: `scale(${interpolate(p, [0, 1], [0.7, 1])})`}}>{title}</div>
    </AbsoluteFill>
  );
};

const CodeEditor: React.FC = () => (
  <Dark>
    <Window title="app/main.py" top={400} height={1000}>
      <Typed
        cps={60}
        size={32}
        lines={[
          {text: 'from fastapi import FastAPI', color: '#C792EA'},
          {text: 'from agent import Agent', color: '#C792EA'},
          {text: ''},
          {text: 'app = FastAPI()'},
          {text: 'agent = Agent(model="claude")'},
          {text: ''},
          {text: '@app.post("/ask")', color: C.accent},
          {text: 'async def ask(q: str):'},
          {text: '    return await agent.run(q)'},
        ]}
      />
    </Window>
  </Dark>
);

const Deploy: React.FC = () => {
  const fr = useCurrentFrame();
  return (
    <Dark>
      <Window title="zsh · deploy" top={480} height={760}>
        <Typed
          cps={80}
          lines={[
            {text: '$ npm run deploy', color: C.green},
            {text: '✗ Build failed: 3 errors', color: C.red},
            {text: '$ npm run deploy', color: C.green},
            {text: '✗ Build failed: 1 error', color: C.red},
            {text: '$ npm run deploy', color: C.green},
            {text: '✓ Deployed to production', color: C.green},
          ]}
        />
      </Window>
      {fr > 40 ? (
        <div style={{position: 'absolute', top: 1300, left: 0, right: 0, textAlign: 'center'}}>
          <span style={{display: 'inline-block', transform: `scale(${pop(fr, 40)})`, background: C.green, color: '#062', fontFamily: FONTS.heavy, fontWeight: 900, fontSize: 64, padding: '12px 36px', borderRadius: 16}}>LAUNCHED 🚀</span>
        </div>
      ) : null}
    </Dark>
  );
};

const RagDiagram: React.FC = () => {
  const fr = useCurrentFrame();
  const boxes = ['Question', 'Retriever', 'Your docs', 'LLM', 'Answer'];
  return (
    <Dark>
      <div style={{position: 'absolute', top: 300, left: 0, right: 0, textAlign: 'center', fontFamily: FONTS.heavy, fontWeight: 900, fontSize: 64, color: C.accent}}>RAG, simply</div>
      <div style={{position: 'absolute', top: 440, left: 0, right: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18}}>
        {boxes.map((b, i) => {
          const p = pop(fr, i * 6);
          return (
            <React.Fragment key={b}>
              {i > 0 ? <div style={{opacity: p, color: C.dim, fontSize: 50, fontFamily: FONTS.heavy}}>↓</div> : null}
              <div style={{opacity: p, transform: `scale(${interpolate(p, [0, 1], [0.6, 1])})`, width: 560, textAlign: 'center', padding: '22px 0', borderRadius: 22, background: i === 3 ? C.primary : C.panel, border: `3px solid ${i === 3 ? C.primary : '#34344a'}`, fontFamily: FONTS.clean, fontWeight: 800, fontSize: 48, color: '#fff'}}>{b}</div>
            </React.Fragment>
          );
        })}
      </div>
    </Dark>
  );
};

const DayTicker: React.FC = () => {
  const fr = useCurrentFrame();
  const days = Array.from({length: 30}, (_, i) => i + 1);
  return (
    <Dark>
      <div style={{position: 'absolute', top: 420, left: 90, right: 90, display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 18}}>
        {days.map((d) => {
          const p = pop(fr, d * 0.9);
          const first = d === 1;
          return (
            <div key={d} style={{opacity: p, aspectRatio: '1', borderRadius: 18, display: 'flex', justifyContent: 'center', alignItems: 'center', background: first ? C.accent : C.panel, color: first ? '#111' : '#555', fontFamily: FONTS.heavy, fontWeight: 900, fontSize: first ? 54 : 40, border: first ? 'none' : '2px solid #26263a'}}>
              {first ? 'D1' : '?'}
            </div>
          );
        })}
      </div>
      <div style={{position: 'absolute', top: 1260, left: 0, right: 0, textAlign: 'center', fontFamily: FONTS.clean, fontWeight: 700, fontSize: 44, color: C.dim}}>the wins · the fails · everything</div>
    </Dark>
  );
};

const ProductTease: React.FC = () => {
  const fr = useCurrentFrame();
  const shimmer = (fr * 12) % 1400;
  const bar = (w: number, h = 34) => <div style={{width: w, height: h, borderRadius: 10, background: `linear-gradient(90deg, #22223a ${shimmer - 400}px, #34345a ${shimmer - 200}px, #22223a ${shimmer}px)`, marginBottom: 22}} />;
  return (
    <Dark>
      <Window title="product-01 · coming soon" top={420} height={960}>
        {bar(420, 56)}
        {bar(760)}
        {bar(640)}
        <div style={{display: 'flex', gap: 20, marginTop: 30}}>
          {[0, 1].map((i) => <div key={i} style={{flex: 1, height: 300, borderRadius: 20, background: '#1d1d30', border: '2px solid #2d2d45'}} />)}
        </div>
        <div style={{marginTop: 50, textAlign: 'center', fontFamily: FONTS.heavy, fontWeight: 900, fontSize: 60, color: C.accent, filter: 'blur(1px)'}}>██████ ███</div>
      </Window>
    </Dark>
  );
};

// ---------- map (Natural Earth, public domain; drawn in a maps-app style) ----------

const MAP = {sea: '#AADAFF', land: '#F4F2EC', border: '#C8C2B6', text: '#5F6368', pk: '#DCDDFF', pkLine: C.primary};
const merc = (lon: number, lat: number): [number, number] => [
  ((lon + 180) / 360) * 1000,
  ((1 - Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360)) / Math.PI) / 2) * 1000,
];
const CAM_WORLD = {c: merc(69, 29), s: 3.4};
const HOME = merc(74.41, 31.47); // Lahore (LUMS): the only location on the map
const CAM_PK = {c: merc(71.5, 29.5), s: 17};
const SCREEN_C: [number, number] = [W / 2, 860];
const TEAM_TAG: [number, number] = [40, 300];

type Cam = {c: [number, number]; s: number};
const toScreen = (cam: Cam, p: [number, number]): [number, number] => [
  (p[0] - cam.c[0]) * cam.s + SCREEN_C[0],
  (p[1] - cam.c[1]) * cam.s + SCREEN_C[1],
];

const MapBase: React.FC<{cam: Cam; pkGlow: number; grey?: number}> = ({cam, pkGlow, grey = 0}) => (
  <AbsoluteFill style={{background: MAP.sea, filter: `grayscale(${grey})`}}>
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
      <g transform={`translate(${SCREEN_C[0]} ${SCREEN_C[1]}) scale(${cam.s}) translate(${-cam.c[0]} ${-cam.c[1]})`}>
        {world.countries.map((c) => {
          const pk = c.name === 'Pakistan';
          return (
            <path
              key={c.name}
              d={c.d}
              fill={pk ? MAP.pk : MAP.land}
              stroke={pk ? MAP.pkLine : MAP.border}
              strokeWidth={pk ? 1.5 + 3 * pkGlow : 1}
              strokeOpacity={pk ? 0.4 + 0.6 * pkGlow : 1}
              vectorEffect="non-scaling-stroke"
              fillRule="evenodd"
            />
          );
        })}
      </g>
      {world.labels.map((l) => {
        const [x, y] = toScreen(cam, l.xy as [number, number]);
        const sea = l.name === 'Arabian Sea';
        const pk = l.name === 'PAKISTAN';
        return (
          <text
            key={l.name}
            x={x}
            y={y}
            textAnchor="middle"
            fontFamily={FONTS.clean}
            fontWeight={pk ? 800 : 600}
            fontStyle={sea ? 'italic' : 'normal'}
            fontSize={pk ? 44 : 30}
            letterSpacing={sea ? 1 : 5}
            fill={sea ? '#4A7FB0' : pk ? '#222' : MAP.text}
            opacity={pk ? 0.4 + 0.6 * pkGlow : 0.9 * interpolate(cam.s, [8, 14], [0, 1], clampOpts)}
          >
            {l.name}
          </text>
        );
      })}
    </svg>
  </AbsoluteFill>
);

const Pin: React.FC<{at: [number, number]; drop: number; emoji: string; bob: number}> = ({at, drop, emoji, bob}) => {
  const [x, y] = at;
  const fr = useCurrentFrame();
  const pulse = (fr % 30) / 30;
  return (
    <>
      <div style={{position: 'absolute', left: x - 60 * (0.3 + pulse), top: y - 24 * (0.3 + pulse), width: 120 * (0.3 + pulse), height: 48 * (0.3 + pulse), borderRadius: '50%', border: `4px solid ${C.primary}`, opacity: drop * (1 - pulse)}} />
      <svg width={70} height={96} viewBox="0 0 70 96" style={{position: 'absolute', left: x - 35, top: y - 96 - (1 - drop) * 400, opacity: Math.min(1, drop * 3)}}>
        <path d="M35 94C35 94 4 56 4 34a31 31 0 0 1 62 0c0 22-31 60-31 60z" fill={C.red} stroke="#fff" strokeWidth={4} />
        <circle cx={35} cy={34} r={12} fill="#fff" />
      </svg>
      <div style={{position: 'absolute', left: x - 70, top: y - 222 + bob, width: 140, height: 124, opacity: drop > 0.95 ? 1 : 0}}>
        <div style={{width: 140, height: 110, borderRadius: 30, background: '#fff', boxShadow: '0 12px 30px rgba(0,0,0,.25)', display: 'flex', justifyContent: 'center', alignItems: 'center', fontSize: 78}}>{emoji}</div>
        <div style={{width: 0, height: 0, margin: '0 auto', borderLeft: '16px solid transparent', borderRight: '16px solid transparent', borderTop: '16px solid #fff'}} />
      </div>
    </>
  );
};

const CityCard: React.FC<{at: [number, number]; p: number}> = ({at, p}) => (
  <div style={{position: 'absolute', left: at[0] - 180, width: 360, top: at[1] + 18, textAlign: 'center', opacity: p, transform: `translateY(${(1 - p) * 30}px)`, background: '#fff', borderRadius: 16, padding: '14px 24px', boxShadow: '0 10px 30px rgba(0,0,0,.2)'}}>
    <div style={{fontFamily: FONTS.clean, fontWeight: 800, fontSize: 40, color: '#202124'}}>Lahore</div>
    <div style={{fontFamily: FONTS.clean, fontWeight: 500, fontSize: 28, color: MAP.text}}>Pakistan 🇵🇰 · that's me</div>
  </div>
);

/** Dashed link from the pin to the "Remote team" tag; `broken` 0→1 snaps it red and pulls the halves apart. */
const RemoteLink: React.FC<{from: [number, number]; draw: number; broken?: number}> = ({from, draw, broken = 0}) => {
  const [x1, y1] = [from[0], from[1] - 232];
  const [x2, y2] = [TEAM_TAG[0] + 150, TEAM_TAG[1] + 90];
  const cx = (x1 + x2) / 2 - 160;
  const cy = (y1 + y2) / 2 - 80;
  const len = 900;
  const color = broken > 0 ? C.red : C.primary;
  const gap = broken * 120;
  return (
    <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
      <defs>
        <clipPath id="lower"><rect x={0} y={(y1 + y2) / 2 + gap / 2} width={W} height={H} /></clipPath>
        <clipPath id="upper"><rect x={0} y={0} width={W} height={(y1 + y2) / 2 - gap / 2} /></clipPath>
      </defs>
      {['lower', 'upper'].map((k) => (
        <path
          key={k}
          clipPath={`url(#${k})`}
          d={`M${x1} ${y1} Q${cx} ${cy} ${x2} ${y2}`}
          fill="none"
          stroke={color}
          strokeWidth={7}
          strokeLinecap="round"
          strokeDasharray={`${len * draw} ${len}`}
          style={{transform: k === 'lower' ? `translateY(${gap / 3}px)` : `translateY(${-gap / 3}px)`}}
          opacity={1 - broken * 0.3}
        />
      ))}
      {broken > 0 ? (
        <g transform={`translate(${(x1 + 2 * cx + x2) / 4} ${(y1 + 2 * cy + y2) / 4}) scale(${broken})`}>
          <circle r={44} fill={C.red} stroke="#fff" strokeWidth={6} />
          <path d="M-16 -16L16 16M16 -16L-16 16" stroke="#fff" strokeWidth={9} strokeLinecap="round" />
        </g>
      ) : null}
      {draw >= 1 ? (
        <circle cx={x1 + (x2 - x1) * ((useCurrentFrame() % 20) / 20)} cy={y1 + (y2 - y1) * ((useCurrentFrame() % 20) / 20)} r={broken > 0 ? 0 : 9} fill={C.accent} />
      ) : null}
    </svg>
  );
};

const TeamTag: React.FC<{p: number; grey?: number}> = ({p, grey = 0}) => (
  <div style={{position: 'absolute', left: TEAM_TAG[0], top: TEAM_TAG[1], opacity: p * (1 - grey * 0.5), transform: `scale(${interpolate(p, [0, 1], [0.7, 1])})`, background: '#202124', color: '#fff', borderRadius: 999, padding: '16px 30px', fontFamily: FONTS.clean, fontWeight: 800, fontSize: 38, filter: `grayscale(${grey})`}}>
    🌍 Remote team
  </div>
);

/** "I was working remotely from Lahore, Pakistan, for a company abroad." */
const MapRemote: React.FC = () => {
  const fr = useCurrentFrame();
  const z = interpolate(fr, [16, 58], [0, 1], {...clampOpts, easing: Easing.inOut(Easing.cubic)});
  const s = Math.exp(Math.log(CAM_WORLD.s) + (Math.log(CAM_PK.s) - Math.log(CAM_WORLD.s)) * z);
  const cam: Cam = {s, c: [CAM_WORLD.c[0] + (CAM_PK.c[0] - CAM_WORLD.c[0]) * z, CAM_WORLD.c[1] + (CAM_PK.c[1] - CAM_WORLD.c[1]) * z]};
  const pkGlow = interpolate(fr, [4, 18], [0, 1], clampOpts) * (0.75 + 0.25 * Math.sin(fr / 5));
  const pin = toScreen(cam, HOME);
  const drop = spring({frame: fr - 60, fps: FPS, config: {damping: 11, stiffness: 160}});
  return (
    <AbsoluteFill>
      <MapBase cam={cam} pkGlow={pkGlow} />
      <RemoteLink from={pin} draw={interpolate(fr, [86, 110], [0, 1], clampOpts)} />
      <TeamTag p={pop(fr, 104)} />
      <Pin at={pin} drop={fr >= 60 ? drop : 0} emoji="🧑‍💻" bob={Math.sin(fr / 6) * 8} />
      <CityCard at={pin} p={pop(fr, 72)} />
    </AbsoluteFill>
  );
};

/** "…while doing my MS in AI at LUMS, in Lahore." The Lahore pin's bubble flips 🧑‍💻 → 🎓, then cut to the LUMS photo with the name tag (this scene only). */
const MapLums: React.FC = () => {
  const fr = useCurrentFrame();
  const pin = toScreen(CAM_PK, HOME);
  const photo = interpolate(fr, [34, 42], [0, 1], clampOpts);
  const kb = interpolate(fr, [34, 110], [1.0, 1.07], clampOpts);
  const tag = pop(fr, 46);
  return (
    <AbsoluteFill>
      <MapBase cam={CAM_PK} pkGlow={1} />
      <RemoteLink from={pin} draw={1} />
      <TeamTag p={1} />
      <Pin at={pin} drop={1} emoji={fr < 8 ? '🧑‍💻' : '🎓'} bob={fr >= 8 && fr < 16 ? -18 * Math.sin(((fr - 8) / 8) * Math.PI) : Math.sin(fr / 6) * 8} />
      <CityCard at={pin} p={1} />
      <AbsoluteFill style={{opacity: photo, background: '#000'}}>
        <Img src={staticFile('work/shots/lums.png')} style={{position: 'absolute', inset: -80, width: W + 160, height: H + 160, objectFit: 'cover', filter: 'blur(36px) brightness(0.5)'}} />
        <div style={{position: 'absolute', left: (W - 720) / 2, top: 400, width: 720, height: 904, transform: `rotate(-2deg) translateY(${(1 - photo) * 60}px)`, background: '#fff', padding: 16, boxShadow: '0 40px 120px rgba(0,0,0,.6)'}}>
          <div style={{width: '100%', height: '100%', overflow: 'hidden'}}>
            <Img src={staticFile('work/shots/lums.png')} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${kb})`}} />
          </div>
        </div>
        <div style={{position: 'absolute', left: 90, top: 290, opacity: tag, transform: `translateX(${(1 - tag) * -80}px) rotate(-2deg)`}}>
          <div style={{display: 'inline-block', background: C.accent, color: '#111', fontFamily: FONTS.heavy, fontWeight: 900, fontSize: 92, padding: '4px 30px', letterSpacing: 4, borderRadius: 14}}>LUMS 🎓</div>
          <div style={{marginTop: 10, background: 'rgba(0,0,0,.78)', color: '#fff', fontFamily: FONTS.clean, fontWeight: 700, fontSize: 34, padding: '10px 22px', borderRadius: 12, borderLeft: `8px solid ${C.accent}`}}>
            MS in Artificial Intelligence · Lahore
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** "Then one day, it was just… over." The link snaps. */
const MapRevoked: React.FC = () => {
  const fr = useCurrentFrame();
  const pin = toScreen(CAM_PK, HOME);
  const broken = interpolate(fr, [6, 16], [0, 1], {...clampOpts, easing: Easing.out(Easing.back(2))});
  const grey = interpolate(fr, [10, 26], [0, 0.8], clampOpts);
  const p = pop(fr, 22);
  const shake = fr >= 6 && fr < 12 ? (12 - fr) * (fr % 2 ? 5 : -5) : 0;
  return (
    <AbsoluteFill style={{transform: `translateX(${shake}px)`}}>
      <MapBase cam={CAM_PK} pkGlow={1 - grey} grey={grey} />
      <RemoteLink from={pin} draw={1} broken={broken} />
      <TeamTag p={1} grey={grey} />
      <Pin at={pin} drop={1} emoji={fr < 12 ? '🧑‍💻' : '😶'} bob={0} />
      <AbsoluteFill style={{background: `rgba(0,0,0,${0.45 * grey})`}} />
      <div style={{position: 'absolute', top: 820, left: 110, right: 110, opacity: p, transform: `scale(${interpolate(p, [0, 1], [0.85, 1])})`, background: '#fff', borderRadius: 28, padding: '44px 40px', textAlign: 'center', boxShadow: '0 40px 120px rgba(0,0,0,.6)'}}>
        <div style={{width: 90, height: 90, borderRadius: 45, background: C.red, color: '#fff', fontFamily: FONTS.heavy, fontWeight: 900, fontSize: 60, margin: '0 auto', display: 'flex', justifyContent: 'center', alignItems: 'center'}}>!</div>
        <div style={{fontFamily: FONTS.clean, fontWeight: 800, fontSize: 44, color: '#111', marginTop: 22}}>Your access has been removed</div>
        <div style={{fontFamily: FONTS.clean, fontWeight: 500, fontSize: 30, color: '#666', marginTop: 10}}>Please contact your administrator.</div>
      </div>
    </AbsoluteFill>
  );
};

const EndCard: React.FC = () => {
  const fr = useCurrentFrame();
  const a = pop(fr);
  const b = pop(fr, 14);
  return (
    <AbsoluteFill style={{background: '#000', justifyContent: 'center', alignItems: 'center'}}>
      <div style={{fontFamily: FONTS.clean, fontWeight: 800, fontSize: 46, color: C.dim, letterSpacing: 8, opacity: a}}>BUILDING FROM SCRATCH</div>
      <div style={{fontFamily: FONTS.heavy, fontWeight: 900, fontSize: 280, color: C.accent, lineHeight: 1, marginTop: 10, transform: `scale(${interpolate(a, [0, 1], [1.5, 1])})`, opacity: a}}>DAY 1</div>
      <div style={{marginTop: 50, marginBottom: 180, opacity: b, textAlign: 'center'}}>
        <div style={{fontFamily: FONTS.heavy, fontWeight: 900, fontSize: 58, color: '#fff'}}>Talal Ahmed</div>
        <div style={{fontFamily: FONTS.clean, fontWeight: 700, fontSize: 42, color: C.dim, marginTop: 10}}>
          AI Engineer <span style={{color: C.accent}}>→</span> Builder
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** Sub-montage inside a scene: [node, seconds][] */
const Chain: React.FC<{parts: [React.ReactNode, number][]}> = ({parts}) => {
  let at = 0;
  return (
    <AbsoluteFill>
      {parts.map(([node, sec], i) => {
        const from = at;
        at += f(sec);
        return (
          <Sequence key={i} from={from} durationInFrames={i === parts.length - 1 ? undefined : f(sec)}>
            {node}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

// ---------- captions (voice-over guide) ----------

const Caption: React.FC<{text: string; dur: number; windows?: [number, number][]}> = ({text, dur, windows}) => {
  const fr = useCurrentFrame();
  const words = text.split(/\s+/);
  const chunks: string[] = [];
  for (let i = 0; i < words.length; i += 3) chunks.push(words.slice(i, i + 3).join(' '));
  const wins = windows?.length ? windows : [[0, dur] as [number, number]];
  const total = wins.reduce((n, [a, b]) => n + (b - a), 0);
  const voiced = wins.reduce((n, [a, b]) => n + Math.min(Math.max(fr - a, 0), b - a), 0);
  const per = total / chunks.length;
  const idx = Math.min(chunks.length - 1, Math.floor(voiced / per));
  const local = voiced - idx * per;
  const s = interpolate(local, [0, 4], [1.15, 1], clampOpts);
  const highlight = /\d|LLMs|RAG|build|AI|LUMS|laid|ridiculous|document|Day/i;
  return (
    <div style={{position: 'absolute', top: H * 0.7, left: 60, right: 60, textAlign: 'center'}}>
      <span style={{display: 'inline-block', transform: `scale(${s})`, background: 'rgba(0,0,0,.55)', padding: '10px 26px', borderRadius: 18, fontFamily: FONTS.heavy, fontWeight: 900, fontSize: 70, textTransform: 'uppercase', color: '#fff', WebkitTextStroke: '3px #000', paintOrder: 'stroke', textShadow: '0 6px 18px rgba(0,0,0,.8)', lineHeight: 1.1}}>
        {chunks[idx].split(' ').map((w, i) => (
          <span key={i} style={{color: highlight.test(w) ? C.accent : '#fff'}}>{w} </span>
        ))}
      </span>
    </div>
  );
};

const DayBadge: React.FC = () => (
  <div style={{position: 'absolute', top: H * 0.13, right: 44, background: 'rgba(0,0,0,.6)', color: '#fff', fontFamily: FONTS.heavy, fontWeight: 900, fontSize: 40, padding: '8px 22px', borderRadius: 999, border: `3px solid ${C.accent}`}}>
    DAY 1
  </div>
);

// ---------- timeline (durations shared with work/make_music.py) ----------

type SceneId = keyof typeof timing.scenes;
type Scene = {id: SceneId; node?: React.ReactNode; vo?: string; badge?: boolean};

const RAPID: [React.ReactNode, number][] = [
  [<NewsShot src="work/shots/news-microsoft.png" iw={2000} ih={620} fx={[0.62, 0.64]} fy={[0.33, 0.33]} vw={[0.5, 0.46]} dur={8} />, 0.26],
  [<NewsShot src="work/shots/news-amazon.png" iw={2000} ih={1054} fx={[0.49, 0.5]} fy={[0.27, 0.27]} vw={[0.84, 0.8]} dur={8} />, 0.26],
  [<NewsShot src="work/shots/news-ai-blamed.png" iw={2000} ih={1054} fx={[0.42, 0.43]} fy={[0.29, 0.29]} vw={[0.62, 0.58]} dur={8} />, 0.26],
  [<NewsShot src="work/shots/news-indonesia.png" iw={2000} ih={660} fx={[0.43, 0.44]} fy={[0.55, 0.55]} vw={[0.82, 0.78]} dur={8} />, 0.26],
  [<NewsShot src="work/shots/layoffs-fyi.png" iw={1080} ih={2200} fx={[0.5, 0.45]} fy={[0.115, 0.11]} vw={[0.95, 0.85]} dur={8} />, 0.26],
];

const NEWS: Record<string, (dur: number) => React.ReactNode> = {
  'cnbc-100k': (d) => <NewsVideo src="work/news/cnbc-100k.mp4" from={0} fx={[0.33, 0.34]} fy={[0.5, 0.52]} vw={[0.72, 0.66]} dur={d} />,
  'cnbc-meta': (d) => <NewsVideo src="work/news/cnbc-meta.mp4" from={0} fx={[0.36, 0.38]} fy={[0.5, 0.5]} vw={[0.78, 0.7]} dur={d} volume={0.8} />,
  'fp-ai-era': (d) => <NewsVideo src="work/news/fp-ai-era.mp4" from={1.35} fx={[0.66, 0.66]} fy={[0.45, 0.45]} vw={[0.56, 0.5]} dur={d} volume={0.5} />,
  'fp-chart': (d) => <NewsVideo src="work/news/fp-chart.mp4" from={1.4} fx={[0.3, 0.34]} fy={[0.36, 0.34]} vw={[0.66, 0.6]} dur={d} volume={0.5} />,
  rapid: () => <NewsMontage items={RAPID} />,
  'fp-human-story': (d) => <NewsVideo src="work/news/fp-human-story.mp4" from={0} fx={[0.3, 0.3]} fy={[0.45, 0.45]} vw={[0.34, 0.3]} dur={d} />,
};
const NEWS_ITEMS = timing.news.map(([k, sec]) => [NEWS[k as string](f(sec as number)), sec as number] as [React.ReactNode, number]);
const NEWS_COUNTER_S = timing.news.slice(0, -1).reduce((n, [, sec]) => n + (sec as number), 0); // counter runs until the last line
const NEWS_LAST_S = timing.news[timing.news.length - 1][1] as number;

const NewsHook: React.FC = () => (
  <AbsoluteFill>
    <NewsMontage items={NEWS_ITEMS} />
    <Sequence durationInFrames={f(NEWS_COUNTER_S)} layout="none">
      <JobsCounter dur={f(NEWS_COUNTER_S)} from={100000} to={129994} />
    </Sequence>
    <Sequence from={f(NEWS_COUNTER_S)} layout="none">
      <Caption text="The layoff story, at its heart, is a human story." dur={f(NEWS_LAST_S)} windows={[[0, f(NEWS_LAST_S) - 2]]} />
    </Sequence>
  </AbsoluteFill>
);

const SCENES: Scene[] = [
  {id: 'news', node: <NewsHook />},
  {id: 'black1'},
  {id: 'face1', node: <SyncedFace id="face1" />, vo: 'Yeah… I got laid off too.'},
  {id: 'face2', node: <SyncedFace id="face2" />, vo: "I'm Talal Ahmed. I'm an AI engineer."},
  {id: 'remote', node: <MapRemote />, vo: 'I was working remotely from Lahore, Pakistan, for a company abroad.'},
  {id: 'lums', node: <MapLums />, vo: 'While doing my MS in AI at LUMS.'},
  {id: 'revoked', node: <MapRevoked />, vo: 'Then one day, it was just… over.'},
  {id: 'whatnext', node: <WhatNext />, vo: "And honestly, I'm figuring out what comes next."},
  {id: 'stack', node: <WordStack words={['LLMs', 'RAG', 'Agents', 'Products']} every={18} />, vo: "For years, I've been building AI systems. LLMs, RAG, agents. Turning ideas into real products."},
  {id: 'someone', node: <SomeoneElses />, vo: "But they were always someone else's ideas."},
  {id: 'face3', node: <SyncedFace id="face3" />, vo: 'While I had a ridiculous number of my own sitting in my head.'},
  {id: 'ideas', node: <Ideas />},
  {id: 'waiting', node: <Waiting dur={f(timing.scenes.waiting)} />, vo: 'So… instead of waiting for the next opportunity…'},
  {id: 'face4', node: <SyncedFace id="face4" />, vo: "I'm going to build."},
  {id: 'buildrush', node: <BuildRush />, badge: true},
  {
    id: 'p1', badge: true, vo: 'One. Products from scratch. The experiments, the failures, hopefully some launches.',
    node: <Chain parts={[[<PillarTitle num="01" title="BUILD" />, 0.8], [<CodeEditor />, 1.4], [<Deploy />, 1.6], [<ProductTease />, 1.0]]} />,
  },
  {
    id: 'p2', badge: true, vo: "Two. AI. What I have learned, and what I'm learning. LLMs, like research papers.",
    node: (
      <Chain
        parts={[
          [<PillarTitle num="02" title="AI" />, 0.8],
          [<Shot src="work/shots/arxiv-attention.png" focusY={420} zoom={[1.5, 1.35]} drift={250} dur={f(1.3)} />, 1.3],
          [<RagDiagram />, 1.5],
          [<Shot src="work/shots/arxiv-rag.png" focusY={560} zoom={[1.45, 1.6]} dur={f(1.0)} />, 1.0],
          [<Shot src="work/shots/huggingface.png" focusY={300} zoom={[1.3, 1.3]} drift={500} dur={f(1.0)} />, 1.0],
        ]}
      />
    ),
  },
  {
    id: 'p3', badge: true, vo: 'Three. Build in public. Everything that happens along the way.',
    node: (
      <Chain
        parts={[
          [<PillarTitle num="03" title="THE JOURNEY" />, 0.8],
          [<Shot src="work/shots/github-trending.png" focusY={900} zoom={[1.3, 1.45]} drift={200} dur={f(1.3)} />, 1.3],
          [<DayTicker />, 2.3],
        ]}
      />
    ),
  },
  {id: 'face5', node: <SyncedFace id="face5" />, vo: 'I have no idea where this is going to take me. But I am going to document it.'},
  {id: 'end', node: <EndCard />, vo: "Let's see what we can build."},
  {id: 'black2'},
];

// cumulative rounding so scene starts match the music cues exactly
const STARTS: number[] = [];
{
  let acc = 0;
  for (const s of SCENES) {
    STARTS.push(f(acc));
    acc += timing.scenes[s.id];
  }
  STARTS.push(f(acc));
}
export const ANIMATIC_FRAMES = STARTS[STARTS.length - 1];

// owner's voice: source cuts per scene (work/voice.wav), laid end to end after a short lead-in
const VOICE = timing.voice.parts as Record<string, number[][]>;
const LEAD = f(timing.voice.lead);
/** scene-relative [from, to) frames of each voice cut */
const voiceWindows = (id: string): [number, number][] => {
  let at = LEAD;
  return (VOICE[id] ?? []).map(([a, b]) => {
    const w: [number, number] = [at, at + Math.round((b - a) * FPS)];
    at = w[1];
    return w;
  });
};
const VoiceTrack: React.FC<{id: string}> = ({id}) => (
  <>
    {(VOICE[id] ?? []).map(([a, b], i) => {
      const [from, to] = voiceWindows(id)[i];
      return (
        <Sequence key={i} from={from} durationInFrames={to - from}>
          <Audio src={staticFile(timing.voice.file)} startFrom={Math.round(a * FPS)} endAt={Math.round(b * FPS)} />
        </Sequence>
      );
    })}
  </>
);

// music ducks ~−12 dB under the voice with 6-frame ramps
const VOICE_SPANS = SCENES.flatMap((s, i) => voiceWindows(s.id).map(([a, b]) => [STARTS[i] + a, STARTS[i] + b] as const));
const NEWS_END = f(timing.scenes.news);
const musicVolume = (fr: number) => {
  let v = fr < NEWS_END ? 0.5 : 1;
  for (const [a, b] of VOICE_SPANS) {
    const d = Math.min(fr - a, b - fr);
    if (d > -6) v = Math.min(v, interpolate(d, [-6, 0], [1, 0.25], clampOpts));
  }
  return v;
};

export const Animatic: React.FC = () => (
  <AbsoluteFill style={{background: '#000'}}>
    <Audio src={staticFile('work/music.wav')} volume={musicVolume} />
    {SCENES.map((s, i) => {
      const dur = STARTS[i + 1] - STARTS[i];
      return (
        <Sequence key={s.id} from={STARTS[i]} durationInFrames={dur}>
          {s.node ?? <AbsoluteFill style={{background: '#000'}} />}
          {s.badge ? <DayBadge /> : null}
          <VoiceTrack id={s.id} />
          {s.vo ? <Caption text={s.vo} dur={dur} windows={voiceWindows(s.id)} /> : null}
        </Sequence>
      );
    })}
  </AbsoluteFill>
);
