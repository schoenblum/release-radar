import "@fontsource/eb-garamond/500.css";
import "@fontsource/noto-sans-jp/400.css";
import "@fontsource/noto-sans-jp/600.css";
import "@fontsource/noto-serif-jp/500.css";
import "@fontsource/open-sans/400-italic.css";
import "@fontsource/open-sans/400.css";
import "@fontsource/open-sans/600.css";
import "./index.css";
import "./i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { ApiError } from "./api/client";
import App from "./App";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Refresh when the window regains focus (R3.3.4). Lists add their 60-second
      // interval when they arrive.
      refetchOnWindowFocus: true,
      staleTime: 30_000,
      retry: (failures, error) =>
        !(error instanceof ApiError && error.status < 500) && failures < 2,
    },
  },
});

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
