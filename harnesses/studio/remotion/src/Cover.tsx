import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import {FONTS} from './fonts';
import type {CoverProps} from './types';

/** Reel cover: strongest frame + hook text (text kept inside the grid-safe centre area). */
export const Cover: React.FC<CoverProps> = ({image, hook, badge, brand, style}) => {
  const heavy = style === 'bip-raw';
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <Img src={staticFile(image)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(0,0,0,0) 35%, rgba(0,0,0,.75) 100%)'}} />
      {badge && (
        <div style={{position: 'absolute', top: 250, left: 60, background: brand.primary, color: '#fff', fontFamily: FONTS.heavy, fontWeight: 900, fontSize: 56, padding: '12px 30px', borderRadius: 999}}>
          {badge}
        </div>
      )}
      <div style={{position: 'absolute', left: 70, right: 70, top: 1920 * 0.5, display: 'flex', justifyContent: 'center'}}>
        <div
          style={{
            fontFamily: heavy ? FONTS.heavy : FONTS.clean, fontWeight: 900, fontSize: 104, lineHeight: 1.05, color: '#fff',
            textAlign: 'center', textTransform: heavy ? 'uppercase' : 'none', WebkitTextStroke: `12px ${brand.shadow}`,
            paintOrder: 'stroke fill', textShadow: '0 10px 30px rgba(0,0,0,.5)',
          }}
        >
          {hook.split(' ').map((w, i) => (
            <span key={i} style={{color: /\d/.test(w) || i === hook.split(' ').length - 1 ? brand.accent : '#fff'}}>{w} </span>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
