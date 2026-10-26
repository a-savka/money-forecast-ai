import { Navigate, Outlet, Route, Routes } from 'react-router-dom'

import { AppLayout } from '@/components/layout/AppLayout'
import { Toaster } from '@/components/Toaster'
import { AnalyticsPage } from '@/features/analytics/AnalyticsPage'
import { BudgetsPage } from '@/features/budgets/BudgetsPage'
import { ExperimentsPage } from '@/features/experiments/ExperimentsPage'
import { FamilyPage } from '@/features/family/FamilyPage'
import { ForecastPage } from '@/features/forecast/ForecastPage'
import { HomePage } from '@/features/home/HomePage'
import { LoginPage } from '@/features/auth/LoginPage'
import { ConnectBankPage } from '@/features/import/ConnectBankPage'
import { ImportPage } from '@/features/import/ImportPage'
import { ReceiptPage } from '@/features/import/ReceiptPage'
import { ScreenshotPage } from '@/features/import/ScreenshotPage'
import { useAlertsNotifier } from '@/features/notifications/api'
import { RecommendationsPage } from '@/features/recommendations/RecommendationsPage'
import { TransactionsPage } from '@/features/transactions/TransactionsPage'
import { PremiumPage } from '@/features/subscription/PremiumPage'
import { MorePage } from '@/pages/MorePage'
import { useSession } from '@/store/session'

function AuthedShell() {
  useAlertsNotifier()
  return (
    <>
      <Toaster />
      <Outlet />
    </>
  )
}

function RequireAuth() {
  const token = useSession((s) => s.token)
  return token ? <AuthedShell /> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route index element={<HomePage />} />
          <Route path="transactions" element={<TransactionsPage />} />
          <Route path="forecast" element={<ForecastPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="more" element={<MorePage />} />
        </Route>
        <Route path="import" element={<ImportPage />} />
        <Route path="connect-bank" element={<ConnectBankPage />} />
        <Route path="receipt" element={<ReceiptPage />} />
        <Route path="screenshot" element={<ScreenshotPage />} />
        <Route path="recommendations" element={<RecommendationsPage />} />
        <Route path="experiments" element={<ExperimentsPage />} />
        <Route path="premium" element={<PremiumPage />} />
        <Route path="family" element={<FamilyPage />} />
        <Route path="budgets" element={<BudgetsPage />} />
        <Route path="onboarding" element={<Navigate to="/transactions" replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
