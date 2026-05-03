/**
 * Advanced Customization Examples
 * Real-world scenarios and solutions for modifying the premium video
 * 
 * Copy-paste these examples and adapt to your needs
 */

// ─────────────────────────────────────────────────────────────────────────────
// EXAMPLE 1: Custom Color Theme (E.g., Blue & Purple for FinTech)
// ─────────────────────────────────────────────────────────────────────────────

const CUSTOM_COLORS_FINTECH = {
  darkBlue: '#1a2654',      // Deep trust color
  lightBlue: '#0066ff',     // Vibrant, action-oriented
  purple: '#8b5cf6',        // Premium, modern
  white: '#ffffff',
  lightGray: '#e0e7ff',     // Secondary text
};

// Usage in component:
/*
export const FinTechExplainerVideo = () => {
  return (
    <div style={{ background: CUSTOM_COLORS_FINTECH.darkBlue }}>
      <MeshGradientBG 
        colors={[CUSTOM_COLORS_FINTECH.lightBlue, CUSTOM_COLORS_FINTECH.purple]}
        animationSpeed={0.6}
      />
      <GradientText
        text="FINTECH SOLUTIONS"
        gradient={`linear-gradient(135deg, ${CUSTOM_COLORS_FINTECH.lightBlue} 0%, ${CUSTOM_COLORS_FINTECH.purple} 100%)`}
      />
    </div>
  );
};
*/

// ─────────────────────────────────────────────────────────────────────────────
// EXAMPLE 2: Extended Duration - 90 Seconds Instead of 60
// ─────────────────────────────────────────────────────────────────────────────

/*
// In yojana_premium_video.jsx, modify composition:

export const YojanaMitraPremiumVideoExtended: React.FC = () => {
  return (
    <div style={{ background: COLORS.darkGreen, width: '100%', height: '100%' }}>
      <Sequence from={0} durationInFrames={400}>    {/* 400 frames = 13.3s */}
        <Scene1PremiumHero />
      </Sequence>
      <Sequence from={400} durationInFrames={400}>
        <Scene2ProblemStats />
      </Sequence>
      <Sequence from={800} durationInFrames={400}>
        <Scene3SolutionFeatures />
      </Sequence>
      <Sequence from={1200} durationInFrames={400}>
        <Scene4HowItWorks />
      </Sequence>
      <Sequence from={1600} durationInFrames={900}>   {/* Extended to 30s */}
        <Scene5FinalCTA />
      </Sequence>
    </div>
  );
};

// Then in remotion_root_enhanced.tsx add:
<Composition
  id="YojanaMitraPremium-90sec"
  component={YojanaMitraPremiumVideoExtended}
  durationInFrames={2700}    // 90 seconds @ 30fps
  fps={30}
  width={1920}
  height={1080}
/>
*/

// ─────────────────────────────────────────────────────────────────────────────
// EXAMPLE 3: Ultra-Premium Animation - Character-by-character Title Reveal
// ─────────────────────────────────────────────────────────────────────────────

import React from 'react';
import { interpolate, useCurrentFrame, useVideoConfig } from 'remotion';

export const UltraPremiumTitleReveal: React.FC<{
  text: string;
  fontSize?: number;
  delay?: number;
}> = ({ text, fontSize = 72, delay = 0 }) => {
  const frame = useCurrentFrame();

  return (
    <h1
      style={{
        fontSize,
        fontWeight: 900,
        margin: 0,
        letterSpacing: '-2px',
        background: 'linear-gradient(90deg, #f97316, #ea580c, #f97316)',
        backgroundSize: '200% 100%',
        animation: `gradient-shift 3s ease infinite`,
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        backgroundClip: 'text',
      }}
    >
      {text.split('').map((char, idx) => {
        const charDelay = delay + idx * 3;
        const charFrame = Math.max(0, frame - charDelay);
        const opacity = Math.min(1, charFrame / 10);
        const scale = interpolate(charFrame, [0, 10], [0.8, 1], {
          extrapolateRight: 'clamp',
        });

        return (
          <span
            key={idx}
            style={{
              display: 'inline-block',
              opacity,
              transform: `scale(${scale}) rotateX(${(1 - scale) * 40}deg)`,
              transformOrigin: 'bottom center',
              transition: 'all 0.1s ease',
            }}
          >
            {char}
          </span>
        );
      })}
      <style>{`
        @keyframes gradient-shift {
          0% { background-position: 0% center; }
          50% { background-position: 100% center; }
          100% { background-position: 0% center; }
        }
      `}</style>
    </h1>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// EXAMPLE 4: Animated Data Visualization - Bar Chart
// ─────────────────────────────────────────────────────────────────────────────

export const AnimatedBarChart: React.FC<{
  data: { label: string; value: number; color: string }[];
  maxValue?: number;
  duration?: number;
  delay?: number;
}> = ({ data, maxValue = 100, duration = 60, delay = 0 }) => {
  const frame = useCurrentFrame();

  const animFrame = Math.max(0, frame - delay);
  const progress = Math.min(1, animFrame / duration);

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'flex-end',
        gap: 20,
        height: 300,
      }}
    >
      {data.map((item, idx) => {
        const barHeight = (item.value / maxValue) * 300 * progress;

        return (
          <div
            key={idx}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <div
              style={{
                width: 60,
                height: barHeight,
                background: `linear-gradient(180deg, ${item.color} 0%, ${item.color}80 100%)`,
                borderRadius: '8px 8px 0 0',
                boxShadow: `0 0 20px ${item.color}40`,
                transition: 'all 0.1s ease',
              }}
            />
            <span
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: '#fff',
                textAlign: 'center',
              }}
            >
              {item.label}
            </span>
          </div>
        );
      })}
    </div>
  );
};

