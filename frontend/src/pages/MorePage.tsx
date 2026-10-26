import { LogOut } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { PageHeader } from '@/components/layout/AppLayout'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useSession } from '@/store/session'

export function MorePage() {
  const { user, logout } = useSession()
  const navigate = useNavigate()
  return (
    <>
      <PageHeader title="Ещё" />
      <Card className="mb-4">
        <p className="font-semibold">{user?.name}</p>
        <p className="text-sm text-slate-500">{user?.email}</p>
      </Card>
      <Button
        variant="secondary"
        className="w-full"
        onClick={() => {
          logout()
          navigate('/login')
        }}
      >
        <LogOut className="h-4 w-4" /> Выйти
      </Button>
    </>
  )
}
