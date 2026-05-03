# YojanaMitra SaaS Explainer Video

Professional 60-second explainer video built with **Remotion** - Programmatic video generation using React.

Inspired by professional SaaS video design patterns from video production best practices.

## 📹 Video Structure

**Timeline (60 seconds at 30fps):**
- **0-10s**: Scrollytelling intro animation (YOJANA MITRA title)
- **10-20s**: The Problem (4,226 schemes, confusion, missed deadlines)
- **20-30s**: The Solution (AI-powered matching, 4,226 schemes, smart features)
- **30-40s**: How It Works (3 simple steps)
- **40-60s**: Call-to-Action (pulsing button with gradient backgrounds)

## 🎨 Design Elements Used

### Colors (From YojanaMitra Brand)
- **Dark Green**: `#0b1a16` (Primary)
- **Marigold Orange**: `#f97316` (Accent)
- **Forest Green**: `#2d6a4f` (Secondary)
- **White**: `#ffffff` (Text)
- **Light Mint**: `#c9ded0` (Background)

### Animation Techniques
- ✨ **Spring animations** - Natural, bouncy text reveals
- 🔄 **Interpolations** - Smooth fade-ins and position transitions
- 🎯 **Staggered animations** - Sequential element reveals
- 💫 **Floating backgrounds** - Subtle looping orbs
- 🎬 **Ease effects** - Professional motion curves
- 👁️ **Blur effects** - Depth and focus

### Components
- Animated title sequences
- Gradient backgrounds (animated)
- Feature cards with backdrop blur
- Step indicators with emoji
- Pulsing CTA button
- Floating icon animations
- Text drop shadows for depth

## 🚀 Installation & Setup

### Prerequisites
- Node.js 16+ 
- npm or yarn
- FFmpeg (for video rendering)

### Install Remotion

```bash
# Using npm
npm install remotion @react-pdf/renderer

# Using yarn
yarn add remotion @react-pdf/renderer
```

### Full Setup with Create React App + Remotion

```bash
# Create new Remotion project
npx create-remotion@latest my-yojana-video

cd my-yojana-video

# Copy the video files
cp ../yojana_explainer_video.jsx src/
cp ../remotion_root.tsx src/
cp ../remotion.config.ts ./
```

### Manual Integration

If integrating into existing project:

```bash
npm install remotion ffmpeg ffprobe-static
```

Add to `package.json`:
```json
{
  "scripts": {
    "start": "remotion preview remotion_root.tsx",
    "render": "remotion render remotion_root.tsx YojanaMitra-Explainer-Video output.mp4"
  }
}
```

## 🎬 Preview & Rendering

### Preview (Live editing)
```bash
npm start
# Opens http://localhost:3000 with live preview
```

### Render to MP4
```bash
# High quality H.264 codec
npm run render

# Or directly
remotion render remotion_root.tsx YojanaMitra-Explainer-Video output.mp4 --fps 30 --width 1920 --height 1080
```

### Render with Custom Settings
```bash
remotion render remotion_root.tsx YojanaMitra-Explainer-Video output.mp4 \
  --fps 30 \
  --width 1920 \
  --height 1080 \
  --codec h264 \
  --pixel-format yuv420p \
  --quality 100
```

## 📋 Scenes Breakdown

### Scene 1: Intro (0-10s)
- Dark gradient background
- Animated title: "YOJANA MITRA"
- Subtitle: "Find What's Truly Yours"
- Scroll hint animation
- Floating background orbs

### Scene 2: Problem (10-20s)
- Light background
- Main problem statement with gradient text
- 3 animated icon cards
  - Endless Searching (😕)
  - Deadlines Missed (⏰)
  - Unclaimed Benefits (💰)

### Scene 3: Solution (20-30s)
- Dark gradient background
- "Meet YojanaMitra" title
- 3 feature cards showing:
  - ⚡ Fast Matching
  - 🏛️ 4,226+ Schemes
  - 🤖 AI-Powered

### Scene 4: How It Works (30-40s)
- Light background
- 3 sequential steps with numbered circles
- Left-to-right flow with arrow animations
  - Step 1: Tell Us About You
  - Step 2: AI Analyzes
  - Step 3: Get Your Match

### Scene 5: CTA (40-60s)
- Dark gradient background
- Main call-to-action text
- Pulsing gradient button
- Floating background animations

## 🛠️ Customization

### Change Colors
In `yojana_explainer_video.jsx`, find the color definitions:
```jsx
// Primary colors
const primaryColor = '#f97316'; // Orange
const darkGreen = '#0b1a16'; // Dark
const lightGreen = '#2d6a4f'; // Green
```

### Modify Text
Simply edit the text content in each Scene component:
```jsx
<h1>Your Custom Title Here</h1>
```

### Adjust Timing
Change frame durations in the main composition:
```jsx
{/* Change from 300 to 400 for longer scene */}
<Sequence from={0} durationInFrames={400}>
  <Scene1Intro />
</Sequence>
```

### Add New Scenes
1. Create new component (e.g., `Scene6Testimonials`)
2. Add to main composition with `<Sequence>`
3. Update total duration

## 📦 Dependencies

```json
{
  "dependencies": {
    "remotion": "^4.0.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.0.0",
    "@types/react-dom": "^18.0.0",
    "typescript": "^5.0.0"
  }
}
```

## 📚 Resources

- **Remotion Docs**: https://www.remotion.dev/docs
- **React Docs**: https://react.dev
- **Video Editing Patterns**: Industry standard SaaS explainer video techniques
- **Color Theory**: YojanaMitra brand guidelines

## 🎯 Professional Techniques Used

✅ **Gradient Mesh Backgrounds** - Creates visual depth  
✅ **Spring Physics** - Natural motion feels less robotic  
✅ **Staggered Animations** - Draws attention sequentially  
✅ **Backdrop Blur Effects** - Modern glassmorphism design  
✅ **Floating Elements** - Continuous subtle animation  
✅ **Text Drop Shadows** - Improves readability  
✅ **Color Gradients** - Professional polish  
✅ **Smooth Transitions** - No jarring cuts  
✅ **Responsive Typography** - Uses clamp() for scaling  
✅ **Accessibility** - Proper contrast ratios  

## 📝 Notes

- Video renders at **1920x1080 (Full HD)** at **30fps**
- Total duration: **60 seconds** = **1800 frames**
- Uses only **React and CSS animations** - no external video libraries
- Fully **responsive** animation system
- Can export to **MP4, ProRes, WebM**, etc.

## 🎬 Next Steps

1. Customize brand colors and text
2. Add your actual website screenshots/components
3. Render to MP4 for YouTube/social media
4. Add background music/sound effects
5. Export subtitle files

---

**Created with ❤️ for YojanaMitra**  
*Making government welfare accessible to all Indians*
