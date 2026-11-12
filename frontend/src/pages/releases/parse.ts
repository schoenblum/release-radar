/** How the grid understands what someone types or pastes. The server has the final word. */

export { normaliseDate } from "../../dates";

// The team's convention in the workbook: a dash means "does not apply" (BRIEF step 1.8).
const NOT_APPLICABLE = new Set(["-", "–", "—", "−", "n/a", "na", "n.a.", "該当なし"]);
const TRUE_WORDS = new Set(["y", "yes", "true", "1", "✓", "x", "on", "はい"]);
const FALSE_WORDS = new Set(["", "n", "no", "false", "0", "off", "いいえ"]);

export function isNotApplicable(text: string): boolean {
  return NOT_APPLICABLE.has(text.normalize("NFKC").trim().toLowerCase());
}

export function parseBoolean(text: string): boolean | null {
  const word = text.normalize("NFKC").trim().toLowerCase();
  if (TRUE_WORDS.has(word)) return true;
  if (FALSE_WORDS.has(word)) return false;
  return null;
}

export function formatNumber(value: number): string {
  return value.toLocaleString("en-US", { maximumFractionDigits: 2 });
}

const DOI_START = /^(https?:\/\/(dx\.)?doi\.org\/|doi:\s*|10\.\d{4,9}\/)/i;

/** The new-release row takes a DOI or a title, and tells them apart by themselves. */
export function looksLikeDoi(text: string): boolean {
  return DOI_START.test(text.trim());
}
