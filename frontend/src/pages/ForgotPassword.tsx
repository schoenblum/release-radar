import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import AuthCard from "../components/AuthCard";
import ErrorNotice from "../components/ErrorNotice";

export default function ForgotPassword() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [result, setResult] = useState<"sent" | "email_disabled" | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { email_enabled: emailEnabled } = await api.forgotPassword(email);
      setResult(emailEnabled ? "sent" : "email_disabled");
    } catch (failure) {
      setError(failure);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthCard title={t("forgot.title")}>
      {result ? (
        <p role="status" className="notice-info">
          {result === "sent" ? t("forgot.sent") : t("forgot.email_disabled")}
        </p>
      ) : (
        <form onSubmit={(event) => void submit(event)} className="space-y-2xs">
          <p>{t("forgot.intro")}</p>
          <div>
            <label className="field-label" htmlFor="email">
              {t("forgot.email")}
            </label>
            <input
              id="email"
              className="input"
              type="email"
              autoComplete="username"
              required
              autoFocus
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <ErrorNotice error={error} />
          <button type="submit" className="btn-primary w-full" disabled={submitting}>
            {t("forgot.submit")}
          </button>
        </form>
      )}
      <p className="mt-2xs text-center text-sm">
        <Link to="/login" className="link">
          {t("forgot.back")}
        </Link>
      </p>
    </AuthCard>
  );
}
