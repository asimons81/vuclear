const themeScript = `
(() => {
  const key = "vuclear-app";
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)");
  let theme = "system";

  try {
    const raw = window.localStorage.getItem(key);
    if (raw) {
      const parsed = JSON.parse(raw);
      const stored = parsed?.state?.theme;
      if (stored === "light" || stored === "dark" || stored === "system") {
        theme = stored;
      }
    }
  } catch {}

  const resolved = theme === "system" ? (prefersDark.matches ? "dark" : "light") : theme;
  document.documentElement.dataset.theme = resolved;
  document.documentElement.style.colorScheme = resolved;
})();
`;

export default function ThemeScript() {
  return <script dangerouslySetInnerHTML={{ __html: themeScript }} />;
}
