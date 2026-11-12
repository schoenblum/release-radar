import type { ReactElement } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AuthProvider, homePath, useAuth } from "./auth";
import Layout from "./components/Layout";
import { PageLoading } from "./components/Spinner";
import { ToastProvider } from "./components/Toast";
import ChangePassword from "./pages/ChangePassword";
import ForgotPassword from "./pages/ForgotPassword";
import Login from "./pages/Login";
import Manual from "./pages/Manual";
import MyFields from "./pages/MyFields";
import Researchers from "./pages/Researchers";
import ResetPassword from "./pages/ResetPassword";
import DataPage from "./pages/releases/DataPage";
import CheckpointsSettings from "./pages/settings/Checkpoints";
import DataSettings from "./pages/settings/Data";
import FormSettings from "./pages/settings/Form";
import InstitutionSettings from "./pages/settings/Institution";
import IntegrationsSettings from "./pages/settings/Integrations";
import ListsSettings from "./pages/settings/Lists";
import ScoreProfilesSettings from "./pages/settings/ScoreProfiles";
import SettingsLayout from "./pages/settings/SettingsLayout";
import UsersSettings from "./pages/settings/Users";
import WritersPage from "./pages/writers/WritersPage";

function RequireAuth({ children }: { children: ReactElement }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <PageLoading />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (user.force_password_change && location.pathname !== "/change-password") {
    return <Navigate to="/change-password" replace />;
  }
  return children;
}

function RequireAdmin({ children }: { children: ReactElement }) {
  const { user } = useAuth();
  if (user?.role !== "admin") return <Navigate to="/" replace />;
  return children;
}

function RequireEditor({ children }: { children: ReactElement }) {
  const { user } = useAuth();
  if (user?.role !== "admin" && user?.role !== "editor") return <Navigate to="/" replace />;
  return children;
}

function Home() {
  const { user } = useAuth();
  return user ? <Navigate to={homePath(user)} replace /> : null;
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route
            path="/change-password"
            element={
              <RequireAuth>
                <ChangePassword />
              </RequireAuth>
            }
          />
          <Route
            element={
              <RequireAuth>
                <Layout />
              </RequireAuth>
            }
          >
            <Route index element={<Home />} />
            <Route path="data" element={<DataPage />} />
            <Route path="writers" element={<WritersPage />} />
            <Route path="manual" element={<Manual />} />
            <Route
              path="researchers"
              element={
                <RequireEditor>
                  <Researchers />
                </RequireEditor>
              }
            />
            <Route
              path="my-fields"
              element={
                <RequireEditor>
                  <MyFields />
                </RequireEditor>
              }
            />
            <Route
              path="settings"
              element={
                <RequireAdmin>
                  <SettingsLayout />
                </RequireAdmin>
              }
            >
              <Route index element={<Navigate to="institution" replace />} />
              <Route path="institution" element={<InstitutionSettings />} />
              <Route path="users" element={<UsersSettings />} />
              <Route path="lists" element={<ListsSettings />} />
              <Route path="lists/:kind" element={<ListsSettings />} />
              <Route path="researchers" element={<Researchers />} />
              <Route path="form" element={<FormSettings />} />
              <Route path="checkpoints" element={<CheckpointsSettings />} />
              <Route path="score_profiles" element={<ScoreProfilesSettings />} />
              <Route path="integrations" element={<IntegrationsSettings />} />
              <Route path="data" element={<DataSettings />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </ToastProvider>
    </AuthProvider>
  );
}
