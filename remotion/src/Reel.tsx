import React, {useMemo} from 'react';
import {AbsoluteFill, Easing, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {Captions} from './Captions';
import {CollageTiles, collageMix, collageSpans, rectPx} from './Collage';
import {GraphicsLayer} from './Graphics';
import type {CropPoint, Ease, ReelProps, Seg} from './types';

const EASE: Record<Ease, (t: number) => number> = {
  linear: (t) => t,
  easeIn: Easing.in(Easing.cubic),
  easeOut: Easing.out(Easing.cubic),
  easeInOut: Easing.inOut(Easing.cubic),
  snap: (t) => t,
};

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

function cropAt(points: CropPoint[], t: number): {cx: number; cy: number} {
  if (!points.length) return {cx: 0.5, cy: 0.42};
  if (t <= points[0].t) return points[0];
  const last = points[points.length - 1];
  if (t >= last.t) return last;
  let i = 0;
  while (i < points.length - 2 && points[i + 1].t < t) i++;
  const a = points[i];
  const b = points[i + 1];
  const k = (t - a.t) / Math.max(1e-6, b.t - a.t);
  return {cx: a.cx + (b.cx - a.cx) * k, cy: a.cy + (b.cy - a.cy) * k};
}

export function segAt(segments: Seg[], t: number): Seg | undefined {
  return segments.find((s) => t >= s.start && t < s.end) ?? segments[segments.length - 1];
}

type Box = {left: number; top: number; width: number; height: number};

/** Position the (larger) rough-cut frame inside `box` so the face sits at the centre-x / upper part of it. */
function videoTransform(p: ReelProps, t: number, box: Box, faceY: number) {
  const seg = segAt(p.segments, t);
  const cover = Math.max(box.width / p.videoW, box.height / p.videoH);
  let zoom = 1;
  let cx = 0.5;
  let cy = 0.42;
  if (seg) {
    const prog = clamp((t - seg.start) / Math.max(1e-6, seg.end - seg.start), 0, 1);
    if (seg.zoom) zoom = seg.zoom.from + (seg.zoom.to - seg.zoom.from) * EASE[seg.zoom.ease ?? 'linear'](prog);
    if (seg.reframe === 'face_track') ({cx, cy} = cropAt(seg.crop, seg.srcIn + (t - seg.start)));
  }
  const vw = p.videoW * cover * zoom;
  const vh = p.videoH * cover * zoom;
  const left = clamp(box.width / 2 - cx * vw, box.width - vw, 0);
  const top = clamp(box.height * faceY - cy * vh, box.height - vh, 0);
  return {left, top, vw, vh};
}

/** The camera: full frame, or (during a collage) a window that morphs in from full frame. */
const Presenter: React.FC<{p: ReelProps; t: number; mix: number}> = ({p, t, mix}) => {
  const full = {left: 0, top: 0, width: p.width, height: p.height};
  const pr = p.layout?.theme.presenter;
  const win = pr ? rectPx(pr, p.width, p.height) : full;
  const lerp = (a: number, b: number) => a + (b - a) * mix;
  const box = {left: lerp(full.left, win.left), top: lerp(full.top, win.top), width: lerp(full.width, win.width), height: lerp(full.height, win.height)};
  const {left, top, vw, vh} = videoTransform(p, t, box, lerp(0.4, 0.45));
  // tiny flash-free "settle" after a snap punch-in
  const seg = segAt(p.segments, t);
  const since = seg ? t - seg.start : 1;
  const settle = seg?.zoom?.ease === 'snap' ? interpolate(since, [0, 0.12], [1.03, 1], {extrapolateRight: 'clamp'}) : 1;
  return (
    <div
      style={{
        position: 'absolute', ...box, overflow: 'hidden', borderRadius: (pr?.radius ?? 0) * mix,
        outline: pr?.border ? `${pr.border * mix}px solid ${pr.border_color}` : undefined,
        boxShadow: pr?.shadow && mix > 0 ? `0 18px 50px rgba(0,0,0,${0.55 * mix})` : undefined,
      }}
    >
      <div style={{position: 'absolute', left, top, width: vw, height: vh, transform: `scale(${settle})`, transformOrigin: '50% 40%'}}>
        <OffthreadVideo src={staticFile(p.video)} muted style={{width: '100%', height: '100%'}} />
      </div>
    </div>
  );
};

const BRoll: React.FC<{seg: Seg; fps: number; width: number; height: number}> = ({seg, fps, width, height}) => {
  if (!seg.broll) return null;
  const {file, mode} = seg.broll;
  const style: React.CSSProperties =
    mode === 'split_top'
      ? {position: 'absolute', top: 0, left: 0, width, height: height / 2, objectFit: 'cover'}
      : mode === 'pip'
        ? {position: 'absolute', top: height * 0.14, right: 40, width: width * 0.42, borderRadius: 28, objectFit: 'cover', boxShadow: '0 12px 40px rgba(0,0,0,.5)'}
        : {position: 'absolute', inset: 0, width, height, objectFit: 'cover'};
  return (
    <Sequence from={Math.round(seg.start * fps)} durationInFrames={Math.max(1, Math.round((seg.end - seg.start) * fps))}>
      <OffthreadVideo src={staticFile(file)} muted startFrom={Math.round(seg.broll.in * fps)} style={style} />
    </Sequence>
  );
};

export const Reel: React.FC<ReelProps> = (p) => {
  const frame = useCurrentFrame();
  const t = frame / p.fps;
  const {p: mix, exit} = collageMix(p.layout, t, p.duration, p.fps);
  const theme = p.layout?.theme;
  const spans = useMemo(() => (p.layout ? collageSpans(p.layout) : []), [p.layout]);
  // during a collage the hook text takes the theme's title style
  const graphics = useMemo(
    () => p.graphics.map((g) => (theme && g.type === 'hook_text' && spans.some((s) => g.start >= s.start - 0.05 && g.start < s.end) ? {...g, look: theme.title} : g)),
    [p.graphics, theme, spans],
  );
  const tiles = p.layout && (mix > 0 || exit < 1) ? <CollageTiles layout={p.layout} exit={exit} fps={p.fps} width={p.width} height={p.height} /> : null;
  const tilesUnder = theme?.presenter.above_tiles ?? true;
  return (
    <AbsoluteFill style={{backgroundColor: theme?.background ?? 'black', overflow: 'hidden'}}>
      {tilesUnder && tiles}
      <Presenter p={p} t={t} mix={mix} />
      {!tilesUnder && tiles}
      {p.segments.filter((s) => s.broll).map((s, i) => (
        <BRoll key={i} seg={s} fps={p.fps} width={p.width} height={p.height} />
      ))}
      <GraphicsLayer graphics={graphics} brand={p.brand} fps={p.fps} width={p.width} height={p.height} style={p.captions.style} />
      {p.captions.enabled && (
        <Captions {...p.captions} top={theme && mix > 0.5 ? theme.captions_top : undefined} brand={p.brand} fps={p.fps} width={p.width} height={p.height} />
      )}
    </AbsoluteFill>
  );
};
