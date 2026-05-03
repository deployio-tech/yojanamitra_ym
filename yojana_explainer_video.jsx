/**
 * YojanaMitra SaaS Explainer Video
 * Built with Remotion - Programmatic React-based Video
 * 
 * Inspired by professional SaaS explainer video structure
 * - Gradient backgrounds
 * - Animated text reveals
 * - Floating icons with subtle motion
 * - Smooth transitions between scenes
 * - Professional color scheme (Green/Orange/White)
 */

import React from 'react';
import {
  Composition,
  Sequence,
  useVideoConfig,
  useCurrentFrame,
  useWindowFrame,
  css,
  spring,
  interpolate,
} from 'remotion';

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 1: INTRO WITH ANIMATED TITLE
// ─────────────────────────────────────────────────────────────────────────────

const Scene1Intro = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Background gradient
  const bgStyle = {
    position: 'absolute',
    width: '100%',
    height: '100%',
    background: 'linear-gradient(135deg, #0b1a16 0%, #1a3a2e 50%, #0d2818 100%)',
  };

  // Main title animation
  const titleOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: 'clamp' });
  const titleScale = spring({
    frame,
    fps,
    config: { damping: 20, mass: 1.5, tension: 100 },
    from: 0.8,
    to: 1,
  });

  // Subtitle animation
  const subtitleOpacity = interpolate(frame, [30, 50], [0, 1], { extrapolateRight: 'clamp' });
  const subtitleY = interpolate(frame, [30, 60], [20, 0]);

  return (
    <div style={bgStyle}>
      {/* Animated Gradient Orbs in background */}
      <div
        style={{
          position: 'absolute',
          width: 400,
          height: 400,
          right: -100,
          top: -50,
          background: 'radial-gradient(circle, rgba(249, 115, 22, 0.1) 0%, transparent 70%)',
          borderRadius: '50%',
          filter: 'blur(40px)',
          animation: 'float 6s ease-in-out infinite',
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: 300,
          height: 300,
          left: -50,
          bottom: 50,
          background: 'radial-gradient(circle, rgba(45, 106, 79, 0.2) 0%, transparent 70%)',
          borderRadius: '50%',
          filter: 'blur(40px)',
          animation: 'float 8s ease-in-out infinite reverse',
        }}
      />

      {/* Main Title */}
      <div
        style={{
          position: 'absolute',
          top: '30%',
          left: '50%',
          transform: `translate(-50%, -50%) scale(${titleScale})`,
          opacity: titleOpacity,
          textAlign: 'center',
          zIndex: 10,
        }}
      >
        <h1
          style={{
            fontSize: 96,
            fontWeight: 800,
            color: '#ffffff',
            margin: 0,
            letterSpacing: '-2px',
            textShadow: '0 20px 40px rgba(0, 0, 0, 0.3)',
            fontFamily: 'Plus Jakarta Sans, sans-serif',
          }}
        >
          YOJANA
        </h1>
        <h1
          style={{
            fontSize: 96,
            fontWeight: 800,
            color: '#f97316',
            margin: '10px 0 0 0',
            letterSpacing: '-2px',
            textShadow: '0 20px 40px rgba(249, 115, 22, 0.4)',
            fontFamily: 'Plus Jakarta Sans, sans-serif',
          }}
        >
          MITRA
        </h1>
      </div>

      {/* Subtitle */}
      <div
        style={{
          position: 'absolute',
          bottom: '30%',
          left: '50%',
          transform: `translate(-50%, 0)`,
          opacity: subtitleOpacity,
          textAlign: 'center',
          zIndex: 10,
          marginTop: subtitleY,
        }}
      >
        <p
          style={{
            fontSize: 28,
            color: 'rgba(255, 255, 255, 0.8)',
            margin: 0,
            fontFamily: 'Plus Jakarta Sans, sans-serif',
            fontWeight: 400,
            letterSpacing: '0.5px',
          }}
        >
          Find What's Truly Yours
        </p>
      </div>

      {/* Scroll hint animation */}
      <div
        style={{
          position: 'absolute',
          bottom: 40,
          left: '50%',
          transform: 'translateX(-50%)',
          textAlign: 'center',
          opacity: interpolate(frame, [100, 120], [1, 0], { extrapolateRight: 'clamp' }),
        }}
      >
        <p
          style={{
            fontSize: 12,
            color: 'rgba(255, 240, 200, 0.6)',
            letterSpacing: '2px',
            textTransform: 'uppercase',
            margin: 0,
            marginBottom: 10,
          }}
        >
          Scroll to begin
        </p>
        <div
          style={{
            fontSize: 20,
            color: 'rgba(255, 220, 140, 0.55)',
            animation: 'scrollBounce 1.5s ease-in-out infinite',
          }}
        >
          ↓
        </div>
      </div>

      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(20px); }
        }
        @keyframes scrollBounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(8px); }
        }
      `}</style>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 2: THE PROBLEM
// ─────────────────────────────────────────────────────────────────────────────

const Scene2Problem = () => {
  const frame = useCurrentFrame();

  const bgStyle = {
    position: 'absolute',
    width: '100%',
    height: '100%',
    background: 'linear-gradient(135deg, #ffffff 0%, #f5f5f0 100%)',
  };

  // Text reveal with typewriter effect
  const textOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const textY = interpolate(frame, [0, 40], [40, 0]);

  // Icon animations
  const icon1Scale = spring({
    frame,
    fps: 30,
    config: { damping: 15, mass: 1, tension: 80 },
    delay: 50,
    from: 0,
    to: 1,
  });

  const icon2Scale = spring({
    frame,
    fps: 30,
    config: { damping: 15, mass: 1, tension: 80 },
    delay: 70,
    from: 0,
    to: 1,
  });

  const icon3Scale = spring({
    frame,
    fps: 30,
    config: { damping: 15, mass: 1, tension: 80 },
    delay: 90,
    from: 0,
    to: 1,
  });

  return (
    <div style={bgStyle}>
      {/* Decorative gradient circles */}
      <div
        style={{
          position: 'absolute',
          width: 500,
          height: 500,
          right: -200,
          top: -200,
          background: 'radial-gradient(circle, rgba(45, 106, 79, 0.08) 0%, transparent 70%)',
          borderRadius: '50%',
        }}
      />

      {/* Main Problem Statement */}
      <div
        style={{
          position: 'absolute',
          top: '15%',
          left: '10%',
          maxWidth: '80%',
          opacity: textOpacity,
          transform: `translateY(${textY}px)`,
        }}
      >
        <p
          style={{
            fontSize: 16,
            color: '#f97316',
            fontWeight: 600,
            margin: '0 0 20px 0',
            letterSpacing: '1px',
            textTransform: 'uppercase',
            fontFamily: 'Plus Jakarta Sans, sans-serif',
          }}
        >
          The Challenge
        </p>
        <h2
          style={{
            fontSize: 48,
            fontWeight: 800,
            color: '#0b1a16',
            margin: 0,
            lineHeight: 1.2,
            fontFamily: 'Plus Jakarta Sans, sans-serif',
          }}
        >
          <span style={{ color: '#f97316' }}>4,226 Government Schemes</span>
          <br />
          But How Do You Know
          <br />
          <span style={{ background: 'linear-gradient(135deg, #2d6a4f 0%, #f97316 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Which One's For You?
          </span>
        </h2>
      </div>

      {/* Problem Icons with animations */}
      <div
        style={{
          position: 'absolute',
          bottom: '20%',
          left: '10%',
          right: '10%',
          display: 'flex',
          justifyContent: 'space-around',
          gap: 40,
        }}
      >
        {/* Icon 1: Confused */}
        <div
          style={{
            flex: 1,
            textAlign: 'center',
            opacity: icon1Scale,
            transform: `scale(${icon1Scale})`,
          }}
        >
          <div
            style={{
              fontSize: 60,
              marginBottom: 15,
              filter: 'drop-shadow(0 10px 20px rgba(0,0,0,0.1))',
            }}
          >
            😕
          </div>
          <p
            style={{
              fontSize: 16,
              fontWeight: 600,
              color: '#0b1a16',
              margin: 0,
              fontFamily: 'Plus Jakarta Sans, sans-serif',
            }}
          >
            Endless Searching
          </p>
          <p
            style={{
              fontSize: 13,
              color: '#5a6a64',
              margin: '8px 0 0 0',
              fontFamily: 'Plus Jakarta Sans, sans-serif',
            }}
          >
            Lost in bureaucracy
          </p>
        </div>

        {/* Icon 2: Missed */}
        <div
          style={{
            flex: 1,
            textAlign: 'center',
            opacity: icon2Scale,
            transform: `scale(${icon2Scale})`,
          }}
        >
          <div
            style={{
              fontSize: 60,
              marginBottom: 15,
              filter: 'drop-shadow(0 10px 20px rgba(0,0,0,0.1))',
            }}
          >
            ⏰
          </div>
          <p
            style={{
              fontSize: 16,
              fontWeight: 600,
              color: '#0b1a16',
              margin: 0,
              fontFamily: 'Plus Jakarta Sans, sans-serif',
            }}
          >
            Deadlines Missed
          </p>
          <p
            style={{
              fontSize: 13,
              color: '#5a6a64',
              margin: '8px 0 0 0',
              fontFamily: 'Plus Jakarta Sans, sans-serif',
            }}
          >
            Opportunities lost
          </p>
        </div>

        {/* Icon 3: Benefits */}
        <div
          style={{
            flex: 1,
            textAlign: 'center',
            opacity: icon3Scale,
            transform: `scale(${icon3Scale})`,
          }}
        >
          <div
            style={{
              fontSize: 60,
              marginBottom: 15,
              filter: 'drop-shadow(0 10px 20px rgba(0,0,0,0.1))',
            }}
          >
            💰
          </div>
          <p
            style={{
              fontSize: 16,
              fontWeight: 600,
              color: '#0b1a16',
              margin: 0,
              fontFamily: 'Plus Jakarta Sans, sans-serif',
            }}
          >
            Unclaimed Benefits
          </p>
          <p
            style={{
              fontSize: 13,
              color: '#5a6a64',
              margin: '8px 0 0 0',
              fontFamily: 'Plus Jakarta Sans, sans-serif',
            }}
          >
            Help you deserve
          </p>
        </div>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 3: THE SOLUTION
// ─────────────────────────────────────────────────────────────────────────────

const Scene3Solution = () => {
  const frame = useCurrentFrame();

  const bgStyle = {
    position: 'absolute',
    width: '100%',
    height: '100%',
    background: 'linear-gradient(135deg, #0b1a16 0%, #1a3a2e 50%, #0d2818 100%)',
  };

  // Solution title animation
  const titleOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const titleScale = spring({
    frame,
    fps: 30,
    config: { damping: 20, mass: 1.5, tension: 100 },
    from: 0.8,
    to: 1,
  });

  // Feature cards animation
  const card1Y = interpolate(frame, [40, 80], [100, 0]);
  const card1Opacity = interpolate(frame, [40, 80], [0, 1]);

  const card2Y = interpolate(frame, [60, 100], [100, 0]);
  const card2Opacity = interpolate(frame, [60, 100], [0, 1]);

  const card3Y = interpolate(frame, [80, 120], [100, 0]);
  const card3Opacity = interpolate(frame, [80, 120], [0, 1]);

  return (
    <div style={bgStyle}>
      {/* Animated gradient background */}
      <div
        style={{
          position: 'absolute',
          width: 400,
          height: 400,
          left: -100,
          top: -50,
          background: 'radial-gradient(circle, rgba(249, 115, 22, 0.15) 0%, transparent 70%)',
          borderRadius: '50%',
          filter: 'blur(40px)',
          animation: 'float 6s ease-in-out infinite',
        }}
      />

      {/* Solution Title */}
      <div
        style={{
          position: 'absolute',
          top: '10%',
          left: '50%',
          transform: `translate(-50%, -50%) scale(${titleScale})`,
          opacity: titleOpacity,
          textAlign: 'center',
          zIndex: 10,
        }}
      >
        <p
          style={{
            fontSize: 16,
            color: '#f97316',
            fontWeight: 600,
            margin: '0 0 15px 0',
            letterSpacing: '1px',
            textTransform: 'uppercase',
            fontFamily: 'Plus Jakarta Sans, sans-serif',
          }}
        >
          Meet YojanaMitra
        </p>
        <h2
          style={{
            fontSize: 56,
            fontWeight: 800,
            color: '#ffffff',
            margin: 0,
            lineHeight: 1.1,
            fontFamily: 'Plus Jakarta Sans, sans-serif',
          }}
        >
          AI-Powered Access
          <br />
          to <span style={{ color: '#f97316' }}>Your Benefits</span>
        </h2>
      </div>

      {/* Feature Cards */}
      <div
        style={{
          position: 'absolute',
          top: '35%',
          left: '5%',
          right: '5%',
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 30,
          zIndex: 10,
        }}
      >
        {/* Card 1: Fast Matching */}
        <div
          style={{
            background: 'linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(249,115,22,0.05) 100%)',
            backdrop: 'blur(10px)',
            border: '1px solid rgba(255,255,255,0.2)',
            borderRadius: 16,
            padding: 30,
            opacity: card1Opacity,
            transform: `translateY(${card1Y}px)`,
            transition: 'all 0.3s ease',
          }}
        >
          <div
            style={{
              fontSize: 40,
              marginBottom: 15,
              background: 'linear-gradient(135deg, #f97316, #ea580c)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            ⚡
          </div>
          <h3
            style={{
              fontSize: 18,
              fontWeight: 700,
              color: '#ffffff',
              margin: '0 0 10px 0',
              fontFamily: 'Plus Jakarta Sans, sans-serif',
            }}
          >
            Fast Matching
          </h3>
          <p
            style={{
              fontSize: 14,
              color: 'rgba(255,255,255,0.7)',
              margin: 0,
              lineHeight: 1.5,
              fontFamily: 'Plus Jakarta Sans, sans-serif',
            }}
          >
            Answer a quick profile and get instant eligibility matches
          </p>
        </div>

        {/* Card 2: All Schemes */}
        <div
          style={{
            background: 'linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(45,106,79,0.1) 100%)',
            backdrop: 'blur(10px)',
            border: '1px solid rgba(255,255,255,0.2)',
            borderRadius: 16,
            padding: 30,
            opacity: card2Opacity,
            transform: `translateY(${card2Y}px)`,
            transition: 'all 0.3s ease',
          }}
        >
          <div
            style={{
              fontSize: 40,
              marginBottom: 15,
              background: 'linear-gradient(135deg, #2d6a4f, #0b1a16)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            🏛️
          </div>
          <h3
            style={{
              fontSize: 18,
              fontWeight: 700,
              color: '#ffffff',
              margin: '0 0 10px 0',
              fontFamily: 'Plus Jakarta Sans, sans-serif',
            }}
          >
            4,226+ Schemes
          </h3>
          <p
            style={{
              fontSize: 14,
              color: 'rgba(255,255,255,0.7)',
              margin: 0,
              lineHeight: 1.5,
              fontFamily: 'Plus Jakarta Sans, sans-serif',
            }}
          >
            Access all government welfare programs in one place
          </p>
        </div>

        {/* Card 3: Smart AI */}
        <div
          style={{
            background: 'linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(249,115,22,0.05) 100%)',
            backdrop: 'blur(10px)',
            border: '1px solid rgba(255,255,255,0.2)',
            borderRadius: 16,
            padding: 30,
            opacity: card3Opacity,
            transform: `translateY(${card3Y}px)`,
            transition: 'all 0.3s ease',
          }}
        >
          <div
            style={{
              fontSize: 40,
              marginBottom: 15,
            }}
          >
            🤖
          </div>
          <h3
            style={{
              fontSize: 18,
              fontWeight: 700,
              color: '#ffffff',
              margin: '0 0 10px 0',
              fontFamily: 'Plus Jakarta Sans, sans-serif',
            }}
          >
            AI-Powered
          </h3>
          <p
            style={{
              fontSize: 14,
              color: 'rgba(255,255,255,0.7)',
              margin: 0,
              lineHeight: 1.5,
              fontFamily: 'Plus Jakarta Sans, sans-serif',
            }}
          >
            Smart eligibility analysis with 4,226 real schemes analyzed
          </p>
        </div>
      </div>

      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(20px); }
        }
      `}</style>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 4: HOW IT WORKS
