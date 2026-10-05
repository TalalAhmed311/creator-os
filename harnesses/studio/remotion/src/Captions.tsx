import React, {useMemo} from 'react';
import {interpolate, spring, useCurrentFrame} from 'remotion';
import {captionFont} from './fonts';
import type {Brand, Preset, Word} from './types';

type Chunk = {words: Word[]; start: number; end: number};

const clean = (s: string) => s.replace(/^[^\w$€£#@"'(]+/, '').replace(/[,.;:…]+$/, '');

/** 1–maxWords words per chunk; break on sentence punctuation or a pause. */
export function chunkWords(words: Word[], maxWords: number): Chunk[] {
  const chunks: Chunk[] = [];
  let cur: Word[] = [];
  const push = () => {
    if (cur.length) chunks.push({words: cur, start: cur[0].start, end: cur[cur.length - 1].end});
    cur = [];
  };
  words.forEach((w, i) => {
    const prev = words[i - 1];
    if (cur.length && (cur.length >= maxWords || (prev && w.start - prev.end > 0.3))) push();
    cur.push(w);
    if (/[.!?]$/.test(w.text)) push();
  });
  push();
  // hold each chunk until the next one starts (no flicker in short gaps)
  chunks.forEach((c, i) => {
    const next = chunks[i + 1];
    if (next && next.start - c.end < 0.4) c.end = next.start;
    else c.end += 0.15;
  });
  return chunks;
}

const STYLE: Record<Preset, {size: number; upper: boolean; stroke: number; weight: number; pop: boolean}> = {
  'bip-raw': {size: 88, upper: true, stroke: 14, weight: 900, pop: true},
  'ai-explained': {size: 70, upper: false, stroke: 0, weight: 800, pop: false},
  'talking-head-basic': {size: 76, upper: false, stroke: 10, weight: 800, pop: true},
};

export const Captions: React.FC<{
  words: Word[];
  style: Preset;
  size: number;
  maxWords: number;
  brand: Brand;
  fps: number;
  width: number;
  height: number;
  top?: number; // fraction of height; a collage theme moves the caption band
}> = ({words, style, size, maxWords, brand, fps, width, height, top = 0.6}) => {
  const frame = useCurrentFrame();
  const t = frame / fps;
  const chunks = useMemo(() => chunkWords(words, maxWords), [words, maxWords]);
  const chunk = chunks.find((c) => t >= c.start && t < c.end);
  if (!chunk) return null;
  const s = STYLE[style];
  const fontSize = s.size * size;
  const local = frame - Math.round(chunk.start * fps);
  const pop = s.pop ? spring({frame: local, fps, config: {damping: 14, stiffness: 220, mass: 0.6}}) : 1;
  const scale = s.pop ? interpolate(pop, [0, 1], [0.82, 1]) : 1;
  const opacity = s.pop ? 1 : interpolate(local, [0, 4], [0.2, 1], {extrapolateRight: 'clamp'});

  return (
    // safe zone: centre band at ~64% height — clear of the top 12% and the bottom 20% platform UI
    <div style={{position: 'absolute', left: 60, right: 60, top: height * top, display: 'flex', justifyContent: 'center'}}>
      <div
        style={{
          display: 'flex', flexWrap: 'wrap', justifyContent: 'center', columnGap: fontSize * 0.34 + s.stroke, rowGap: 0,
          maxWidth: width - 120, transform: `scale(${scale})`, opacity, textAlign: 'center',
          fontFamily: captionFont(style), fontWeight: s.weight, fontSize, lineHeight: 1.08,
          ...(style === 'ai-explained'
            ? {background: 'rgba(0,0,0,0.55)', padding: '14px 26px', borderRadius: 20}
            : {}),
        }}
      >
        {chunk.words.map((w, i) => {
          const active = t >= w.start && t < w.end + 0.05;
          const color = w.highlight ? brand.accent : brand.text;
          const txt = s.upper ? clean(w.text).toUpperCase() : clean(w.text);
          return (
            <span
              key={i}
              style={{
                color,
                WebkitTextStroke: s.stroke ? `${s.stroke}px ${brand.shadow}` : undefined,
                paintOrder: 'stroke fill',
                textShadow: s.stroke ? '0 6px 18px rgba(0,0,0,0.45)' : '0 3px 12px rgba(0,0,0,0.6)',
                transform: style === 'bip-raw' && active ? 'scale(1.08)' : undefined,
                display: 'inline-block',
                opacity: style === 'ai-explained' && t < w.start ? 0.55 : 1,
              }}
            >
              {txt}
            </span>
          );
        })}
      </div>
    </div>
  );
};
