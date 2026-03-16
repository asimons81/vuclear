import { create } from "zustand";
import { persist } from "zustand/middleware";

type AppStore = {
  tosAccepted: boolean;
  theme: "system" | "light" | "dark";
  acceptTos: () => void;
  setTheme: (theme: "system" | "light" | "dark") => void;
};

export const useAppStore = create<AppStore>()(
  persist(
    (set) => ({
      tosAccepted: false,
      theme: "system",
      acceptTos: () => set({ tosAccepted: true }),
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: "vuclear-app",
      partialize: (state) => ({
        tosAccepted: state.tosAccepted,
        theme: state.theme,
      }),
    },
  ),
);
