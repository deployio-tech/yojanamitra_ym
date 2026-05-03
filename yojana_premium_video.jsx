/**
 * YojanaMitra Premium Explainer Video - ADVANCED VERSION
 * Using Enhanced Components for High-End Production
 *
 * This version uses premium animations, mesh gradients, and professional
 * effects to match YouTube-level SaaS explainer video quality.
 */

import React from 'react';
import { Composition, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import {
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
} from './yojana_enhanced_components';

const COLORS = {
  darkGreen: '#0b1a16',
  orange: '#f97316',
  darkOrange: '#ea580c',
  green: '#2d6a4f',
  white: '#ffffff',
  lightMint: '#c9ded0',
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 1: PREMIUM HERO INTRO
// High-end text reveal with mesh gradient background
// ─────────────────────────────────────────────────────────────────────────────

const Scene1PremiumHero: React.FC = () => {
  const frame = useCurrentFrame();
  const fps = useVideoConfig().fps;

  // Subtitle animation
  const subtitleOpacity = interpolate(
    frame,
    [80, 120],
    [0, 1],
    { extrapolateRight: 'clamp' }
  );

  const subtitleY = interpolate(
    frame,
    [80, 120],
    [20, 0],
    { extrapolateRight: 'clamp' }
  );

  // CTA opacity
  const ctaOpacity = interpolate(
    frame,
    [200, 240],
    [0, 1],
    { extrapolateRight: 'clamp' }
  );

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
      {/* Mesh gradient background */}
      <MeshGradientBG 
        colors={[COLORS.orange, COLORS.green, COLORS.darkGreen]}
        animationSpeed={0.5}
      />

      {/* Floating particles */}
      <Particles count={30} color={COLORS.white} opacity={0.15} />

      {/* Main content */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          textAlign: 'center',
          padding: '60px 40px',
          zIndex: 10,
        }}
      >
        {/* Premium gradient title */}
        <div style={{ marginBottom: 40 }}>
          <GradientText
            text="YOJANA MITRA"
            gradient={`linear-gradient(135deg, ${COLORS.white} 0%, ${COLORS.lightMint} 100%)`}
            fontSize={92}
            fontWeight={800}
          />
        </div>

        {/* Animated subtitle */}
        <div
          style={{
            opacity: subtitleOpacity,
            transform: `translateY(${subtitleY}px)`,
            marginBottom: 60,
          }}
        >
          <p
            style={{
              fontSize: 32,
              color: COLORS.lightMint,
              margin: 0,
              fontWeight: 500,
              letterSpacing: '1px',
            }}
          >
            Find Your Perfect Government Scheme In Seconds
          </p>
        </div>

        {/* Scroll hint */}
        <div
          style={{
            opacity: subtitleOpacity,
            animation: 'bounce 2s infinite',
            marginBottom: 100,
          }}
        >
          <div
            style={{
              width: 8,
              height: 28,
              border: `2px solid ${COLORS.lightMint}`,
              borderRadius: 20,
              display: 'flex',
              justifyContent: 'center',
              paddingTop: 4,
            }}
          >
            <div
              style={{
                width: 2,
                height: 6,
                background: COLORS.lightMint,
                borderRadius: 2,
              }}
            />
          </div>
        </div>

        {/* CTA Button */}
        <div style={{ opacity: ctaOpacity }}>
          <EnhancedCTAButton 
            text="Get Started Now"
            delay={200}
            color={COLORS.orange}
          />
        </div>
      </div>

      <style>{`
        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(10px); }
        }
      `}</style>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 2: PROBLEM STATISTICS
// Show numbers with animated counter and stat boxes
// ─────────────────────────────────────────────────────────────────────────────

const Scene2ProblemStats: React.FC = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(
    frame,
    [0, 40],
    [0, 1],
    { extrapolateRight: 'clamp' }
  );

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
      {/* Gradient background */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `linear-gradient(135deg, ${COLORS.darkGreen} 0%, ${COLORS.green} 100%)`,
        }}
      />

      {/* Background particles */}
      <Particles count={25} color={COLORS.orange} opacity={0.1} />

      {/* Main content */}
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
        }}
      >
        {/* Title */}
        <div style={{ opacity: titleOpacity, marginBottom: 80, textAlign: 'center' }}>
          <h2
            style={{
              fontSize: 56,
              fontWeight: 700,
              color: COLORS.white,
              margin: '0 0 20px 0',
              letterSpacing: '-1px',
            }}
          >
            Millions Are Missing Out
          </h2>
          <p
            style={{
              fontSize: 20,
              color: COLORS.lightMint,
              margin: 0,
            }}
          >
            On government schemes and benefits they deserve
          </p>
        </div>

        {/* Statistics grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 40,
            width: '100%',
            maxWidth: 1100,
          }}
        >
          <AnimatedStatBox
            icon="🔍"
            title="Schemes Available"
            value={4226}
            delay={100}
            color={COLORS.orange}
          />
          <AnimatedStatBox
            icon="💰"
            title="Potential Benefits"
            value={890}
            suffix="B+"
            delay={150}
            color={COLORS.lightMint}
          />
          <AnimatedStatBox
            icon="👥"
            title="Eligible Candidates"
            value={180}
            suffix="M+"
            delay={200}
            color={COLORS.orange}
          />
        </div>

        {/* Bottom text */}
        <div style={{ marginTop: 80, textAlign: 'center', maxWidth: 700 }}>
          <p
            style={{
              fontSize: 18,
              color: 'rgba(255, 255, 255, 0.8)',
              lineHeight: 1.6,
              margin: 0,
            }}
          >
            Finding the right scheme is <strong>complex & time-consuming</strong>. Most people don't know
            where to start, leading to missed opportunities worth thousands of rupees.
          </p>
        </div>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 3: SOLUTION FEATURES
