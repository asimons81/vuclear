import { create } from "zustand";
import { persist } from "zustand/middleware";

type AppStore = {
  tosAccepted: boolean;
  acceptTos: () => void;
};

export const useAppStore = create<AppStore>()(
  persist(
    (set) => ({
      tosAccepted: false,
      acceptTos: () => set({ tosAccepted: true }),
    }),
    { name: "vuclear-app" },
  ),
);
