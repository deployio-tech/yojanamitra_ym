# YojanaMitra Video - Quick Reference CheatSheet

## 🚀 Quick Start

```bash
# 1. Install
npm install remotion ffmpeg-static @types/react @types/node typescript

# 2. Preview
npm start

# 3. Render Premium Version
npx remotion render remotion_root_enhanced.tsx YojanaMitraPremium premium.mp4

# 4. Render Mobile (Portrait)
npx remotion render remotion_root_enhanced.tsx YojanaMitraPremium-Portrait premium-mobile.mp4
```

---

## 📁 File Structure

| File | Purpose | Edit For |
|------|---------|----------|
| `yojana_premium_video.jsx` | Main video (5 scenes) | Content, text, timing |
| `yojana_enhanced_components.tsx` | Reusable components | Animations, effects |
| `remotion_root_enhanced.tsx` | Composition entry | Adding/removing scenes |
| `YOJANA_PREMIUM_VIDEO_GUIDE.md` | Full documentation | Learning |
| `ADVANCED_CUSTOMIZATION_EXAMPLES.tsx` | Code examples | Advanced features |

---

## 🎨 Component Quick Reference

### Mesh Gradient Background
```jsx
<MeshGradientBG 
  colors={['#f97316', '#2d6a4f', '#0b1a16']}
  animationSpeed={0.5}
/>
```

### Animated Counter
```jsx
<AnimatedCounter 
  to={4226}
  suffix="+"
  framesCountDuration={60}
/>
```

### Stat Box
```jsx
<AnimatedStatBox
  icon="🎯"
  title="Title"
  value={1000}
  delay={100}
  color="#f97316"
/>
```

### Gradient Text
```jsx
<GradientText
  text="Your Text"
  gradient="linear-gradient(135deg, #fff 0%, #c9ded0 100%)"
  fontSize={64}
  fontWeight={800}
/>
```

### Animated Button
```jsx
<EnhancedCTAButton 
  text="Click Me"
  delay={200}
  color="#f97316"
/>
```

### Slide-in Card
```jsx
<AnimatedSlideBox
  from="left"    // or "right", "top", "bottom"
  delay={60}
  duration={40}
>
  <p>Content</p>
</AnimatedSlideBox>
```

### Floating Particles
```jsx
<Particles 
  count={30}
  color="#ffffff"
  opacity={0.15}
/>
```

---

## 🎬 Scene Timeline

| Scene | Frames | Duration | Content |
|-------|--------|----------|---------|
| 1. Hero | 0-300 | 10s | Title, gradient, CTA |
| 2. Problem | 300-600 | 10s | Stats, numbers |
| 3. Solution | 600-900 | 10s | 4 feature cards |
| 4. How It Works | 900-1200 | 10s | 3-step process |
| 5. Final CTA | 1200-1800 | 20s | Closing, trust badges |
| **TOTAL** | **1800** | **60s** | |

---

## 🎨 Colors (YojanaMitra Palette)

```javascript
#0b1a16  // Dark Green - Authority, primary bg
#2d6a4f  // Medium Green - Growth, secondary
#f97316  // Orange - Energy, CTAs, accents
#ea580c  // Dark Orange - Complementary accent
#ffffff  // White - Primary text
#c9ded0  // Light Mint - Secondary text, accents
```

---

## ⏱️ Frame Duration Conversion

| Seconds | Frames @30fps |
|---------|--------------|
| 1s | 30 |
| 5s | 150 |
| 10s | 300 |
| 30s | 900 |
| 60s | 1800 |
| 90s | 2700 |

---

## 🎯 Animation Timing Patterns

### Staggered Reveal (Multiple Elements)
```jsx
<AnimatedStatBox delay={100} />    // First
<AnimatedStatBox delay={150} />    // Delayed 50 frames
<AnimatedStatBox delay={200} />    // Delayed 100 frames
```