// Usage:
/*
<AnimatedBarChart
  data={[
    { label: 'Scheme A', value: 85, color: '#f97316' },
    { label: 'Scheme B', value: 70, color: '#2d6a4f' },
    { label: 'Scheme C', value: 90, color: '#c9ded0' },
  ]}
  delay={100}
/>
*/

// ─────────────────────────────────────────────────────────────────────────────
// EXAMPLE 5: Interactive-Style Toggle Effect
// ─────────────────────────────────────────────────────────────────────────────

export const AnimatedToggle: React.FC<{
  option1: string;
  option2: string;
  activeOption: 1 | 2;
  delay?: number;
  color1?: string;
  color2?: string;
}> = ({ option1, option2, activeOption, delay = 0, color1 = '#f97316', color2 = '#2d6a4f' }) => {
  const frame = useCurrentFrame();

  const toggleSlide = interpolate(
    frame - delay,
    [0, 30],
    [activeOption === 1 ? 0 : 100, activeOption === 1 ? 0 : 100],
    { extrapolateRight: 'clamp' }
  );

  return (
    <div
      style={{
        display: 'flex',
        background: 'rgba(255, 255, 255, 0.1)',
        borderRadius: 24,
        padding: 6,
        width: 'fit-content',
        position: 'relative',
        border: '1px solid rgba(255, 255, 255, 0.2)',
      }}
    >
      {/* Animated background slider */}
      <div
        style={{
          position: 'absolute',
          left: `${toggleSlide}%`,
          top: 6,
          height: 'calc(100% - 12px)',
          width: '50%',
          background: activeOption === 1 ? color1 : color2,
          borderRadius: 20,
          transition: 'all 0.3s ease',
          zIndex: 0,
        }}
      />

      {/* Options */}
      <button
        style={{
          position: 'relative',
          zIndex: 1,
          flex: 1,
          padding: '10px 24px',
          border: 'none',
          background: 'transparent',
          color: activeOption === 1 ? '#000' : '#fff',
          fontSize: 14,
          fontWeight: 600,
          cursor: 'pointer',
          transition: 'all 0.3s ease',
        }}
      >
        {option1}
      </button>

      <button
        style={{
          position: 'relative',
          zIndex: 1,
          flex: 1,
          padding: '10px 24px',
          border: 'none',
          background: 'transparent',
          color: activeOption === 2 ? '#000' : '#fff',
          fontSize: 14,
          fontWeight: 600,
          cursor: 'pointer',
          transition: 'all 0.3s ease',
        }}
      >
        {option2}
      </button>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// EXAMPLE 6: Animated Badge/Badge with Rotation
// ─────────────────────────────────────────────────────────────────────────────

export const AnimatedBadge: React.FC<{
  text: string;
  icon?: string;
  delay?: number;
  backgroundColor?: string;
  rotation?: boolean;
}> = ({
  text,
  icon = '⭐',
  delay = 0,
  backgroundColor = 'rgba(249, 115, 22, 0.2)',
  rotation = false,
}) => {
  const frame = useCurrentFrame();

  const scale = interpolate(
    frame - delay,
    [0, 20],
    [0, 1],
    { extrapolateRight: 'clamp' }
  );

  const rotate = rotation ? (frame * 2) % 360 : 0;

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        padding: '8px 16px',
        background: backgroundColor,
        border: '1px solid rgba(249, 115, 22, 0.5)',
        borderRadius: 20,
        fontSize: 12,
        fontWeight: 700,
        color: '#f97316',
        transform: `scale(${scale})`,
        transformOrigin: 'center',
        backdropFilter: 'blur(10px)',
      }}
    >
      <span
        style={{
          fontSize: 16,
          transform: `rotate(${rotate}deg)`,
          transition: 'transform 0.05s linear',
        }}
      >
        {icon}
      </span>
      {text}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// EXAMPLE 7: Timeline/Roadmap Animation
// ─────────────────────────────────────────────────────────────────────────────

export const AnimatedTimeline: React.FC<{
  steps: { title: string; description: string; icon: string }[];
  delay?: number;
}> = ({ steps, delay = 0 }) => {
  const frame = useCurrentFrame();

  return (
    <div
      style={{
        position: 'relative',
        maxWidth: 800,
      }}
    >
      {/* Vertical line */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: 0,
          bottom: 0,
          width: 2,
          background: 'linear-gradient(180deg, #f97316, transparent)',
          transform: 'translateX(-50%)',
        }}
      />

      {/* Steps */}
      <div>
        {steps.map((step, idx) => {
          const stepDelay = delay + idx * 40;
          const stepFrame = Math.max(0, frame - stepDelay);
          const opacity = Math.min(1, stepFrame / 20);
          const scale = interpolate(stepFrame, [0, 20], [0.8, 1], {
            extrapolateRight: 'clamp',
          });

          return (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                marginBottom: 60,
                opacity,
                transform: `scale(${scale})`,
                transformOrigin: 'center',
              }}
            >
              {/* Left content (even) */}
              {idx % 2 === 0 && (
                <>
                  <div style={{ flex: 1, textAlign: 'right', paddingRight: 40 }}>
                    <h4 style={{ margin: '0 0 8px 0', fontSize: 16, fontWeight: 700 }}>
                      {step.title}
                    </h4>
                    <p style={{ margin: 0, fontSize: 14, opacity: 0.8 }}>
                      {step.description}
                    </p>
                  </div>
                  <div
                    style={{
                      width: 60,
                      height: 60,
                      borderRadius: '50%',
                      background: 'linear-gradient(135deg, #f97316, #ea580c)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 28,
                      position: 'relative',
                      zIndex: 10,
                    }}
                  >
                    {step.icon}
                  </div>
                  <div style={{ flex: 1 }} />
                </>
              )}

              {/* Right content (odd) */}
              {idx % 2 === 1 && (
                <>
                  <div style={{ flex: 1 }} />
                  <div
                    style={{
                      width: 60,
                      height: 60,
                      borderRadius: '50%',
                      background: 'linear-gradient(135deg, #2d6a4f, #c9ded0)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 28,
                      position: 'relative',
                      zIndex: 10,
                    }}
                  >
                    {step.icon}
                  </div>
                  <div style={{ flex: 1, textAlign: 'left', paddingLeft: 40 }}>
                    <h4 style={{ margin: '0 0 8px 0', fontSize: 16, fontWeight: 700 }}>
                      {step.title}
                    </h4>
                    <p style={{ margin: 0, fontSize: 14, opacity: 0.8 }}>
                      {step.description}
                    </p>
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// EXAMPLE 8: Comparison Card (Before/After or Feature Comparison)
// ─────────────────────────────────────────────────────────────────────────────

export const ComparisonCard: React.FC<{
  title: string;
  before: string;
  after: string;
  icon: string;
  delay?: number;
}> = ({ title, before, after, icon, delay = 0 }) => {
  const frame = useCurrentFrame();

  const slideFrame = Math.max(0, frame - delay);
  const slide = interpolate(slideFrame, [0, 40], [-100, 0], {
    extrapolateRight: 'clamp',
  });
  const opacity = interpolate(slideFrame, [0, 20], [0, 1], {
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        opacity,
        transform: `translateX(${slide}px)`,
        background: 'rgba(255, 255, 255, 0.08)',
        border: '1px solid rgba(255, 255, 255, 0.15)',
        borderRadius: 16,
        padding: 30,
        backdropFilter: 'blur(20px)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 20, gap: 12 }}>
        <span style={{ fontSize: 32 }}>{icon}</span>
        <h3 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>{title}</h3>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* Before */}
        <div>
          <p style={{ fontSize: 12, fontWeight: 600, color: '#f97316', margin: '0 0 8px 0' }}>
            BEFORE
          </p>
          <p style={{ margin: 0, fontSize: 14, color: 'rgba(255, 255, 255, 0.7)' }}>
            {before}
          </p>
        </div>

        {/* After */}
        <div>
          <p style={{ fontSize: 12, fontWeight: 600, color: '#c9ded0', margin: '0 0 8px 0' }}>
            AFTER
          </p>
          <p style={{ margin: 0, fontSize: 14, color: 'rgba(255, 255, 255, 0.7)' }}>
            {after}
          </p>
        </div>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// EXAMPLE 9: Full Custom Scene Builder
// ─────────────────────────────────────────────────────────────────────────────

/*
// Create a new scene with all premium components

export const CustomScene: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      {/* Background */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'linear-gradient(135deg, #0b1a16 0%, #2d6a4f 100%)',
        }}
      />

      {/* Mesh gradient overlay */}
      <MeshGradientBG
        colors={['#f97316', '#2d6a4f', '#0b1a16']}
        animationSpeed={0.5}
      />

      {/* Floating particles */}
      <Particles count={30} color="#ffffff" opacity={0.1} />

      {/* Main content container */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '80px 60px',
          zIndex: 10,
          textAlign: 'center',
        }}
      >
        {/* Custom heading */}
        <GradientText
          text="Your Custom Title"
          gradient="linear-gradient(135deg, #ffffff 0%, #c9ded0 100%)"
          fontSize={64}
          fontWeight={800}
        />

        {/* Stats grid */}
        <div
          style={{
            marginTop: 80,
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 30,
            maxWidth: 1000,
          }}
        >
          <AnimatedStatBox
            icon="📊"
            title="Metric One"
            value={1000}
            delay={100}
          />
          <AnimatedStatBox
            icon="🎯"
            title="Metric Two"
            value={500}
            delay={150}
          />
          <AnimatedStatBox
            icon="✅"
            title="Metric Three"
            value={250}
            delay={200}
          />
        </div>

        {/* CTA */}
        <div style={{ marginTop: 80 }}>
          <EnhancedCTAButton
            text="Call to Action"
            delay={300}
          />
        </div>
      </div>
    </div>
  );
};

// Add to remotion_root_enhanced.tsx:
<Composition
  id="CustomScene"
  component={CustomScene}
  durationInFrames={600}
  fps={30}
  width={1920}
  height={1080}
/>

// Render:
npx remotion render remotion_root_enhanced.tsx CustomScene custom-scene.mp4
*/

// ─────────────────────────────────────────────────────────────────────────────
// EXAMPLE 10: Easing Playground - Test Different Animations
// ─────────────────────────────────────────────────────────────────────────────

export const EasingPlayground: React.FC = () => {
  const frame = useCurrentFrame();
  const fps = useVideoConfig().fps;

  // Different easings to compare
  const easeLinear = interpolate(frame, [0, 100], [0, 200]);
  const easeInQuad = interpolate(frame, [0, 100], [0, 200], {
    easing: Easing.inQuad,
  });
  const easeOutQuad = interpolate(frame, [0, 100], [0, 200], {
    easing: Easing.outQuad,
  });
  const easeInOutQuad = interpolate(frame, [0, 100], [0, 200], {
    easing: Easing.inOutQuad,
  });

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        background: '#0b1a16',
        padding: 40,
        color: '#fff',
        fontFamily: 'monospace',
        overflow: 'hidden',
      }}
    >
      <h1 style={{ margin: '20px 0' }}>Easing Playground (Frame: {frame})</h1>

      {/* Linear */}
      <div style={{ marginBottom: 40 }}>
        <p>Linear</p>
        <div
          style={{
            width: easeLinear,
            height: 20,
            background: '#f97316',
            borderRadius: 4,
          }}
        />
      </div>

      {/* Ease In Quad */}
      <div style={{ marginBottom: 40 }}>
        <p>Ease In Quad</p>
        <div
          style={{
            width: easeInQuad,
            height: 20,
            background: '#2d6a4f',
            borderRadius: 4,
          }}
        />
      </div>

      {/* Ease Out Quad */}
      <div style={{ marginBottom: 40 }}>
        <p>Ease Out Quad</p>
        <div
          style={{
            width: easeOutQuad,
            height: 20,
            background: '#c9ded0',
            borderRadius: 4,
          }}
        />
      </div>

      {/* Ease In Out Quad */}
      <div style={{ marginBottom: 40 }}>
        <p>Ease In Out Quad</p>
        <div
          style={{
            width: easeInOutQuad,
            height: 20,
            background: '#ea580c',
            borderRadius: 4,
          }}
        />
      </div>
    </div>
  );
};

import { interpolate, Easing, useCurrentFrame, useVideoConfig } from 'remotion';

export default {
  UltraPremiumTitleReveal,
  AnimatedBarChart,
  AnimatedToggle,
  AnimatedBadge,
  AnimatedTimeline,
  ComparisonCard,
  EasingPlayground,
};
