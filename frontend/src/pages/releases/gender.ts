/**
 * The researcher's gender as typed or pasted, as forgiving as dates (Daniel, 2026-11-08):
 * either language, any case or width, a word or its start. Empty means not recorded.
 */
export type Gender = "F" | "M" | "other";

const NONE = "none";
type Meaning = Gender | typeof NONE;

// Each word means one thing. The longer ones also work from their first two letters.
const WORDS: Record<Meaning, string[]> = {
  F: ["f", "w", "female", "woman", "women", "♀", "女", "女性", "女子"],
  M: ["m", "male", "man", "men", "♂", "男", "男性", "男子"],
  other: ["o", "x", "other", "diverse", "non-binary", "nonbinary", "nb", "その他", "他"],
  none: ["", "-", "–", "—", "?", "n/a", "na", "none", "unknown", "not recorded", "未記録", "不明"],
};
const PREFIX_FROM = 2;

function clean(text: string): string {
  return text.normalize("NFKC").trim().toLowerCase().replace(/\s+/g, " ").replace(/\.$/, "");
}

/** F, M or other; null for not recorded; undefined when it cannot tell. */
export function parseGender(text: string): Gender | null | undefined {
  const wanted = clean(text);
  const meanings = Object.entries(WORDS) as [Meaning, string[]][];
  let found = meanings.find(([, words]) => words.includes(wanted))?.[0];
  if (found === undefined && wanted.length >= PREFIX_FROM) {
    const matching = meanings.filter(([, words]) =>
      words.some((word) => word.length > PREFIX_FROM && word.startsWith(wanted)),
    );
    if (matching.length === 1) found = matching[0][0];
  }
  if (found === undefined) return undefined;
  return found === NONE ? null : found;
}

export const GENDERS: Gender[] = ["F", "M", "other"];
