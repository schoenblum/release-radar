import { Children, isValidElement, useEffect, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import Markdown from "react-markdown";

import english from "../manual/en.md?raw";
import japanese from "../manual/ja.md?raw";

/** An address for a heading, in either language: letters and digits kept, the rest a dash. */
export function headingId(text: string): string {
  return text
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-+|-+$/g, "");
}

function plainText(children: ReactNode): string {
  return Children.toArray(children)
    .map((child) =>
      typeof child === "string" || typeof child === "number"
        ? String(child)
        : isValidElement<{ children?: ReactNode }>(child)
          ? plainText(child.props.children)
          : "",
    )
    .join("");
}

/** The sections of the page, from its second-level headings, in order. */
export function sections(markdown: string): { id: string; title: string }[] {
  return markdown
    .split("\n")
    .filter((line) => line.startsWith("## "))
    .map((line) => {
      const title = line.slice(3).replace(/\*\*/g, "").trim();
      return { id: headingId(title), title };
    });
}

const COMPONENTS = {
  h2: ({ children }: { children?: ReactNode }) => (
    <h2 id={headingId(plainText(children))}>{children}</h2>
  ),
};

/** Short and task-first (step 1.9): the title and its line, the contents, then the sections. */
export default function Manual() {
  const { t, i18n } = useTranslation();
  const text = i18n.language === "ja" ? japanese : english;
  // A link from another page to one section, such as the one on Settings → Integrations.
  useEffect(() => {
    const hash = window.location.hash.slice(1);
    if (hash) document.getElementById(decodeURIComponent(hash))?.scrollIntoView();
  }, [i18n.language]);
  const split = text.indexOf("\n## ");
  const intro = split < 0 ? text : text.slice(0, split);
  const body = split < 0 ? "" : text.slice(split + 1);
  return (
    <article className="manual">
      <Markdown components={COMPONENTS}>{intro}</Markdown>
      <nav aria-label={t("manual.contents")} className="manual-contents">
        <p className="manual-contents-title">{t("manual.contents")}</p>
        <ol>
          {sections(body).map((section) => (
            <li key={section.id}>
              <a href={`#${section.id}`}>{section.title}</a>
            </li>
          ))}
        </ol>
      </nav>
      <Markdown components={COMPONENTS}>{body}</Markdown>
    </article>
  );
}
