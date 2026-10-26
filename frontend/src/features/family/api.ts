import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, unwrap } from '@/api/client'
import type { FamilyInfo } from '@/api/types'

const key = ['family']

export function useFamily() {
  return useQuery({ queryKey: key, queryFn: () => unwrap<FamilyInfo | null>(api.GET('/mock/family')) })
}

function useFamilyMutation<T>(fn: (arg: T) => Promise<FamilyInfo | null>) {
  const qc = useQueryClient()
  return useMutation({ mutationFn: fn, onSuccess: (data) => qc.setQueryData(key, data) })
}

export const useCreateFamily = () =>
  useFamilyMutation((name: string) => unwrap<FamilyInfo | null>(api.POST('/mock/family', { body: { name } })))
export const useJoinFamily = () =>
  useFamilyMutation((code: string) => unwrap<FamilyInfo | null>(api.POST('/mock/family/join', { body: { code } })))
export const useAddDemoMember = () =>
  useFamilyMutation(() => unwrap<FamilyInfo | null>(api.POST('/mock/family/demo-member')))
export const useLeaveFamily = () =>
  useFamilyMutation(() => unwrap<FamilyInfo | null>(api.POST('/mock/family/leave')))
