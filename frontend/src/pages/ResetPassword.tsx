import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import { api, ApiError } from "../api/client";
import AuthCard from "../components/AuthCard";
import ErrorNotice from "../components/ErrorNotice";

export default function ResetPassword() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    setError(null);
    if (password !== confirmation) {
      setError(new ApiError(422, "password_mismatch"));
      return;
    }
    setSubmitting(true);
    try {
      await api.resetPassword(token, password);
      setDone(true);
    } catch (failure) {
      setError(failure);
    } finally {
      setSubmitting(false);
    }
  }

  if (!token) {
    return (
      <AuthCard title={t("reset.title")}>
        <p role="alert" className="notice-error">
          {t("reset.missing_token")}
        </p>
        <p className="mt-2xs text-center text-sm">
          <Link to="/forgot-password" className="link">
            {t("reset.request_new")}
          </Link>
        </p>
      </AuthCard>
    );
  }

  if (done) {
    return (
      <AuthCard title={t("reset.title")}>
        <p role="status" className="notice-info">
          {t("reset.done")}
        </p>
        <p className="mt-2xs text-center text-sm">
          <Link to="/login" className="link">
            {t("reset.to_login")}
          </Link>
        </p>
      </AuthCard>
    );
  }

  return (
    <AuthCard title={t("reset.title")}>
      <form onSubmit={(event) => void submit(event)} className="space-y-2xs">
        <div>
          <label className="field-label" htmlFor="new-password">
            {t("reset.new_password")}
          </label>
          <input
            id="new-password"
            className="input"
            type="password"
            autoComplete="new-password"
            required
            autoFocus
            aria-describedby="password-hint"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <p id="password-hint" className="field-hint">
            {t("change_password.hint")}
          </p>
        </div>
        <div>
          <label className="field-label" htmlFor="confirm-password">
            {t("reset.confirm_password")}
          </label>
          <input
            id="confirm-password"
            className="input"
            type="password"
            autoComplete="new-password"
            required
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
          />
        </div>
        <ErrorNotice error={error} />
        <button type="submit" className="btn-primary w-full" disabled={submitting}>
          {t("reset.submit")}
        </button>
      </form>
    </AuthCard>
  );
}
