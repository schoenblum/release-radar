import { useTranslation } from "react-i18next";
import Markdown from "react-markdown";

import english from "../manual/en.md?raw";
import japanese from "../manual/ja.md?raw";

export default function Manual() {
  const { i18n } = useTranslation();
  return (
    <article className="manual">
      <Markdown>{i18n.language === "ja" ? japanese : english}</Markdown>
    </article>
  );
}
