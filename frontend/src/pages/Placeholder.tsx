import { Construction } from 'lucide-react'

import { PageHeader } from '@/components/layout/AppLayout'
import { EmptyState } from '@/components/ui/feedback'

export function Placeholder({ title }: { title: string }) {
  return (
    <>
      <PageHeader title={title} />
      <EmptyState icon={<Construction className="h-8 w-8" />} title="Раздел в разработке" />
    </>
  )
}