### Sequential Scenes
```jsx
<Sequence from={0} durationInFrames={300}>
  <Scene1 />  {/* 0-300 */}
</Sequence>
<Sequence from={300} durationInFrames={300}>
  <Scene2 />  {/* 300-600 */}
</Sequence>
```

### Spring Physics (Natural Motion)
```jsx
const scale = spring({
  frame,
  fps,
  config: { damping: 15, mass: 1, tension: 100 },
  from: 0,
  to: 1,
});
```

---

## 🔧 Common Customizations

### Change Colors
```jsx
// Find in yojana_premium_video.jsx
const COLORS = {
  orange: '#YOUR_COLOR',    // ← Edit this
  green: '#YOUR_COLOR',
  // ...
}
```

### Change Text
```jsx
// Find Scene components
<h2>Your Text Here</h2>    // ← Edit this
<p>Your description</p>    // ← Or this
```

### Adjust Animation Speed
```jsx
// Change frame duration in Sequence
<Sequence from={0} durationInFrames={200}>  {/* Was 300, now 200 = faster */}
  <Scene1 />
</Sequence>
```

### Change Button Text
```jsx
<EnhancedCTAButton 
  text="Your Button Text"   // ← Edit this
/>
```

### Add/Remove Background
```jsx
<MeshGradientBG 
  colors={['#f97316', '#2d6a4f', '#0b1a16']}
/>
// Remove this div to remove background
```

---

## 🐛 Common Issues & Fixes

### Issue: Video plays too fast
**Fix:** Check `fps={30}` in all Composition definitions

### Issue: Animation not showing
**Fix:** Check delay < total scene duration
```jsx
// ❌ Wrong: delay is after scene ends
<Scene delay={400} duration={300} />  // Scene is 300 frames long

// ✅ Correct
<Scene delay={100} duration={300} />  // Delay is within scene
```

### Issue: Colors look wrong
**Fix:** Export PNG to verify before rendering MP4
```bash
npx remotion still yojana_premium_video.jsx YojanaMitraPremium --frame=30 --output=test.png
```

### Issue: Render takes too long
**Fix:** Reduce concurrency
```bash
npx remotion render yojana_premium_video.jsx YojanaMitraPremium output.mp4 --concurrency=2
```

### Issue: Components not found
**Fix:** Install TypeScript types
```bash
npm install --save-dev @types/react @types/node typescript
```

---

## 📊 Rendering Commands

### Standard Resolution (1080p)
```bash
npx remotion render remotion_root_enhanced.tsx YojanaMitraPremium output.mp4
```

### Portrait (Mobile)
```bash
npx remotion render remotion_root_enhanced.tsx YojanaMitraPremium-Portrait output-mobile.mp4
```

### Square (Social Media)
```bash
npx remotion render remotion_root_enhanced.tsx YojanaMitraPremium-Square output-square.mp4
```

### High Quality
```bash
npx remotion render yojana_premium_video.jsx YojanaMitraPremium --crf=18 output.mp4
```

### ProRes (Professional)
```bash
npx remotion render yojana_premium_video.jsx YojanaMitraPremium output.mov --codec=prores
```

### Keyframe Preview
```bash
npx remotion still yojana_premium_video.jsx YojanaMitraPremium --frame=900 --output=frame-30sec.png
```

---

## 🎬 Spring Physics Presets

```javascript
// Gentle Wave
{ damping: 20, mass: 1.5, tension: 80 }

// Bouncy Energy
{ damping: 10, mass: 1, tension: 120 }

// Snappy Response
{ damping: 15, mass: 0.8, tension: 180 }

// Smooth & Slow
{ damping: 25, mass: 2, tension: 60 }

// Default (Good all-purpose)
{ damping: 15, mass: 1, tension: 100 }
```

---

## 📐 Interpolation Quick Syntax

