#!/bin/bash

##############################################################################
# YojanaMitra Explainer Video - Quick Start Setup
# 
# This script sets up Remotion and generates your video
# Usage: bash setup_video.sh
##############################################################################

echo "🎬 YojanaMitra Explainer Video Setup"
echo "===================================="
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 16+"
    exit 1
fi

echo "✅ Node.js found: $(node --version)"
echo ""

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm not found. Please install npm"
    exit 1
fi

echo "✅ npm found: $(npm --version)"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
npm install remotion ffmpeg-static

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed"
echo ""

# Create package.json scripts if not exists
if ! grep -q '"scripts"' package.json 2>/dev/null; then
    echo "📝 Adding scripts to package.json..."
    npm set-script start "remotion preview remotion_root.tsx"
    npm set-script render "remotion render remotion_root.tsx YojanaMitra-Explainer-Video output.mp4 --fps 30 --width 1920 --height 1080 --quality 100"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Available commands:"
echo ""
echo "   npm start"
echo "   └─ Preview video in browser with live reload"
echo ""
echo "   npm run render"
echo "   └─ Render to output.mp4 (High quality)"
echo ""
echo "🎯 Next steps:"
echo "   1. npm start          (Preview the video)"
echo "   2. Edit yojana_explainer_video.jsx"
echo "   3. npm run render     (Generate MP4)"
echo ""
