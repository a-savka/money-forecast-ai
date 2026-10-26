import type { InputHTMLAttributes, LabelHTMLAttributes, SelectHTMLAttributes } from 'react'

import { cn } from '@/lib/utils'

const field =
  'h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-base outline-none ' +
  'focus:border-brand-500 focus:ring-2 focus:ring-brand-100'

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(field, className)} {...props} />
}

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn(field, 'appearance-none', className)} {...props} />
}

export function Label({ className, ...props }: LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={cn('mb-1 block text-sm font-medium text-slate-600', className)} {...props} />
}