```javascript
// Basic
interpolate(frame, [0, 60], [0, 100])

// With easing
interpolate(frame, [0, 60], [0, 100], {
  easing: Easing.outQuad
})

// With extrapolation
interpolate(frame, [0, 60], [0, 100], {
  extrapolateRight: 'clamp'  // Don't go past 100
})
```

---

## 🏗️ Scene Template (Copy & Paste)

```jsx
const MyCustomScene: React.FC = () => {
  const frame = useCurrentFrame();
  const fps = useVideoConfig().fps;

  // Animations
  const titleOpacity = interpolate(
    frame,
    [0, 40],
    [0, 1],
    { extrapolateRight: 'clamp' }
  );

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      {/* Background */}
      <div style={{ position: 'absolute', inset: 0, background: '#0b1a16' }} />

      {/* Particles */}
      <Particles count={25} color="#ffffff" opacity={0.1} />

      {/* Content */}
      <div style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 10,
      }}>
        <div style={{ opacity: titleOpacity }}>
          <GradientText text="Your Text" gradient="..." fontSize={64} />
        </div>
      </div>
    </div>
  );
};

// Add to remotion_root_enhanced.tsx:
<Composition
  id="MyScene"
  component={MyCustomScene}
  durationInFrames={300}
  fps={30}
  width={1920}
  height={1080}
/>
```

---

## 📱 Mobile Optimization

### Portrait Resolution
```jsx
<Composition
  id="Video-Portrait"
  component={YojanaMitraPremiumVideo}
  durationInFrames={1800}
  fps={30}
  width={1080}
  height={1920}  // Taller than wide
/>
```

### Size Optimization
```bash
# Compress for web
ffmpeg -i premium.mp4 -c:v libx264 -preset slow -crf 24 premium-web.mp4

# Optimize for mobile
ffmpeg -i premium.mp4 -vf scale=720:-1 -c:v libx264 -crf 26 premium-mobile.mp4
```

---

## 🔗 External Resources

- **Remotion Docs:** https://remotion.dev/docs
- **Spring Easing:** https://easings.net/
- **FFmpeg Tips:** https://ffmpeg.org/documentation.html
- **Animation Principles:** https://material.io/design/motion/

---

## 💾 Project Setup Checklist

- [x] Node.js 16+ installed
- [x] npm installed
- [x] `remotion` package installed
- [x] `ffmpeg-static` installed
- [x] TypeScript types installed (`@types/react`)
- [x] All `.tsx` and `.jsx` files in place
- [x] `package.json` scripts added
- [x] Preview runs on `npm start`
- [x] Export renders successfully

---

## 📈 Performance Tips

1. **Reduce particle count** if slower systems:
   ```jsx
   <Particles count={15} />  // Instead of 30
   ```

2. **Use `extrapolateRight: 'clamp'`** to stop animations early:
   ```jsx
   interpolate(frame, [0, 60], [0, 1], { extrapolateRight: 'clamp' })
   ```

3. **Batch render multiple formats**:
   ```bash
   npm run render:all
   ```

4. **Increase concurrency for faster renders**:
   ```bash
   npx remotion render --concurrency=8 ...
   ```

---

## 🎓 Learning Path

1. **Start:** Edit text in scenes
2. **Next:** Change colors in `COLORS` object
3. **Advanced:** Modify animation delays
4. **Expert:** Create custom components using examples
5. **Master:** Build full custom scenes from scratch

---

## 🚀 deployment Options

| Platform | Format | Dimensions | FPS |
|----------|--------|------------|-----|
| YouTube | MP4 | 1920x1080 | 30 |
| TikTok | MP4, MOV | 1080x1920 | 30 |
| Instagram | MP4 | 1080x1080 | 30 |
| LinkedIn | MP4 | 1200x627 | 30 |
| Twitter | MP4 | 1280x720 | 30 |
| Website | WebM | 1920x1080 | 30 |

---

**Version:** 2.0 Premium Edition  
**Last Updated:** 2024  
**Quick Ref:** v1.0