// Premium feature cards with slide-in animation
// ─────────────────────────────────────────────────────────────────────────────

const Scene3SolutionFeatures: React.FC = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(
    frame,
    [0, 40],
    [0, 1],
    { extrapolateRight: 'clamp' }
  );

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
      {/* Gradient background */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `linear-gradient(135deg, ${COLORS.darkOrange} 0%, ${COLORS.orange} 50%, ${COLORS.green} 100%)`,
        }}
      />

      {/* Mesh gradient overlay */}
      <MeshGradientBG 
        colors={[COLORS.orange, COLORS.green, COLORS.white]}
        animationSpeed={0.3}
      />

      {/* Main content */}
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
        }}
      >
        {/* Title */}
        <div style={{ opacity: titleOpacity, marginBottom: 80, textAlign: 'center' }}>
          <h2
            style={{
              fontSize: 56,
              fontWeight: 700,
              color: COLORS.white,
              margin: '0 0 20px 0',
              letterSpacing: '-1px',
            }}
          >
            One Platform. All Solutions.
          </h2>
          <p
            style={{
              fontSize: 20,
              color: 'rgba(255, 255, 255, 0.9)',
              margin: 0,
            }}
          >
            Everything you need to find and apply for government schemes
          </p>
        </div>

        {/* Features grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: 32,
            width: '100%',
            maxWidth: 1000,
          }}
        >
          {/* Feature 1 */}
          <AnimatedSlideBox
            from="left"
            delay={60}
            duration={40}
            background="rgba(255, 255, 255, 0.12)"
            padding={40}
          >
            <div style={{ fontSize: 40, marginBottom: 16 }}>⚡</div>
            <h3 style={{ fontSize: 24, fontWeight: 700, color: COLORS.white, margin: '0 0 8px 0' }}>
              Lightning Fast
            </h3>
            <p style={{ fontSize: 14, color: 'rgba(255, 255, 255, 0.8)', margin: 0 }}>
              Find relevant schemes in seconds, not hours
            </p>
          </AnimatedSlideBox>

          {/* Feature 2 */}
          <AnimatedSlideBox
            from="right"
            delay={100}
            duration={40}
            background="rgba(255, 255, 255, 0.12)"
            padding={40}
          >
            <div style={{ fontSize: 40, marginBottom: 16 }}>🎯</div>
            <h3 style={{ fontSize: 24, fontWeight: 700, color: COLORS.white, margin: '0 0 8px 0' }}>
              Hyper-Targeted
            </h3>
            <p style={{ fontSize: 14, color: 'rgba(255, 255, 255, 0.8)', margin: 0 }}>
              AI powered matching based on your profile
            </p>
          </AnimatedSlideBox>

          {/* Feature 3 */}
          <AnimatedSlideBox
            from="left"
            delay={140}
            duration={40}
            background="rgba(255, 255, 255, 0.12)"
            padding={40}
          >
            <div style={{ fontSize: 40, marginBottom: 16 }}>📱</div>
            <h3 style={{ fontSize: 24, fontWeight: 700, color: COLORS.white, margin: '0 0 8px 0' }}>
              Simple & Intuitive
            </h3>
            <p style={{ fontSize: 14, color: 'rgba(255, 255, 255, 0.8)', margin: 0 }}>
              No technical knowledge required, just tell us about yourself
            </p>
          </AnimatedSlideBox>

          {/* Feature 4 */}
          <AnimatedSlideBox
            from="right"
            delay={180}
            duration={40}
            background="rgba(255, 255, 255, 0.12)"
            padding={40}
          >
            <div style={{ fontSize: 40, marginBottom: 16 }}>✅</div>
            <h3 style={{ fontSize: 24, fontWeight: 700, color: COLORS.white, margin: '0 0 8px 0' }}>
              Ready to Apply
            </h3>
            <p style={{ fontSize: 14, color: 'rgba(255, 255, 255, 0.8)', margin: 0 }}>
              Direct links to apply immediately with guidance
            </p>
          </AnimatedSlideBox>
        </div>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 4: HOW IT WORKS (STEP-BY-STEP)
