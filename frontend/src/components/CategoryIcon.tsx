import {
  ArrowRightLeft,
  Baby,
  Bike,
  Bus,
  Car,
  Circle,
  GraduationCap,
  HeartPulse,
  Home,
  Landmark,
  Laptop,
  Lightbulb,
  Package,
  PiggyBank,
  PlusCircle,
  Repeat,
  Shirt,
  ShoppingCart,
  Ticket,
  Utensils,
  Wallet,
  Wifi,
  type LucideIcon,
} from 'lucide-react'

import type { Category } from '@/api/types'
import { cn } from '@/lib/utils'

const ICONS: Record<string, LucideIcon> = {
  'shopping-cart': ShoppingCart,
  utensils: Utensils,
  bike: Bike,
  bus: Bus,
  car: Car,
  home: Home,
  lightbulb: Lightbulb,
  wifi: Wifi,
  repeat: Repeat,
  package: Package,
  shirt: Shirt,
  'heart-pulse': HeartPulse,
  ticket: Ticket,
  'graduation-cap': GraduationCap,
  baby: Baby,
  landmark: Landmark,
  'arrow-right-left': ArrowRightLeft,
  circle: Circle,
  wallet: Wallet,
  laptop: Laptop,
  'plus-circle': PlusCircle,
  'piggy-bank': PiggyBank,
}

export function CategoryIcon({ category, size = 'md' }: { category?: Category; size?: 'sm' | 'md' }) {
  const Icon = ICONS[category?.icon ?? 'circle'] ?? Circle
  const color = category?.color ?? '#94a3b8'
  return (
    <span
      className={cn('flex shrink-0 items-center justify-center rounded-full', size === 'md' ? 'h-10 w-10' : 'h-8 w-8')}
      style={{ backgroundColor: `${color}22`, color }}
    >
      <Icon className={size === 'md' ? 'h-5 w-5' : 'h-4 w-4'} />
    </span>
  )
}
