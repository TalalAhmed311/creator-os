import React, {useMemo} from 'react';
import {AbsoluteFill, Easing, Img, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame} from 'remotion';
import type {CollageTile, Layout, Rect, VideoTheme} from './types';

/** Collage layout: image tiles around (or behind) the presenter. Theme packs live in brain/video-themes/. */

type Span = {start: number; end: number};
type Run = {slot: number; tile: CollageTile; start: number; end: number; delay: number};

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const ease = Easing.inOut(Easing.cubic);
const SWAP_OVERLAP = 0.35; // old tile stays underneath while the new one enters

/** Contiguous blocks form one span: the presenter morphs into the window once per span, not per block. */
export function collageSpans(layout: Layout): Span[] {
  const spans: Span[] = [];
  for (const b of [...layout.blocks].sort((a, c) => a.start - c.start)) {
    const last = spans[spans.length - 1];
    if (last && b.start - last.end < 0.05) last.end = Math.max(last.end, b.end);
    else spans.push({start: b.start, end: b.end});
  }
  return spans;
}

/** p: 0 = plain full-frame reel, 1 = full collage. exit: tile opacity while the span closes. */
export function collageMix(layout: Layout | null | undefined, t: number, duration: number, fps: number) {
  if (!layout) return {p: 0, exit: 1};
  const span = collageSpans(layout).find((s) => t >= s.start && t < s.end);
  if (!span) return {p: 0, exit: 1};
  const m = Math.max(1e-3, layout.theme.morph);
  const into = span.start < 1 / fps ? 1 : (t - span.start) / m; // a collage on frame 0 is fully there on frame 0
  const out = span.end >= duration - 1 / fps ? 1 : (span.end - t) / m;
  return {p: ease(clamp(Math.min(into, out), 0, 1)), exit: clamp(out, 0, 1)};
}

const sameTile = (a: CollageTile | null, b: CollageTile | null) => !!a && !!b && a.file === b.file && a.in === b.in;

/** Per slot, merge consecutive blocks showing the same file into one run (so Ken Burns and video don't restart). */
export function tileRuns(layout: Layout): Run[] {
  const {stagger} = layout.theme.tiles;
  const runs: Run[] = [];
  const blocks = [...layout.blocks].sort((a, c) => a.start - c.start);
  for (const span of collageSpans(layout)) {
    const open: (Run | null)[] = layout.theme.slots.map(() => null);
    for (const b of blocks.filter((x) => x.start >= span.start - 1e-6 && x.end <= span.end + 1e-6)) {
      open.forEach((run, slot) => {
        const tile = b.tiles[slot] ?? null;
        if (run && sameTile(run.tile, tile)) {
          run.end = b.end;
          return;
        }
        if (run) run.end = tile ? Math.min(b.start + SWAP_OVERLAP, span.end) : b.start;
        open[slot] = tile ? {slot, tile, start: b.start, end: b.end, delay: b.start === span.start ? slot * stagger : 0} : null;
        if (open[slot]) runs.push(open[slot]!);
      });
    }
  }
  return runs.sort((a, b) => a.start - b.start); // later runs paint on top of the ones they replace
}

export function rectPx(r: Rect, width: number, height: number, inset = 0) {
  return {left: r.x * width + inset, top: r.y * height + inset, width: r.w * width - inset * 2, height: r.h * height - inset * 2};
}

const Tile: React.FC<{run: Run; theme: VideoTheme; fps: number; width: number; height: number}> = ({run, theme, fps, width, height}) => {
  const f = useCurrentFrame();
  const tt = theme.tiles;
  const instant = run.start < 1 / fps || tt.enter === 'cut';
  const local = f - Math.round(run.delay * fps);
  if (local < 0 && !instant) return null;
  const e = instant ? 1 : spring({frame: local, fps, config: {damping: 15, stiffness: 170, mass: 0.7}});
  const dur = Math.max(1, (run.end - run.start) * fps);
  const kb = tt.motion === 'ken_burns' ? interpolate(f, [0, dur], [1, tt.ken_burns], {extrapolateRight: 'clamp'}) : 1;
  const slot = theme.slots[run.slot];
  const box = rectPx(slot, width, height, theme.gap / 2);
  const rot = slot.rotate ?? 0;
  const enter =
    tt.enter === 'pop'
      ? `scale(${interpolate(e, [0, 1], [0.86, 1])})`
      : tt.enter === 'slide'
        ? `translateY(${(1 - e) * box.height * 0.35}px)`
        : tt.enter === 'drop'
          ? `scale(${interpolate(e, [0, 1], [1.35, 1])}) rotate(${(1 - e) * 10}deg)`
          : '';
  const media: React.CSSProperties = {
    width: '100%', height: '100%', objectFit: 'cover', objectPosition: `${run.tile.fx * 100}% ${run.tile.fy * 100}%`,
    transform: `scale(${kb})`, filter: `saturate(${tt.saturate}) contrast(${tt.contrast}) brightness(${tt.brightness})`,
  };
  return (
    <div
      style={{
        position: 'absolute', ...box, overflow: 'hidden', borderRadius: tt.radius, opacity: Math.min(1, e * 1.4),
        border: tt.border ? `${tt.border}px solid ${tt.border_color}` : undefined, background: tt.border_color,
        boxShadow: tt.shadow ? '0 18px 48px rgba(0,0,0,.5)' : undefined, transform: `rotate(${rot}deg) ${enter}`,
      }}
    >
      {run.tile.video ? (
        <OffthreadVideo src={staticFile(run.tile.file)} muted startFrom={Math.round(run.tile.in * fps)} style={media} />
      ) : (
        <Img src={staticFile(run.tile.file)} style={media} />
      )}
      {tt.dim > 0 && <AbsoluteFill style={{background: `rgba(0,0,0,${tt.dim})`}} />}
    </div>
  );
};

export const CollageTiles: React.FC<{layout: Layout; exit: number; fps: number; width: number; height: number}> = ({layout, exit, fps, width, height}) => {
  const runs = useMemo(() => tileRuns(layout), [layout]);
  return (
    <AbsoluteFill style={{opacity: exit}}>
      {runs.map((r, i) => (
        <Sequence key={i} from={Math.round(r.start * fps)} durationInFrames={Math.max(1, Math.round((r.end - r.start) * fps))} layout="none">
          <Tile run={r} theme={layout.theme} fps={fps} width={width} height={height} />
        </Sequence>
      ))}
      {layout.theme.tiles.scrim > 0 && (
        // keeps the title readable over busy images (screenshots, headlines)
        <AbsoluteFill style={{background: `linear-gradient(rgba(0,0,0,${layout.theme.tiles.scrim}) ${layout.theme.title.top * 100 - 4}%, transparent ${layout.theme.title.top * 100 + 14}%)`}} />
      )}
    </AbsoluteFill>
  );
};
