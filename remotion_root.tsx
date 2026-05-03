import React from 'react';
import { Composition } from 'remotion';
import { YojanaMitraExplainerComp } from './yojana_explainer_video';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="YojanaMitra-Explainer-Video"
        component={YojanaMitraExplainerComp}
        durationInFrames={1800}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{}}
      />
    </>
  );
};
