import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useTranslation } from "react-i18next";

interface Message {
  text: string;
  undo?: () => void;
}

const VISIBLE_MS = 6000;
const ToastContext = createContext<((message: Message) => void) | null>(null);

/** Short confirmations, with Undo in place of "are you sure?" for reversible actions. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const [message, setMessage] = useState<Message | null>(null);
  const show = useCallback((next: Message) => setMessage(next), []);
  const value = useMemo(() => show, [show]);

  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => setMessage(null), VISIBLE_MS);
    return () => clearTimeout(timer);
  }, [message]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      {message && (
        <div role="status" className="toast">
          <span>{message.text}</span>
          {message.undo && (
            <button
              type="button"
              className="btn-small"
              onClick={() => {
                message.undo?.();
                setMessage(null);
              }}
            >
              {t("common.undo")}
            </button>
          )}
        </div>
      )}
    </ToastContext.Provider>
  );
}

export function useToast(): (message: Message) => void {
  const show = useContext(ToastContext);
  if (!show) throw new Error("useToast must be used inside ToastProvider");
  return show;
}
