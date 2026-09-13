import '~/assets/css/public-card-focus.css'

/** Route scope also covers teleported cards and the standalone error page. */
export const usePublicCardFocus = () => {
  const route = useRoute()
  const enabled = computed(() => !/^\/admin(?:\/|$)/i.test(route.path))
  useHead(() => ({
    htmlAttrs: {
      'data-public-card-focus': enabled.value ? 'true' : null,
    },
  }))

  let glow: HTMLElement | null = null
  let frame = 0
  let pointerMedia: MediaQueryList | undefined
  const fading = new Map<HTMLElement, ReturnType<typeof setTimeout>>()
  const removeGlow = (card: HTMLElement) => {
    card.removeAttribute('data-focus-glow')
    card.style.removeProperty('--focus-pointer-x')
    card.style.removeProperty('--focus-pointer-y')
    clearTimeout(fading.get(card))
    fading.delete(card)
  }
  const leaveGlow = () => {
    cancelAnimationFrame(frame)
    frame = 0
    if (!glow) return
    const card = glow
    glow = null
    // Keep the last light position while the existing highlight fades out.
    fading.set(card, setTimeout(() => removeGlow(card), 180))
  }
  const clearGlow = () => {
    cancelAnimationFrame(frame)
    frame = 0
    if (glow) removeGlow(glow)
    glow = null
    for (const card of fading.keys()) removeGlow(card)
  }
  const moveGlow = (event: PointerEvent) => {
    if (!enabled.value || event.pointerType !== 'mouse' || !pointerMedia?.matches || !(event.target instanceof Element)) return
    const card = event.target.closest<HTMLElement>('[data-focus-card]')
    // The atlas already owns a branch-wide glow, including its linked cards.
    if (!card || card.closest('.knowledge-path')) {
      leaveGlow()
      return
    }
    if (glow !== card) {
      leaveGlow()
      clearTimeout(fading.get(card))
      fading.delete(card)
      glow = card
    }
    cancelAnimationFrame(frame)
    frame = requestAnimationFrame(() => {
      frame = 0
      if (!card.isConnected) return clearGlow()
      const rect = card.getBoundingClientRect()
      card.style.setProperty('--focus-pointer-x', `${event.clientX - rect.left - card.clientLeft}px`)
      card.style.setProperty('--focus-pointer-y', `${event.clientY - rect.top - card.clientTop}px`)
      card.setAttribute('data-focus-glow', '')
    })
  }
  const exitGlow = (event: PointerEvent) => {
    if (glow && (!(event.relatedTarget instanceof Element) || event.relatedTarget.closest('[data-focus-card]') !== glow)) leaveGlow()
  }

  // Touch :active may be delayed until release while the browser resolves a pan.
  // Observe the gesture without capturing it or preventing native scrolling.
  let pressed: HTMLElement | null = null
  const clearPress = () => {
    pressed?.removeAttribute('data-focus-pressed')
    pressed = null
  }
  const press = (event: PointerEvent) => {
    clearPress()
    if (!enabled.value || !event.isPrimary || event.pointerType === 'mouse' || !(event.target instanceof Element)) return
    clearGlow()
    pressed = event.target.closest<HTMLElement>('[data-focus-card]')
    pressed?.setAttribute('data-focus-pressed', '')
  }
  const clearFeedback = () => { clearPress(); clearGlow() }
  watch(() => route.path, () => { if (import.meta.client) clearFeedback() })
  onMounted(() => {
    pointerMedia = window.matchMedia('(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)')
    pointerMedia.addEventListener('change', clearGlow)
    document.addEventListener('pointerover', moveGlow, { passive: true })
    document.addEventListener('pointermove', moveGlow, { passive: true })
    document.addEventListener('pointerout', exitGlow, { passive: true })
    document.addEventListener('keydown', clearGlow)
    document.addEventListener('pointerdown', press, { passive: true })
    document.addEventListener('pointerup', clearPress, { passive: true })
    document.addEventListener('pointercancel', clearFeedback, { passive: true })
    window.addEventListener('blur', clearFeedback)
    window.addEventListener('scroll', clearFeedback, true)
  })
  onBeforeUnmount(() => {
    clearFeedback()
    pointerMedia?.removeEventListener('change', clearGlow)
    document.removeEventListener('pointerover', moveGlow)
    document.removeEventListener('pointermove', moveGlow)
    document.removeEventListener('pointerout', exitGlow)
    document.removeEventListener('keydown', clearGlow)
    document.removeEventListener('pointerdown', press)
    document.removeEventListener('pointerup', clearPress)
    document.removeEventListener('pointercancel', clearFeedback)
    window.removeEventListener('blur', clearFeedback)
    window.removeEventListener('scroll', clearFeedback, true)
  })
}
