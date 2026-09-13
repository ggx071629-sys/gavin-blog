import type { ProfilePublic } from '~/types/api'

const fetchPublicProfile = () => apiFetch<ProfilePublic>('/profile')

export const usePublicProfile = () => useAsyncData(
  'public-profile',
  fetchPublicProfile,
)
