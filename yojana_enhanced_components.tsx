/**
 * YojanaMitra Enhanced Explainer Video Components
 * Advanced animations and professional Polish
 * 
 * Features:
 * - Mesh gradient backgrounds
 * - Animated counters
 * - Enhanced typography
 * - Advanced easing functions
 * - Particle effects
 */

import React from 'react';
import {
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Easing,
} from 'remotion';

// ─────────────────────────────────────────────────────────────────────────────
// MESH GRADIENT BACKGROUND
// High-end animated background used in modern SaaS videos
// ─────────────────────────────────────────────────────────────────────────────

export const MeshGradientBG: React.FC<{ 
  colors: string[];
  animationSpeed?: number;
}> = ({ colors, animationSpeed = 1 }) => {
  const frame = useCurrentFrame();
  const fps = useVideoConfig().fps;
  
  const angle = (frame * animationSpeed * 360) / (fps * 10);
  
  return (
    <svg
      viewBox="0 0 1920 1080"
      style={{
        position: 'absolute',
        width: '100%',
        height: '100%',
        top: 0,
        left: 0,
      }}
      preserveAspectRatio="xMidYMid slice"
    >
      <defs>
        <radialGradient id="grad1" r="50%">
          <stop offset="0%" stopColor={colors[0]} stopOpacity="0.8" />
          <stop offset="100%" stopColor={colors[0]} stopOpacity="0" />
        </radialGradient>
        <radialGradient id="grad2" r="50%">
          <stop offset="0%" stopColor={colors[1]} stopOpacity="0.6" />
          <stop offset="100%" stopColor={colors[1]} stopOpacity="0" />
        </radialGradient>
        <radialGradient id="grad3" r="50%">
          <stop offset="0%" stopColor={colors[2] || colors[0]} stopOpacity="0.7" />
          <stop offset="100%" stopColor={colors[2] || colors[0]} stopOpacity="0" />
        </radialGradient>
      </defs>
      
      {/* Animated circles */}
      <circle
        cx={960 + 400 * Math.cos((angle * Math.PI) / 180)}
        cy={540 + 300 * Math.sin((angle * Math.PI) / 180)}
        r="500"
        fill="url(#grad1)"
      />
      <circle
        cx={960 + 400 * Math.cos(((angle + 120) * Math.PI) / 180)}
        cy={540 + 300 * Math.sin(((angle + 120) * Math.PI) / 180)}
        r="450"
        fill="url(#grad2)"
      />
      <circle
        cx={960 + 300 * Math.cos(((angle + 240) * Math.PI) / 180)}
        cy={540 + 250 * Math.sin(((angle + 240) * Math.PI) / 180)}
        r="400"
        fill="url(#grad3)"
      />
    </svg>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// ANIMATED COUNTER
// Counts up from 0 to a final number with smooth animation
// ─────────────────────────────────────────────────────────────────────────────

export const AnimatedCounter: React.FC<{
  from?: number;
  to: number;
  framesDelay?: number;
  framesCountDuration?: number;
  fontSize?: number;
  suffix?: string;
  prefix?: string;
}> = ({
  from = 0,
  to,
  framesDelay = 0,
  framesCountDuration = 60,
  fontSize = 48,
  suffix = '',
  prefix = '',
}) => {
  const frame = useCurrentFrame();
  
  const countFrame = Math.max(0, frame - framesDelay);
  const progress = Math.min(1, countFrame / framesCountDuration);
  const current = Math.round(from + (to - from) * progress);

  return (
    <span style={{ fontSize, fontWeight: 'bold', color: 'inherit' }}>
      {prefix}
      {current.toLocaleString()}
      {suffix}
    </span>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// ANIMATED STAT BOX
// Professional stat display with icon and counter
// ─────────────────────────────────────────────────────────────────────────────

export const AnimatedStatBox: React.FC<{
  icon: string;
  title: string;
  value: number;
  suffix?: string;
  delay?: number;
  color?: string;
}> = ({ icon, title, value, suffix = '', delay = 0, color = '#f97316' }) => {
  const frame = useCurrentFrame();
  const fps = useVideoConfig().fps;

  const scaleFrame = Math.max(0, frame - delay);
  const scale = spring({
    frame: scaleFrame,
    fps,
    config: { damping: 15, mass: 1, tension: 80 },
    from: 0,
    to: 1,
  });

  const opacity = interpolate(
    scaleFrame,
    [0, 20],
    [0, 1],
    { extrapolateRight: 'clamp' }
  );

  return (
    <div
      style={{
        opacity,
        transform: `scale(${scale})`,
        textAlign: 'center',
        padding: '30px',
        background: 'rgba(255, 255, 255, 0.1)',
        backdropFilter: 'blur(20px)',
        borderRadius: 16,
        border: '1px solid rgba(255, 255, 255, 0.2)',
        flex: 1,
      }}
    >
      <div style={{ fontSize: 44, marginBottom: 15, filter: 'drop-shadow(0 5px 10px rgba(0,0,0,0.2))' }}>
        {icon}
      </div>
      <div style={{ fontSize: 32, fontWeight: 700, color: color, marginBottom: 8 }}>
        <AnimatedCounter to={value} suffix={suffix} framesCountDuration={60} />
      </div>
      <p style={{ fontSize: 14, color: 'rgba(255, 255, 255, 0.7)', margin: 0 }}>
        {title}
      </p>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// ANIMATED TEXT REVEAL
// Premium text reveal with staggered character animation
// ─────────────────────────────────────────────────────────────────────────────

export const AnimatedTextReveal: React.FC<{
  text: string;
  fontSize?: number;
  fontWeight?: number;
  color?: string;
  delay?: number;
  duration?: number;
  staggerDelay?: number;
}> = ({
  text,
  fontSize = 24,
  fontWeight = 400,
  color = '#ffffff',
  delay = 0,
  duration = 40,
  staggerDelay = 2,
}) => {
  const frame = useCurrentFrame();

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
      {text.split(' ').map((word, wordIdx) => (
        <div key={wordIdx} style={{ display: 'flex', gap: '2px' }}>
          {word.split('').map((char, charIdx) => {
            const charDelay = delay + wordIdx * staggerDelay + charIdx * (staggerDelay / word.length);
            const charFrame = Math.max(0, frame - charDelay);
            const charDuration = duration / word.length;
            
            const opacity = Math.min(1, charFrame / charDuration);
            const yTranslate = interpolate(charFrame, [0, charDuration], [20, 0], {
              extrapolateRight: 'clamp',
            });

            return (
              <span
                key={charIdx}
                style={{
                  opacity,
                  transform: `translateY(${yTranslate}px)`,
                  fontSize,
                  fontWeight,
                  color,
                  display: 'inline-block',
                  transitions: 'all 0.3s ease',
                }}
              >
                {char}
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// GRADIENT TEXT
// Text with animated gradient fill
// ─────────────────────────────────────────────────────────────────────────────

export const GradientText: React.FC<{
  text: string;
  gradient: string;
  fontSize?: number;
  fontWeight?: number;
}> = ({ text, gradient, fontSize = 48, fontWeight = 700 }) => {
  return (
    <h1
      style={{
        fontSize,
        fontWeight,
        margin: 0,
        background: gradient,
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        backgroundClip: 'text',
        fontFamily: 'Plus Jakarta Sans, sans-serif',
      }}
    >
      {text}
    </h1>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// PARTICLE EFFECT
// Floating particles for premium background animations
// ─────────────────────────────────────────────────────────────────────────────

export const Particles: React.FC<{
  count?: number;
  color?: string;
  opacity?: number;
}> = ({ count = 20, color = '#f97316', opacity = 0.3 }) => {
  const frame = useCurrentFrame();
  const fps = useVideoConfig().fps;

  const particles = Array.from({ length: count }, (_, i) => {
    const randomX = (Math.sin(i * 12.9898) * 0.5 + 0.5) * 1920;
    const randomY = (Math.sin(i * 78.233) * 0.5 + 0.5) * 1080;
    const randomSpeed = (Math.sin(i * 45.164) * 0.5 + 0.5) * 2 + 1;
    const randomSize = (Math.sin(i * 23.456) * 0.5 + 0.5) * 4 + 1;

    const y = (randomY + (frame * randomSpeed) % 1080 + 1080) % 1080;

    return (
      <circle
        key={i}
        cx={randomX}
        cy={y}
        r={randomSize}
        fill={color}
        opacity={opacity}
      />
    );
  });

  return (
    <svg
      style={{
        position: 'absolute',
        width: '100%',
        height: '100%',
        top: 0,
        left: 0,
      }}
      viewBox="0 0 1920 1080"
      preserveAspectRatio="none"
    >
      {particles}
    </svg>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// ANIMATED SLIDE-IN BOX
// Professional card that slides and fades in
// ─────────────────────────────────────────────────────────────────────────────

export const AnimatedSlideBox: React.FC<{
  from: 'left' | 'right' | 'top' | 'bottom';
  delay?: number;
  duration?: number;
  children: React.ReactNode;
  background?: string;
  border?: string;
  borderRadius?: number;
  padding?: number;
}> = ({
  from,
  delay = 0,
  duration = 30,
  children,
  background = 'rgba(255, 255, 255, 0.1)',
  border = '1px solid rgba(255, 255, 255, 0.2)',
  borderRadius = 16,
  padding = 30,
}) => {
  const frame = useCurrentFrame();
  
  const animFrame = Math.max(0, frame - delay);
  const progress = Math.min(1, animFrame / duration);

  let transform = 'translate(0, 0)';
  
  if (from === 'left') {
    transform = `translateX(${-100 + progress * 100}px)`;
  } else if (from === 'right') {
    transform = `translateX(${100 - progress * 100}px)`;
  } else if (from === 'top') {
    transform = `translateY(${-100 + progress * 100}px)`;
  } else if (from === 'bottom') {
    transform = `translateY(${100 - progress * 100}px)`;
  }

  return (
    <div
      style={{
        background,
        border,
        borderRadius,
        padding,
        opacity: progress,
        transform,
        transition: 'all 0.3s ease',
      }}
    >
      {children}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// BLINKING CURSOR (for typing effect)
// ─────────────────────────────────────────────────────────────────────────────

export const BlinkingCursor: React.FC<{
  color?: string;
  size?: number;
}> = ({ color = '#f97316', size = 2 }) => {
  const frame = useCurrentFrame();
  const opacity = frame % 30 < 15 ? 1 : 0;
  
  return (
    <span
      style={{
        display: 'inline-block',
        width: size,
        height: '1em',
        background: color,
        marginLeft: 4,
        opacity,
        verticalAlign: 'text-bottom',
      }}
    />
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// EASING FUNCTIONS
// Professional easing curves for smooth animations
// ─────────────────────────────────────────────────────────────────────────────

export const EasingFunctions = {
  easeOutElastic: (t: number): number => {
    const c5 = (2 * Math.PI) / 4.5;
    return t === 0 ? 0 : t === 1 ? 1 : Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c5) + 1;
  },

  easeOutBounce: (t: number): number => {
    const n1 = 7.5625;
    const d1 = 2.75;

    if (t < 1 / d1) {
      return n1 * t * t;
    } else if (t < 2 / d1) {
      return n1 * (t -= 1.5 / d1) * t + 0.75;
    } else if (t < 2.5 / d1) {
      return n1 * (t -= 2.25 / d1) * t + 0.9375;
    } else {
      return n1 * (t -= 2.625 / d1) * t + 0.984375;
    }
  },

  easeInOutCubic: (t: number): number => {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  },

  easeOutQuad: (t: number): number => {
    return 1 - (1 - t) * (1 - t);
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// ENHANCED CTA BUTTON
// Professional button with hover effects and glow
// ─────────────────────────────────────────────────────────────────────────────

export const EnhancedCTAButton: React.FC<{
  text: string;
  delay?: number;
  color?: string;
  glowColor?: string;
}> = ({ text, delay = 0, color = '#f97316', glowColor = 'rgba(249, 115, 22, 0.3)' }) => {
  const frame = useCurrentFrame();
  const fps = useVideoConfig().fps;

  const scale = spring({
    frame: Math.max(0, frame - delay),
    fps,
    config: { damping: 10, mass: 1, tension: 100 },
    from: 0.8,
    to: 1,
  });

  const glowPulse = Math.sin((frame * 0.02) * Math.PI) * 0.5 + 0.5;

  return (
    <div
      style={{
        position: 'relative',
        display: 'inline-block',
        transform: `scale(${scale})`,
      }}
    >
      <button
        style={{
          background: `linear-gradient(135deg, ${color} 0%, ${
            color === '#f97316' ? '#ea580c' : color
          } 100%)`,
          color: '#ffffff',
          border: 'none',
          padding: '18px 56px',
          fontSize: 18,
          fontWeight: 700,
          borderRadius: 12,
          cursor: 'pointer',
          boxShadow: `0 20px 60px ${color}40`,
          fontFamily: 'Plus Jakarta Sans, sans-serif',
          letterSpacing: '0.5px',
          transition: 'transform 0.3s ease',
          transform: `scale(${1 + glowPulse * 0.02})`,
        }}
      >
        {text}
      </button>

      {/* Glow effect */}
      <div
        style={{
          position: 'absolute',
          inset: -10,
          background: `radial-gradient(circle, ${glowColor} 0%, transparent 70%)`,
          borderRadius: 12,
          opacity: 0.5 + glowPulse * 0.3,
          filter: 'blur(20px)',
          pointerEvents: 'none',
        }}
      />
    </div>
  );
};

export default {
  MeshGradientBG,
  AnimatedCounter,
  AnimatedStatBox,
  AnimatedTextReveal,
  GradientText,
  Particles,
  AnimatedSlideBox,
  BlinkingCursor,
  EasingFunctions,
  EnhancedCTAButton,
};
