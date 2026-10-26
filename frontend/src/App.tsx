import { Navigate, Outlet, Route, Routes } from 'react-router-dom'

import { AppLayout } from '@/components/layout/AppLayout'
import { Placeholder } from '@/pages/Placeholder'
import { useSession } from '@/store/session'

function RequireAuth() {
  const token = useSession((s) => s.token)
  return token ? <Outlet /> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Placeholder title="Вход" />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route index element={<Placeholder title="Главная" />} />
          <Route path="transactions" element={<Placeholder title="Операции" />} />
          <Route path="forecast" element={<Placeholder title="Прогноз" />} />
          <Route path="analytics" element={<Placeholder title="Аналитика" />} />
          <Route path="more" element={<Placeholder title="Ещё" />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
