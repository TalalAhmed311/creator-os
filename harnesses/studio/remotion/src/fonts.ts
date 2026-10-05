import {loadFont as loadMontserrat} from '@remotion/google-fonts/Montserrat';
import {loadFont as loadInter} from '@remotion/google-fonts/Inter';
import {loadFont as loadMono} from '@remotion/google-fonts/JetBrainsMono';
import type {Preset} from './types';

const montserrat = loadMontserrat('normal', {weights: ['800', '900'], subsets: ['latin']});
const inter = loadInter('normal', {weights: ['500', '700', '800'], subsets: ['latin']});
const mono = loadMono('normal', {weights: ['500', '700'], subsets: ['latin']});

export const FONTS = {
  heavy: montserrat.fontFamily,
  clean: inter.fontFamily,
  mono: mono.fontFamily,
};

export const captionFont = (style: Preset) => (style === 'bip-raw' ? FONTS.heavy : FONTS.clean);
