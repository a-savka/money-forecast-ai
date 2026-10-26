import { Navigate, Outlet, Route, Routes } from 'react-router-dom'

import { AppLayout } from '@/components/layout/AppLayout'
import { LoginPage } from '@/features/auth/LoginPage'
import { ImportPage } from '@/features/import/ImportPage'
import { TransactionsPage } from '@/features/transactions/TransactionsPage'
import { MorePage } from '@/pages/MorePage'
import { Placeholder } from '@/pages/Placeholder'
import { useSession } from '@/store/session'

function RequireAuth() {
  const token = useSession((s) => s.token)
  return token ? <Outlet /> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route index element={<Placeholder title="Главная" />} />
          <Route path="transactions" element={<TransactionsPage />} />
          <Route path="forecast" element={<Placeholder title="Прогноз" />} />
          <Route path="analytics" element={<Placeholder title="Аналитика" />} />
          <Route path="more" element={<MorePage />} />
        </Route>
        <Route path="import" element={<ImportPage />} />
        <Route path="onboarding" element={<Navigate to="/transactions" replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
