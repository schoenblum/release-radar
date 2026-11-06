import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../auth";

export default function UserMenu() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: PointerEvent) {
      if (!container.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  if (!user) return null;

  async function signOut() {
    setOpen(false);
    await logout().catch(() => undefined);
    navigate("/login", { replace: true });
  }

  return (
    <div className="relative" ref={container}>
      <button
        type="button"
        className="btn-quiet max-w-52"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t("user_menu.open")}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="truncate">{user.full_name ?? user.email}</span>
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 z-20 mt-5xs w-64 rounded border border-line-disabled bg-surface-primary py-4xs shadow-md"
        >
          <div className="border-b border-line-disabled px-2xs pb-4xs">
            <div className="truncate text-sm">{user.email}</div>
            <div className="text-sm text-content-secondary">
              {t(`user_menu.roles.${user.role}`)}
            </div>
          </div>
          <Link
            role="menuitem"
            to="/change-password"
            className="block px-2xs py-4xs text-sm hover:bg-surface-secondary"
            onClick={() => setOpen(false)}
          >
            {t("user_menu.change_password")}
          </Link>
          <button
            type="button"
            role="menuitem"
            className="block w-full px-2xs py-4xs text-left text-sm hover:bg-surface-secondary"
            onClick={() => void signOut()}
          >
            {t("user_menu.sign_out")}
          </button>
        </div>
      )}
    </div>
  );
}
