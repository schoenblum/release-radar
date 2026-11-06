import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { homePath, useAuth } from "../auth";
import AuthCard from "../components/AuthCard";
import ErrorNotice from "../components/ErrorNotice";
import { PageLoading } from "../components/Spinner";

export default function Login() {
  const { t } = useTranslation();
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  if (loading) return <PageLoading />;
  if (user) return <Navigate to={homePath(user.role)} replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const signedIn = await login(email, password);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(signedIn.force_password_change ? "/change-password" : (from ?? "/"), {
        replace: true,
      });
    } catch (failure) {
      setError(failure);
      setSubmitting(false);
    }
  }

  return (
    <AuthCard title={t("login.title")}>
      <form onSubmit={(event) => void submit(event)} className="space-y-2xs">
        <div>
          <label className="field-label" htmlFor="email">
            {t("login.email")}
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
        <div>
          <label className="field-label" htmlFor="password">
            {t("login.password")}
          </label>
          <input
            id="password"
            className="input"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>
        <ErrorNotice error={error} />
        <button type="submit" className="btn-primary w-full" disabled={submitting}>
          {t("login.submit")}
        </button>
        <p className="text-center text-sm">
          <Link to="/forgot-password" className="link">
            {t("login.forgot")}
          </Link>
        </p>
      </form>
    </AuthCard>
  );
}
