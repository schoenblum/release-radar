import type { ReactNode } from "react";

import { useBrand } from "../brand";
import LanguageToggle from "./LanguageToggle";
import Wordmark from "./Wordmark";

/** The frame around the pages shown before someone is fully signed in. */
export default function AuthCard({ title, children }: { title: string; children: ReactNode }) {
  const { institutionName, logoUrl } = useBrand();
  return (
    <div className="flex min-h-screen flex-col bg-surface-secondary">
      <div className="flex justify-end p-2xs">
        <LanguageToggle />
      </div>
      <main className="flex flex-1 items-start justify-center px-2xs pb-l sm:pt-m">
        <div className="w-full max-w-md rounded-lg bg-surface-primary p-s shadow-sm">
          <Wordmark stacked />
          {/* A logo already says who this is. */}
          {institutionName && !logoUrl && (
            <p className="mt-5xs text-sm text-content-secondary">{institutionName}</p>
          )}
          <div className="accent-rule my-2xs" />
          <h1 className="mb-2xs text-2xl">{title}</h1>
          {children}
        </div>
      </main>
    </div>
  );
}
