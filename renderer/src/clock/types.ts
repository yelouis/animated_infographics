// Clock abstraction types from design_rendering.md §3.

export type SceneClock = {
  frame: number; // since scene start; float-safe (live mode will pass fractional frames)
  fps: 30;
  sceneFrames: number; // end_frame - start_frame
  phase: "enter" | "hold" | "exit";
  enterProgress: number; // 0..1 over ENTER_FRAMES
  exitProgress: number; // 0..1 over EXIT_FRAMES after sceneFrames; 0 before
};

export type GlobalClock = {
  frame: number;
  fps: 30;
};
