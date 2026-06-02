<template>
  <router-view />
</template>

<style>
:root {
  color-scheme: light;
  --ea-bg: #f3f6fa;
  --ea-surface: #ffffff;
  --ea-surface-alt: #f8fafc;
  --ea-text: #0f172a;
  --ea-text-muted: #475569;
  --ea-primary: #1d4ed8;
  --ea-primary-strong: #1e3a8a;
  --ea-accent: #0f766e;
  --ea-border: #d9e2ec;
  --ea-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
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
    radial-gradient(circle at top left, rgba(29, 78, 216, 0.05), transparent 22%),
    linear-gradient(180deg, #f8fafc 0%, #f3f6fa 100%);
  color: var(--ea-text);
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
</style>
