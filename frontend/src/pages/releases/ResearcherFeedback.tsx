import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { http } from "../../api/client";
import type { FeedbackItem, FeedbackResponse } from "../../api/types";
import { useBrand } from "../../brand";
import { formatDate } from "../../dates";

const SCALE = [1, 2, 3, 4, 5] as const;

function isScore(value: unknown): value is (typeof SCALE)[number] {
  return typeof value === "number" && (SCALE as readonly number[]).includes(value);
}

function label(item: FeedbackItem, isJa: boolean): string {
  return (isJa && item.label_ja) || item.label_en;
}

/** One multiple-choice question: what was ticked, or that it was skipped (missing, not 0). */
function Choices({
  response,
  question,
  title,
}: {
  response: FeedbackResponse;
  question: "inquiries" | "activities";
  title: string;
}) {
  const { t, i18n } = useTranslation();
  const isJa = i18n.language === "ja";
  const items = response.items.filter((item) => item.question === question);
  const answered = items.some((item) => item.key in response.answers);
  const ticked = items.filter((item) => response.answers[item.key] === true);
  const other = response.other_texts[question];
  let text: string;
  if (!answered && !other) text = t("data.feedback.not_answered");
  else if (ticked.length === 0 && !other) text = t("data.feedback.none");
  else text = ticked.map((item) => label(item, isJa)).join(", ");
  return (
    <>
      <dt className="font-semibold">{title}</dt>
      <dd>
        {text}
        {other && (
          <span className="block text-content-secondary">
            {t("data.feedback.other", { text: other })}
          </span>
        )}
      </dd>
    </>
  );
}

function Response({ response }: { response: FeedbackResponse }) {
  const { t, i18n } = useTranslation();
  const { timezone } = useBrand();
  const isJa = i18n.language === "ja";
  const statements = response.items.filter((item) => item.question === "satisfaction");
  const comment = response.answers.comments;
  const facts = [
    response.submitted_at ? formatDate(response.submitted_at, timezone) : null,
    response.language ? t(`data.feedback.language_${response.language}`) : null,
    response.respondent_name,
    response.source === "legacy_import"
      ? t("data.feedback.imported", { template: response.template_name })
      : null,
  ].filter(Boolean);
  return (
    <article className="mb-3xs border-b border-line-disabled pb-3xs last:border-b-0">
      <p className="mb-4xs text-sm text-content-secondary">{facts.join(" · ")}</p>
      <dl className="grid gap-x-3xs gap-y-5xs text-sm sm:grid-cols-[10rem_1fr]">
        {statements.map((item) => {
          const score = response.answers[item.key];
          return (
            <div key={item.key} className="contents">
              <dt className="font-semibold">{label(item, isJa)}</dt>
              <dd>
                {isScore(score)
                  ? t("data.feedback.scale", { word: t(`data.feedback.scale_${score}`), score })
                  : t("data.feedback.not_answered")}
              </dd>
            </div>
          );
        })}
        <Choices response={response} question="activities" title={t("data.feedback.activities")} />
        <Choices response={response} question="inquiries" title={t("data.feedback.inquiries")} />
        <dt className="font-semibold">{t("data.feedback.comments")}</dt>
        <dd className="whitespace-pre-line">
          {typeof comment === "string" && comment ? comment : "—"}
        </dd>
      </dl>
    </article>
  );
}

/**
 * The record's Researcher feedback section (R8.1.2): each response in words. Office users only;
 * names stay here, never on guest pages.
 */
export default function ResearcherFeedback({ releaseId }: { releaseId: string }) {
  const { t } = useTranslation();
  const { data: responses } = useQuery({
    queryKey: ["releases", releaseId, "feedback"],
    queryFn: () => http.get<FeedbackResponse[]>(`/releases/${releaseId}/feedback`),
  });
  if (!responses) return null;
  return (
    <section className="drawer-section">
      <h3 className="drawer-heading">{t("data.feedback.title")}</h3>
      {responses.length === 0 ? (
        <p className="text-sm text-content-secondary">{t("data.feedback.no_responses")}</p>
      ) : (
        responses.map((response) => <Response key={response.id} response={response} />)
      )}
    </section>
  );
}