// Animated step counter with process flow
// ─────────────────────────────────────────────────────────────────────────────

const Scene4HowItWorks: React.FC = () => {
  const frame = useCurrentFrame();
  const fps = useVideoConfig().fps;

  const titleOpacity = interpolate(
    frame,
    [0, 40],
    [0, 1],
    { extrapolateRight: 'clamp' }
  );

  // Arrow animations
  const arrow1Scale = spring({
    frame: Math.max(0, frame - 100),
    fps,
    config: { damping: 12, mass: 1, tension: 100 },
    from: 0.5,
    to: 1,
  });

  const arrow2Scale = spring({
    frame: Math.max(0, frame - 160),
    fps,
    config: { damping: 12, mass: 1, tension: 100 },
    from: 0.5,
    to: 1,
  });

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
      {/* Gradient background */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `linear-gradient(135deg, ${COLORS.green} 0%, ${COLORS.darkGreen} 100%)`,
        }}
      />

      {/* Main content */}
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
        }}
      >
        {/* Title */}
        <div style={{ opacity: titleOpacity, marginBottom: 80, textAlign: 'center' }}>
          <h2
            style={{
              fontSize: 56,
              fontWeight: 700,
              color: COLORS.white,
              margin: '0 0 20px 0',
              letterSpacing: '-1px',
            }}
          >
            Three Simple Steps
          </h2>
          <p
            style={{
              fontSize: 20,
              color: COLORS.lightMint,
              margin: 0,
            }}
          >
            From discovery to application in minutes
          </p>
        </div>

        {/* Steps container */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            gap: 60,
            width: '100%',
            maxWidth: 1000,
          }}
        >
          {/* Step 1 */}
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div
              style={{
                width: 120,
                height: 120,
                background: `linear-gradient(135deg, ${COLORS.orange}, ${COLORS.darkOrange})`,
                borderRadius: '50%',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                fontSize: 54,
                margin: '0 auto 20px',
                boxShadow: `0 20px 40px rgba(249, 115, 22, 0.3)`,
              }}
            >
              1️⃣
            </div>
            <h4
              style={{
                fontSize: 20,
                fontWeight: 600,
                color: COLORS.white,
                margin: '0 0 8px 0',
              }}
            >
              Tell Us About You
            </h4>
            <p
              style={{
                fontSize: 14,
                color: 'rgba(255, 255, 255, 0.7)',
                margin: 0,
              }}
            >
              Answer a few simple questions about yourself
            </p>
          </div>

          {/* Arrow 1 */}
          <div
            style={{
              fontSize: 32,
              color: COLORS.orange,
              opacity: arrow1Scale,
              transform: `scale(${arrow1Scale})`,
            }}
          >
            →
          </div>

          {/* Step 2 */}
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div
              style={{
                width: 120,
                height: 120,
                background: `linear-gradient(135deg, ${COLORS.lightMint}, ${COLORS.green})`,
                borderRadius: '50%',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                fontSize: 54,
                margin: '0 auto 20px',
                boxShadow: `0 20px 40px rgba(201, 222, 208, 0.3)`,
              }}
            >
              2️⃣
            </div>
            <h4
              style={{
                fontSize: 20,
                fontWeight: 600,
                color: COLORS.white,
                margin: '0 0 8px 0',
              }}
            >
              AI Analyzes
            </h4>
            <p
              style={{
                fontSize: 14,
                color: 'rgba(255, 255, 255, 0.7)',
                margin: 0,
              }}
            >
              Our AI engine finds matching schemes instantly
            </p>
          </div>

          {/* Arrow 2 */}
          <div
            style={{
              fontSize: 32,
              color: COLORS.orange,
              opacity: arrow2Scale,
              transform: `scale(${arrow2Scale})`,
            }}
          >
            →
          </div>

          {/* Step 3 */}
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div
              style={{
                width: 120,
                height: 120,
                background: `linear-gradient(135deg, ${COLORS.orange}, ${COLORS.green})`,
                borderRadius: '50%',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                fontSize: 54,
                margin: '0 auto 20px',
                boxShadow: `0 20px 40px rgba(249, 115, 22, 0.3)`,
              }}
            >
              3️⃣
            </div>
            <h4
              style={{
                fontSize: 20,
                fontWeight: 600,
                color: COLORS.white,
                margin: '0 0 8px 0',
              }}
            >
              Get & Apply
            </h4>
            <p
              style={{
                fontSize: 14,
                color: 'rgba(255, 255, 255, 0.7)',
                margin: 0,
              }}
            >
              View details and apply directly to schemes
            </p>
          </div>
        </div>

        {/* Bottom emphasis */}
        <div
          style={{
            marginTop: 80,
            padding: '30px 40px',
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(20px)',
            borderRadius: 16,
            border: '1px solid rgba(255, 255, 255, 0.2)',
            textAlign: 'center',
            maxWidth: 600,
          }}
        >
          <p
            style={{
              fontSize: 16,
              color: COLORS.white,
              margin: 0,
              fontWeight: 500,
            }}
          >
            ✨ <strong>No paperwork. No confusion. Just results.</strong>
          </p>
        </div>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 5: FINAL CTA
