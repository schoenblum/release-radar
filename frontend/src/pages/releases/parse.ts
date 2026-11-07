/** How the grid understands what someone types or pastes. The server has the final word. */

// The team's convention in the workbook: a dash means "does not apply" (BRIEF step 1.8).
const NOT_APPLICABLE = new Set(["-", "–", "—", "−", "n/a", "na", "n.a.", "該当なし"]);
const TRUE_WORDS = new Set(["y", "yes", "true", "1", "✓", "x", "on", "はい"]);
const FALSE_WORDS = new Set(["", "n", "no", "false", "0", "off", "いいえ"]);
const MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];

export function isNotApplicable(text: string): boolean {
  return NOT_APPLICABLE.has(text.normalize("NFKC").trim().toLowerCase());
}

export function parseBoolean(text: string): boolean | null {
  const word = text.normalize("NFKC").trim().toLowerCase();
  if (TRUE_WORDS.has(word)) return true;
  if (FALSE_WORDS.has(word)) return false;
  return null;
}

function iso(year: number, month: number, day: number): string | null {
  const date = new Date(Date.UTC(year, month - 1, day));
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1) return null;
  if (date.getUTCDate() !== day) return null;
  return `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

/**
 * Dates as they arrive by hand or by paste: 2026-04-09, 2026/4/9, 9-Apr-26. Anything else goes
 * to the server unchanged, to be refused with an explanation. Day and month are never guessed
 * from a form like 4/9/2026, which reads differently in different countries.
 */
export function normaliseDate(text: string): string {
  const clean = text.normalize("NFKC").trim();
  const numeric = /^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$/.exec(clean);
  if (numeric) return iso(+numeric[1], +numeric[2], +numeric[3]) ?? clean;
  const japanese = /^(\d{4})年(\d{1,2})月(\d{1,2})日$/.exec(clean);
  if (japanese) return iso(+japanese[1], +japanese[2], +japanese[3]) ?? clean;
  const named = /^(\d{1,2})[-\s]([A-Za-z]{3,9})[-\s,]*(\d{2}|\d{4})$/.exec(clean);
  if (named) {
    const month = MONTHS.indexOf(named[2].slice(0, 3).toLowerCase());
    const year = named[3].length === 2 ? 2000 + +named[3] : +named[3];
    if (month !== -1) return iso(year, month + 1, +named[1]) ?? clean;
  }
  return clean;
}

export function formatNumber(value: number): string {
  return value.toLocaleString("en-US", { maximumFractionDigits: 2 });
}

const DOI_START = /^(https?:\/\/(dx\.)?doi\.org\/|doi:\s*|10\.\d{4,9}\/)/i;

/** The new-release row takes a DOI or a title, and tells them apart by themselves. */
export function looksLikeDoi(text: string): boolean {
  return DOI_START.test(text.trim());
}
