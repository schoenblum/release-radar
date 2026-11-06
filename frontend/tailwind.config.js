// Colours, fonts and radii come only from the theme tokens, which the backend
// serves from the brand pack as /brand/theme.css. The palette is replaced rather
// than extended, so a class such as bg-slate-500 simply does not exist.
const token = (name) => `var(--${name})`;

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    colors: {
      transparent: "transparent",
      current: "currentColor",
      surface: {
        primary: token("surface-primary"),
        accent: token("surface-accent"),
        secondary: token("surface-secondary"),
        tertiary: token("surface-tertiary"),
        alert: token("surface-alert"),
      },
      content: {
        primary: token("text-primary"),
        accent: token("text-accent"),
        secondary: token("text-secondary"),
        alert: token("text-alert"),
        "on-accent": token("text-on-accent"),
      },
      line: {
        primary: token("border-primary"),
        disabled: token("border-disabled"),
      },
      accent: {
        10: token("accent-10"),
        30: token("accent-30"),
        50: token("accent-50"),
        70: token("accent-70"),
        90: token("accent-90"),
      },
      tag: {
        1: token("tag01"),
        "1-line": token("tag01-border"),
        2: token("tag02"),
        "2-line": token("tag02-border"),
        3: token("tag03"),
        "3-line": token("tag03-border"),
        4: token("tag04"),
        "4-line": token("tag04-border"),
      },
    },
    fontFamily: {
      heading: token("font-heading"),
      body: token("font-body"),
      wordmark: token("font-wordmark"),
    },
    borderRadius: {
      none: "0",
      sm: token("radius-sm"),
      DEFAULT: token("radius-md"),
      md: token("radius-md"),
      lg: token("radius-lg"),
      full: token("radius-full"),
    },
    extend: {
      spacing: {
        "5xs": token("space-5xs"),
        "4xs": token("space-4xs"),
        "3xs": token("space-3xs"),
        "2xs": token("space-2xs"),
        xs: token("space-xs"),
        s: token("space-s"),
        m: token("space-m"),
        l: token("space-l"),
        xl: token("space-xl"),
      },
    },
  },
  plugins: [],
};