// Premium closing with call-to-action
// ─────────────────────────────────────────────────────────────────────────────

const Scene5FinalCTA: React.FC = () => {
  const frame = useCurrentFrame();
  const fps = useVideoConfig().fps;

  // Heading animations
  const headingScale = spring({
    frame,
    fps,
    config: { damping: 15, mass: 1.2, tension: 80 },
    from: 0.85,
    to: 1,
  });

  const subheadingOpacity = interpolate(
    frame,
    [40, 80],
    [0, 1],
    { extrapolateRight: 'clamp' }
  );

  const buttonOpacity = interpolate(
    frame,
    [100, 140],
    [0, 1],
    { extrapolateRight: 'clamp' }
  );

  const footerOpacity = interpolate(
    frame,
    [200, 240],
    [0, 1],
    { extrapolateRight: 'clamp' }
  );

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
      {/* Premium gradient background */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `linear-gradient(135deg, ${COLORS.darkGreen} 0%, ${COLORS.green} 50%, ${COLORS.orange} 100%)`,
        }}
      />

      {/* Animated mesh gradient */}
      <MeshGradientBG 
        colors={[COLORS.orange, COLORS.white, COLORS.green]}
        animationSpeed={0.4}
      />

      {/* Main content */}
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
        {/* Main heading */}
        <div
          style={{
            transform: `scale(${headingScale})`,
            marginBottom: 40,
          }}
        >
          <h1
            style={{
              fontSize: 72,
              fontWeight: 800,
              color: COLORS.white,
              margin: 0,
              letterSpacing: '-2px',
              lineHeight: 1.2,
            }}
          >
            Your Perfect Scheme <br /> Awaits
          </h1>
        </div>

        {/* Subheading */}
        <div
          style={{
            opacity: subheadingOpacity,
            marginBottom: 60,
          }}
        >
          <p
            style={{
              fontSize: 24,
              color: 'rgba(255, 255, 255, 0.9)',
              margin: 0,
              lineHeight: 1.5,
            }}
          >
            Stop missing opportunities. Start finding schemes today.
          </p>
        </div>

        {/* CTA Button */}
        <div style={{ opacity: buttonOpacity, marginBottom: 100 }}>
          <EnhancedCTAButton 
            text="Start Finding Schemes"
            delay={100}
            color={COLORS.orange}
            glowColor="rgba(249, 115, 22, 0.4)"
          />
        </div>

        {/* Trust indicators */}
        <div
          style={{
            opacity: footerOpacity,
            padding: '30px 40px',
            background: 'rgba(255, 255, 255, 0.08)',
            backdropFilter: 'blur(20px)',
            borderRadius: 16,
            border: '1px solid rgba(255, 255, 255, 0.15)',
            maxWidth: 500,
          }}
        >
          <p
            style={{
              fontSize: 14,
              color: 'rgba(255, 255, 255, 0.8)',
              margin: 0,
              marginBottom: 12,
              letterSpacing: '0.5px',
            }}
          >
            TRUSTED BY
          </p>
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: 20,
              fontSize: 24,
              opacity: 0.6,
            }}
          >
            🏛️ 🏦 💼 🎓
          </div>
          <p
            style={{
              fontSize: 12,
              color: 'rgba(255, 255, 255, 0.6)',
              margin: '12px 0 0 0',
            }}
          >
            Government Agencies • Educational Institutions • Organizations
          </p>
        </div>
      </div>

      {/* Floating particles */}
      <Particles count={40} color={COLORS.white} opacity={0.1} />
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPOSITION
// Sequences all scenes together
// ─────────────────────────────────────────────────────────────────────────────

export const YojanaMitraPremiumVideo: React.FC = () => {
  return (
    <div
      style={{
        background: COLORS.darkGreen,
        width: '100%',
        height: '100%',
      }}
    >
      <Sequence from={0} durationInFrames={300}>
        <Scene1PremiumHero />
      </Sequence>
      <Sequence from={300} durationInFrames={300}>
        <Scene2ProblemStats />
      </Sequence>
      <Sequence from={600} durationInFrames={300}>
        <Scene3SolutionFeatures />
      </Sequence>
      <Sequence from={900} durationInFrames={300}>
        <Scene4HowItWorks />
      </Sequence>
      <Sequence from={1200} durationInFrames={600}>
        <Scene5FinalCTA />
      </Sequence>
    </div>
  );
};

export default YojanaMitraPremiumVideo;
