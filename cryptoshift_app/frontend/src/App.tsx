import { Routes, Route, Link } from "react-router-dom";
import { Shell } from "./components/Shell";
import { Overview, Repositories, Inventory, Risk, Planner } from "./pages/core";
import { PatchStudio, Verification, Traces, Rollback, Reports, Settings } from "./pages/workflow";
import LabPage from "./pages/anatomy/LabPage";
import QuantumPage from "./pages/anatomy/QuantumPage";
import AssetPage from "./pages/anatomy/AssetPage";
import DependenciesPage from "./pages/anatomy/DependenciesPage";
import MigrationPage from "./pages/anatomy/MigrationPage";
import { Empty, PageHeader } from "./components/ui";

function NotFound() {
  return (
    <>
      <PageHeader title="Page not found" />
      <Empty>
        There is no page at this address. <Link to="/">Back to Overview</Link>
      </Empty>
    </>
  );
}

export function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Overview />} />
        <Route path="repositories" element={<Repositories />} />
        <Route path="inventory" element={<Inventory />} />
        <Route path="risk" element={<Risk />} />
        <Route path="planner" element={<Planner />} />
        <Route path="patches" element={<PatchStudio />} />
        <Route path="verification" element={<Verification />} />
        <Route path="traces" element={<Traces />} />
        <Route path="rollback" element={<Rollback />} />
        <Route path="anatomy" element={<LabPage />} />
        <Route path="anatomy/quantum-computer" element={<QuantumPage />} />
        <Route path="anatomy/cryptographic-asset" element={<AssetPage />} />
        <Route path="anatomy/banking-dependencies" element={<DependenciesPage />} />
        <Route path="anatomy/verified-migration" element={<MigrationPage />} />
        <Route path="reports" element={<Reports />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
