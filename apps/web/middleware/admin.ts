export default defineNuxtRouteMiddleware(async (to) => {
  try {
    await apiFetch('/auth/session')
  }
  catch (error: unknown) {
    if (apiErrorStatus(error) === 401) {
      return navigateTo({
        path: '/admin/login',
        query: { returnTo: to.fullPath },
      })
    }
    throw createError(pageFailureFromApi(error, '管理会话不可用'))
  }
})
