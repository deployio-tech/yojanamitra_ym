/**
 * Remotion Root - Video Composition Entry Point (Enhanced)
 * Supports both Standard and Premium versions
 * 
 * Usage:
 * Standard: remotion render remotion_root_enhanced.tsx YojanaMitra-Explainer standard.mp4
 * Premium: remotion render remotion_root_enhanced.tsx YojanaMitraPremium premium.mp4
 */

import React from 'react';
import { Composition } from 'remotion';
import YojanaMitraExplainerComp from './yojana_explainer_video';
import YojanaMitraPremiumVideo from './yojana_premium_video';

export const RemotionRoot = () => {
  return (
    <>
      {/* Standard Version - 60 seconds */}
      <Composition
        id="YojanaMitra-Explainer"
        component={YojanaMitraExplainerComp}
        durationInFrames={1800}
        fps={30}
        width={1920}
        height={1080}
      />
      
      {/* Premium Version - 60 seconds */}
      <Composition
        id="YojanaMitraPremium"
        component={YojanaMitraPremiumVideo}
        durationInFrames={1800}
        fps={30}
        width={1920}
        height={1080}
      />
      
      {/* Portrait Version (for mobile/social) - Premium */}
      <Composition
        id="YojanaMitraPremium-Portrait"
        component={YojanaMitraPremiumVideo}
        durationInFrames={1800}
        fps={30}
        width={1080}
        height={1920}
      />
      
      {/* Square Version (for Instagram/LinkedIn) - Premium */}
      <Composition
        id="YojanaMitraPremium-Square"
        component={YojanaMitraPremiumVideo}
        durationInFrames={1800}
        fps={30}
        width={1080}
        height={1080}
      />
    </>
  );
};
