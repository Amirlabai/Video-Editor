# ffmpegMagic — Accessibility Statement (Draft)

Application: ffmpegMagic  
Platform: Windows desktop  
UI stack: PyWebView + WebView2 + semantic HTML/CSS/JS  
Target standard: WCAG 2.1 Level AA (IS 5568 aligned where applicable)

## How accessibility works

HTML and ARIA in the WebView2 surface map to Windows UI Automation via Chromium. Native file and folder pickers use the OS dialog accessibility tree.

## Implemented measures

- Semantic landmarks: header, nav, main, footer
- Skip link to main content
- Modal dialogs with role="dialog", aria-modal, focus trap, Escape to close
- Live regions for progress, logs, alerts, and splash status
- Table captions and column scope attributes
- Checkbox labels and aria-labels on controls
- text_select=True in PyWebView host for copy/paste of errors
- Self-hosted fonts (system Segoe UI / Arial stack — no CDN)
- forced-colors and prefers-reduced-motion CSS support
- Visible :focus-visible outlines on interactive elements

## Known gaps

- Splash error strings are English only
- Manual screen-reader verification with Narrator pending per release

Last updated: 2026-06-14
