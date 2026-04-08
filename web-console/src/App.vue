<template>
  <router-view />
</template>

<style>
:root {
  color-scheme: light;
  --ea-bg: #edf2f7;
  --ea-surface: #ffffff;
  --ea-surface-alt: #f8fafc;
  --ea-text: #17202b;
  --ea-text-muted: #53606f;
  --ea-primary: #1447a6;
  --ea-primary-strong: #0f3278;
  --ea-accent: #d3a449;
  --ea-border: rgba(15, 23, 32, 0.08);
  --ea-shadow: 0 18px 36px rgba(15, 23, 32, 0.08);
}

html,
body,
#app {
  min-height: 100%;
  margin: 0;
}

*,
*::before,
*::after {
  box-sizing: border-box;
}

body {
  font-family: 'Bahnschrift', 'Segoe UI', 'Microsoft YaHei', sans-serif;
  background:
    radial-gradient(circle at top left, rgba(211, 164, 73, 0.14), transparent 22%),
    linear-gradient(180deg, #eff4fb 0%, #edf2f7 100%);
  color: var(--ea-text);
  overflow-x: hidden;
}

button,
input,
select,
textarea {
  font: inherit;
}

a {
  color: inherit;
  text-decoration: none;
}

@media (max-width: 768px) {
  body {
    padding-bottom: calc(80px + env(safe-area-inset-bottom, 0px));
  }
}
</style>
