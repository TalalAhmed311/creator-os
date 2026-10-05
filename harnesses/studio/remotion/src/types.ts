export type Ease = 'linear' | 'easeIn' | 'easeOut' | 'easeInOut' | 'snap';
export type Preset = 'bip-raw' | 'ai-explained' | 'talking-head-basic';

export type CropPoint = {t: number; cx: number; cy: number};

/** One cut on the output timeline (times in seconds). */
export type Seg = {
  start: number; // output time
  end: number;
  srcIn: number; // source time at `start`
  reframe: 'face_track' | 'center' | 'none';
  zoom: {from: number; to: number; ease?: Ease} | null;
  crop: CropPoint[]; // source-time samples for this segment
  broll: {file: string; in: number; mode: 'full' | 'split_top' | 'pip'} | null;
};

export type Word = {text: string; start: number; end: number; highlight?: boolean};

export type Graphic = {
  type: 'hook_text' | 'badge' | 'callout' | 'diagram' | 'series_tag' | 'intro_sting' | 'lower_third' | 'emoji_pop';
  text?: string;
  spec?: string;
  start: number;
  end: number;
  position?: 'top' | 'middle' | 'bottom' | 'top_left' | 'top_right';
  look?: ThemeTitle; // set by Reel when a collage is on screen: hook text takes the theme's title style
};

/** Fractions of the output frame; x/y = top-left corner. */
export type Rect = {x: number; y: number; w: number; h: number; rotate?: number};

export type ThemeTitle = {top: number; size: number; font: 'clean' | 'heavy'; weight: number; color: string; stroke: number; upper: boolean};

/** brain/video-themes/<name>/theme.json, merged with defaults by harnesses/studio/collage.py (snake_case kept as-is). */
export type VideoTheme = {
  name: string;
  background: string;
  gap: number;
  slots: Rect[];
  presenter: Rect & {radius: number; border: number; border_color: string; shadow: boolean; above_tiles: boolean};
  tiles: {
    radius: number; border: number; border_color: string; shadow: boolean;
    motion: 'ken_burns' | 'none'; ken_burns: number; enter: 'pop' | 'slide' | 'drop' | 'cut'; stagger: number;
    saturate: number; contrast: number; brightness: number; dim: number; scrim: number; // scrim: top gradient behind the title
  };
  title: ThemeTitle;
  captions_top: number;
  morph: number; // seconds
};

export type CollageTile = {file: string; video: boolean; in: number; fx: number; fy: number};
export type CollageBlock = {start: number; end: number; tiles: (CollageTile | null)[]}; // output time
export type Layout = {theme: VideoTheme; blocks: CollageBlock[]};

export type Brand = {
  primary: string;
  accent: string;
  text: string;
  shadow: string;
  handle: string;
};

export type ReelProps = {
  video: string; // path relative to --public-dir (project root)
  fps: number;
  width: number;
  height: number;
  duration: number; // seconds
  videoW: number; // pixel size of the rough cut
  videoH: number;
  segments: Seg[];
  captions: {enabled: boolean; style: Preset; size: number; maxWords: number; words: Word[]};
  graphics: Graphic[];
  layout?: Layout | null;
  brand: Brand;
};

export type CoverProps = {
  image: string;
  hook: string;
  badge?: string | null;
  brand: Brand;
  style: Preset;
};
