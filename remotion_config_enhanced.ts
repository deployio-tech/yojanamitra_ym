/**
 * Remotion Configuration - Enhanced Version
 * Supports both standard and premium video compositions
 * 
 * This config handles multiple export variations:
 * - H.264 MP4 (streaming optimized)
 * - ProRes for professional workflows
 * - Multiple resolutions (1920x1080, 1080x1920, 1080x1080)
 */

import { Config } from "remotion";

export const MyConfig = Config.defineConfig({
  // Default output codec and format
  codecs: ["h264"],
  imageFormat: "png",
  pixelFormat: "yuv420p",
  
  // Enable concurrent rendering for faster production builds
  concurrency: 4,
  
  // Rendering output settings
  frameRange: [0, 1800],
  shouldOverwrite: true,
  
  // Quality settings
  crf: 18, // 0-28, lower = higher quality (default is 23)
  
  // Enable faster preview mode
  logImageSequence: false,
});

// Export function to render with custom settings
export const renderConfig = {
  // Standard resolution (16:9 - YouTube)
  standard: {
    width: 1920,
    height: 1080,
    fps: 30,
    durationInFrames: 1800,
  },
  
  // Portrait resolution (9:16 - TikTok/Instagram Reels)
  portrait: {
    width: 1080,
    height: 1920,
    fps: 30,
    durationInFrames: 1800,
  },
  
  // Square resolution (1:1 - Instagram/LinkedIn)
  square: {
    width: 1080,
    height: 1080,
    fps: 30,
    durationInFrames: 1800,
  },
  
  // High resolution (4K)
  '4k': {
    width: 3840,
    height: 2160,
    fps: 30,
    durationInFrames: 1800,
  },
};

export default MyConfig;
