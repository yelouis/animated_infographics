import React, { createContext, useContext } from "react";
import type {
  TimelineCastMember,
  TimelinePlace,
  TimelineSetPiece,
} from "../generated/contracts";

export interface EntitiesContextValue {
  cast: Record<string, TimelineCastMember>;
  places: Record<string, TimelinePlace>;
  setPieces: Record<string, TimelineSetPiece>;
}

export const EntitiesContext = createContext<EntitiesContextValue>({
  cast: {},
  places: {},
  setPieces: {},
});

export const EntitiesProvider: React.FC<{
  value: EntitiesContextValue;
  children: React.ReactNode;
}> = ({ value, children }) => {
  return (
    <EntitiesContext.Provider value={value}>
      {children}
    </EntitiesContext.Provider>
  );
};

export const useCast = (
  id?: string | null
): TimelineCastMember | undefined => {
  const { cast } = useContext(EntitiesContext);
  if (!id) return undefined;
  return cast[id];
};

export const usePlace = (
  id?: string | null
): TimelinePlace | undefined => {
  const { places } = useContext(EntitiesContext);
  if (!id) return undefined;
  return places[id];
};

export const useSetPiece = (
  id?: string | null
): TimelineSetPiece | undefined => {
  const { setPieces } = useContext(EntitiesContext);
  if (!id) return undefined;
  return setPieces[id];
};
