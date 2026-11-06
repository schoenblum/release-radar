import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { homePath, useAuth } from "../auth";
import AuthCard from "../components/AuthCard";
import ErrorNotice from "../components/ErrorNotice";

export default function ChangePassword() {
  const { t } = useTranslation();
  const { user, changePassword } = useAuth();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);
  const forced = user?.force_password_change ?? false;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (password !== confirmation) {
      setError(new ApiError(422, "password_mismatch"));
      return;
    }
    setSubmitting(true);
    try {
      const updated = await changePassword(current, password);
      navigate(homePath(updated), { replace: true });
    } catch (failure) {
      setError(failure);
      setSubmitting(false);
    }
  }

  return (
    <AuthCard title={t("change_password.title")}>
      {forced && (
        <p role="status" className="notice-info mb-2xs">
          {t("change_password.forced_notice")}
        </p>
      )}
      <form onSubmit={(event) => void submit(event)} className="space-y-2xs">
        <div>
          <label className="field-label" htmlFor="current-password">
            {t("change_password.current_password")}
          </label>
          <input
            id="current-password"
            className="input"
            type="password"
            autoComplete="current-password"
            required
            autoFocus
            value={current}
            onChange={(event) => setCurrent(event.target.value)}
          />
        </div>
        <div>
          <label className="field-label" htmlFor="new-password">
            {t("change_password.new_password")}
          </label>
          <input
            id="new-password"
            className="input"
            type="password"
            autoComplete="new-password"
            required
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
            {t("change_password.confirm_password")}
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
          {t("change_password.submit")}
        </button>
      </form>
      {!forced && (
        <p className="mt-2xs text-center text-sm">
          <Link to="/" className="link">
            {t("change_password.back")}
          </Link>
        </p>
      )}
    </AuthCard>
  );
}
