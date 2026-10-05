import React from 'react';
import {Composition, Still} from 'remotion';
import {Animatic, ANIMATIC_FRAMES} from './Animatic';
import {Cover} from './Cover';
import {Reel} from './Reel';
import type {CoverProps, ReelProps} from './types';

const brand = {primary: '#5B5BF7', accent: '#FFD23F', text: '#FFFFFF', shadow: '#000000', handle: '@handle'};

// Studio preview defaults; real renders pass --props from pipeline/render.py
const defaultReel: ReelProps = {
  video: 'work/rough.mp4', fps: 30, width: 1080, height: 1920, duration: 6, videoW: 1080, videoH: 1920,
  segments: [{start: 0, end: 6, srcIn: 0, reframe: 'center', zoom: {from: 1, to: 1.06, ease: 'easeInOut'}, crop: [], broll: null}],
  captions: {enabled: true, style: 'bip-raw', size: 1, maxWords: 3, words: [
    {text: 'This', start: 0.2, end: 0.5}, {text: 'took', start: 0.5, end: 0.8}, {text: '3', start: 0.8, end: 1.1, highlight: true},
    {text: 'hours.', start: 1.1, end: 1.6},
  ]},
  graphics: [
    {type: 'hook_text', text: '3 hours, not 3 weeks', start: 0, end: 2.5},
    {type: 'badge', text: 'Day 12', start: 0, end: 2.5},
    {type: 'diagram', spec: 'request -> model -> response', start: 2.6, end: 6},
  ],
  brand,
};

export const Root: React.FC = () => (
  <>
    <Composition
      id="Reel"
      component={Reel}
      defaultProps={defaultReel}
      fps={30}
      width={1080}
      height={1920}
      durationInFrames={180}
      calculateMetadata={({props}) => ({
        durationInFrames: Math.max(1, Math.round(props.duration * props.fps)),
        fps: props.fps,
        width: props.width,
        height: props.height,
      })}
    />
    <Composition id="Animatic" component={Animatic} fps={30} width={1080} height={1920} durationInFrames={ANIMATIC_FRAMES} />
    <Still
      id="Cover"
      component={Cover}
      width={1080}
      height={1920}
      defaultProps={{image: 'work/cover_frame.jpg', hook: 'This took 3 hours', badge: 'Day 12', brand, style: 'bip-raw'} as CoverProps}
    />
  </>
);