// ─────────────────────────────────────────────────────────────────────────────

const Scene4HowItWorks = () => {
  const frame = useCurrentFrame();

  const bgStyle = {
    position: 'absolute',
    width: '100%',
    height: '100%',
    background: 'linear-gradient(135deg, #ffffff 0%, #f5f5f0 100%)',
  };

  // Step animations
  const step1Scale = spring({ frame, fps: 30, config: { damping: 15, mass: 1, tension: 80 }, delay: 0, from: 0, to: 1 });
  const step2Scale = spring({ frame, fps: 30, config: { damping: 15, mass: 1, tension: 80 }, delay: 30, from: 0, to: 1 });
  const step3Scale = spring({ frame, fps: 30, config: { damping: 15, mass: 1, tension: 80 }, delay: 60, from: 0, to: 1 });

  // Arrow animations
  const arrow1Opacity = interpolate(frame, [40, 80], [0, 1]);
  const arrow2Opacity = interpolate(frame, [70, 110], [0, 1]);

  return (
    <div style={bgStyle}>
      <div
        style={{
          position: 'absolute',
          top: '10%',
          left: '50%',
          transform: 'translate(-50%, 0)',
          textAlign: 'center',
          width: '90%',
        }}
      >
        <p style={{ fontSize: 16, color: '#f97316', fontWeight: 600, margin: '0 0 15px 0', letterSpacing: '1px', textTransform: 'uppercase', fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
          Three Simple Steps
        </p>
        <h2 style={{ fontSize: 48, fontWeight: 800, color: '#0b1a16', margin: 0, fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
          How It Works
        </h2>
      </div>

      {/* Steps Container */}
      <div
        style={{
          position: 'absolute',
          top: '35%',
          left: '10%',
          right: '10%',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 40,
        }}
      >
        {/* Step 1 */}
        <div
          style={{
            flex: 1,
            textAlign: 'center',
            opacity: step1Scale,
            transform: `scale(${step1Scale})`,
          }}
        >
          <div
            style={{
              width: 80,
              height: 80,
              margin: '0 auto 20px',
              background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 40,
              boxShadow: '0 20px 40px rgba(249, 115, 22, 0.3)',
            }}
          >
            1️⃣
          </div>
          <h3 style={{ fontSize: 20, fontWeight: 700, color: '#0b1a16', margin: '0 0 10px 0', fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
            Tell Us About You
          </h3>
          <p style={{ fontSize: 14, color: '#5a6a64', margin: 0, lineHeight: 1.6, fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
            Share your basic profile - age, income, location, and needs
          </p>
        </div>

        {/* Arrow 1 */}
        <div
          style={{
            fontSize: 28,
            color: '#f97316',
            opacity: arrow1Opacity,
            animation: 'slideArrow 1s ease-in-out infinite',
          }}
        >
          →
        </div>

        {/* Step 2 */}
        <div
          style={{
            flex: 1,
            textAlign: 'center',
            opacity: step2Scale,
            transform: `scale(${step2Scale})`,
          }}
        >
          <div
            style={{
              width: 80,
              height: 80,
              margin: '0 auto 20px',
              background: 'linear-gradient(135deg, #2d6a4f 0%, #0b1a16 100%)',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 40,
              boxShadow: '0 20px 40px rgba(45, 106, 79, 0.3)',
            }}
          >
            🤖
          </div>
          <h3 style={{ fontSize: 20, fontWeight: 700, color: '#0b1a16', margin: '0 0 10px 0', fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
            AI Analyzes
          </h3>
          <p style={{ fontSize: 14, color: '#5a6a64', margin: 0, lineHeight: 1.6, fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
            Our AI checks 4,226 schemes against your eligibility criteria
          </p>
        </div>

        {/* Arrow 2 */}
        <div
          style={{
            fontSize: 28,
            color: '#f97316',
            opacity: arrow2Opacity,
            animation: 'slideArrow 1s ease-in-out infinite 0.3s',
          }}
        >
          →
        </div>

        {/* Step 3 */}
        <div
          style={{
            flex: 1,
            textAlign: 'center',
            opacity: step3Scale,
            transform: `scale(${step3Scale})`,
          }}
        >
          <div
            style={{
              width: 80,
              height: 80,
              margin: '0 auto 20px',
              background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 40,
              boxShadow: '0 20px 40px rgba(249, 115, 22, 0.3)',
            }}
          >
            ✨
          </div>
          <h3 style={{ fontSize: 20, fontWeight: 700, color: '#0b1a16', margin: '0 0 10px 0', fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
            Get Your Match
          </h3>
          <p style={{ fontSize: 14, color: '#5a6a64', margin: 0, lineHeight: 1.6, fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
            Discover schemes you qualify for with application details
          </p>
        </div>
      </div>

      <style>{`
        @keyframes slideArrow {
          0%, 100% { transform: translateX(0); }
          50% { transform: translateX(8px); }
        }
      `}</style>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 5: CALL TO ACTION
// ─────────────────────────────────────────────────────────────────────────────

const Scene5CTA = () => {
  const frame = useCurrentFrame();

  const bgStyle = {
    position: 'absolute',
    width: '100%',
    height: '100%',
    background: 'linear-gradient(135deg, #0b1a16 0%, #1a3a2e 50%, #0d2818 100%)',
  };

  // Content animations
  const contentOpacity = interpolate(frame, [0, 40], [0, 1], { extrapolateRight: 'clamp' });
  const contentScale = spring({
    frame,
    fps: 30,
    config: { damping: 20, mass: 1.5, tension: 100 },
    from: 0.8,
    to: 1,
  });

  // Button pulse
  const buttonScale = spring({
    frame: (frame - 80) % 100,
    fps: 30,
    config: { damping: 10, mass: 1, tension: 100 },
    from: 0.95,
    to: 1.05,
  });

  return (
    <div style={bgStyle}>
      {/* Animated background elements */}
      <div
        style={{
          position: 'absolute',
          width: 500,
          height: 500,
          right: -200,
          top: 50,
          background: 'radial-gradient(circle, rgba(249, 115, 22, 0.15) 0%, transparent 70%)',
          borderRadius: '50%',
          filter: 'blur(40px)',
          animation: 'float 8s ease-in-out infinite',
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: 300,
          height: 300,
          left: -100,
          bottom: 50,
          background: 'radial-gradient(circle, rgba(45, 106, 79, 0.15) 0%, transparent 70%)',
          borderRadius: '50%',
          filter: 'blur(40px)',
          animation: 'float 6s ease-in-out infinite reverse',
        }}
      />

      {/* Main content */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: `translate(-50%, -50%) scale(${contentScale})`,
          opacity: contentOpacity,
          textAlign: 'center',
          zIndex: 10,
          width: '90%',
          maxWidth: 900,
        }}
      >
        <h2
          style={{
            fontSize: 56,
            fontWeight: 800,
            color: '#ffffff',
            margin: '0 0 20px 0',
            lineHeight: 1.1,
            fontFamily: 'Plus Jakarta Sans, sans-serif',
          }}
        >
          Stop Searching.
          <br />
          Start <span style={{ color: '#f97316' }}>Benefiting.</span>
        </h2>
        <p
          style={{
            fontSize: 20,
            color: 'rgba(255, 255, 255, 0.8)',
            margin: '0 0 50px 0',
            lineHeight: 1.6,
            fontFamily: 'Plus Jakarta Sans, sans-serif',
          }}
        >
          Join thousands of Indians discovering their true eligibility with YojanaMitra
        </p>

        {/* CTA Button */}
        <div
          style={{
            display: 'inline-block',
            position: 'relative',
          }}
        >
          <button
            style={{
              background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
              color: '#ffffff',
              border: 'none',
              padding: '16px 48px',
              fontSize: 18,
              fontWeight: 700,
              borderRadius: 12,
              cursor: 'pointer',
              boxShadow: '0 20px 40px rgba(249, 115, 22, 0.3)',
              transform: `scale(${buttonScale})`,
              fontFamily: 'Plus Jakarta Sans, sans-serif',
              letterSpacing: '0.5px',
              transition: 'box-shadow 0.3s ease',
            }}
          >
            Find Your Schemes Now
          </button>
          <div
            style={{
              position: 'absolute',
              inset: -2,
              background: 'radial-gradient(circle, rgba(249, 115, 22, 0.3) 0%, transparent 70%)',
              borderRadius: 12,
              pointerEvents: 'none',
              animation: 'pulse 2s ease-in-out infinite',
            }}
          />
        </div>
      </div>

      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(20px); }
        }
        @keyframes pulse {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.1); opacity: 0; }
        }
      `}</style>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPOSITION
// ─────────────────────────────────────────────────────────────────────────────

export const YojanaMitraExplainer = () => {
  return (
    <Composition
      id="YojanaMitra-Explainer"
      component={YojanaMitraExplainerComp}
      durationInFrames={30 * 60} // 60 seconds at 30fps
      fps={30}
      width={1920}
      height={1080}
    />
  );
};

export const YojanaMitraExplainerComp = () => {
  return (
    <div style={{ width: '100%', height: '100%', fontFamily: 'Plus Jakarta Sans, sans-serif', overflow: 'hidden' }}>
      {/* Scene 1: intro - 0-300 frames (10 seconds) */}
      <Sequence from={0} durationInFrames={300}>
        <Scene1Intro />
      </Sequence>

      {/* Scene 2: Problem - 300-600 frames (10 seconds) */}
      <Sequence from={300} durationInFrames={300}>
        <Scene2Problem />
      </Sequence>

      {/* Scene 3: Solution - 600-900 frames (10 seconds) */}
      <Sequence from={600} durationInFrames={300}>
        <Scene3Solution />
      </Sequence>

      {/* Scene 4: How it works - 900-1200 frames (10 seconds) */}
      <Sequence from={900} durationInFrames={300}>
        <Scene4HowItWorks />
      </Sequence>

      {/* Scene 5: CTA - 1200-1800 frames (20 seconds) */}
      <Sequence from={1200} durationInFrames={600}>
        <Scene5CTA />
      </Sequence>
    </div>
  );
};

export default YojanaMitraExplainer;
