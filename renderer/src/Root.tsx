import React from "react";
import { Composition } from "remotion";

const TrivialComponent: React.FC = () => {
  return <div>Trivial</div>;
};

export const Root: React.FC = () => {
  return (
    <Composition
      id="Trivial"
      component={TrivialComponent}
      durationInFrames={1}
      fps={30}
      width={1080}
      height={1920}
    />
  );
};
