import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api, onSessionLost, refreshSession } from "./api/client";
import type { User, UserRole } from "./api/types";
import { applyLanguage, currentLanguage } from "./i18n";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<User>;
  setUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Where each role lands after signing in (D10). Configurable per role from step 1.3. */
export function homePath(role: UserRole): string {
  return role === "viewer" ? "/releases" : "/my-releases";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  /**
   * Use the language saved on the account. A first-time user keeps the one on
   * screen, and it is saved, so the emails they receive use it too.
   */
  const adopt = useCallback((signedIn: User): User => {
    if (signedIn.language) {
      applyLanguage(signedIn.language);
    } else {
      void api.updateMe({ language: currentLanguage() }).catch(() => undefined);
    }
    setUserState(signedIn);
    return signedIn;
  }, []);

  useEffect(() => {
    onSessionLost(() => setUserState(null));
    // A valid session cookie restores the sign-in after a page reload.
    refreshSession()
      .then((result) => adopt(result.user))
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, [adopt]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      login: async (email, password) => adopt((await api.login(email, password)).user),
      logout: async () => {
        try {
          await api.logout();
        } finally {
          setUserState(null);
        }
      },
      changePassword: async (currentPassword, newPassword) =>
        adopt((await api.changePassword(currentPassword, newPassword)).user),
      setUser: setUserState,
    }),
    [user, loading, adopt],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
