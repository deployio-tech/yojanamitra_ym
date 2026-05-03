import { Config } from 'remotion';

/**
 * YojanaMitra SaaS Explainer Video Configuration
 * Remotion - Programmatic video generation with React
 */

Config.setVideoImageFormat('png');
Config.setCodec('h264');
Config.setShouldOverwriteOutput(true);
Config.setPixelFormat('yuv420p');
Config.setFrameRange([0, 1800]); // 60 seconds at 30fps

export default undefined;
