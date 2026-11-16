import * as React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./anatomy/kit/iso.css";
import "./styles.css";
import "./auth/auth.css";
import { App } from "./App";
import { AuthProvider, AuthGate } from "./auth/Auth";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthProvider>
      <AuthGate>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AuthGate>
    </AuthProvider>
  </React.StrictMode>,
);
