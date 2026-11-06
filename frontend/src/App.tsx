import type { ReactElement } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AuthProvider, homePath, useAuth } from "./auth";
import Layout from "./components/Layout";
import { PageLoading } from "./components/Spinner";
import ChangePassword from "./pages/ChangePassword";
import ForgotPassword from "./pages/ForgotPassword";
import Login from "./pages/Login";
import Manual from "./pages/Manual";
import Placeholder from "./pages/Placeholder";
import ResetPassword from "./pages/ResetPassword";

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

function Home() {
  const { user } = useAuth();
  return user ? <Navigate to={homePath(user.role)} replace /> : null;
}

export default function App() {
  return (
    <AuthProvider>
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
          <Route path="my-releases" element={<Placeholder page="my_releases" />} />
          <Route path="releases" element={<Placeholder page="all_releases" />} />
          <Route path="writers" element={<Placeholder page="writers" />} />
          <Route path="manual" element={<Manual />} />
          <Route
            path="settings"
            element={
              <RequireAdmin>
                <Placeholder page="settings" />
              </RequireAdmin>
            }
          />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
