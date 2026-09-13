import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

/** Loaded only after the enabled discovery component mounts in the browser. */
export function createOrbMotion(root: HTMLElement) {
  gsap.registerPlugin(ScrollTrigger)
  let media: gsap.MatchMedia | undefined
  let loops: gsap.core.Animation[] = []
  let scroll: gsap.core.Tween | undefined
  let engaged = false
  let destroyed = false
  let refreshTimer: ReturnType<typeof setTimeout> | undefined

  const refresh = () => {
    clearTimeout(refreshTimer)
    refreshTimer = setTimeout(() => {
      if (!destroyed) scroll?.scrollTrigger?.refresh()
    }, 100)
  }
  const setEngaged = (value: boolean) => {
    engaged = value
    loops.forEach(animation => animation.paused(value))
  }
  const setActive = (value: boolean) => {
    if (destroyed) return
    if (!value) {
      media?.revert()
      media = undefined
      return
    }
    if (media) return
    media = gsap.matchMedia()
    media.add({
      compact: '(max-width: 639px), (pointer: coarse)',
      desktop: '(min-width: 640px)',
      reduce: '(prefers-reduced-motion: reduce)',
    }, context => {
      if (context.conditions?.reduce) return
      const compact = context.conditions?.compact
      const idle = gsap.timeline({ repeat: -1, defaults: { ease: 'sine.inOut' } })
        .addLabel('rise')
        .to('.assistant-orb-float', { y: compact ? -2 : -4, rotation: -5, duration: 2.6 }, 'rise')
        .to('.assistant-orb-glow', { scale: 1.12, opacity: 0.65, duration: 2.6 }, 'rise')
        .addLabel('settle')
        .to('.assistant-orb-float', { y: 0, rotation: 0, duration: 2.6 }, 'settle')
        .to('.assistant-orb-glow', { scale: 1, opacity: 0.35, duration: 2.6 }, 'settle')
      const orbit = gsap.to('.assistant-orb-orbit', { rotation: 360, duration: compact ? 20 : 14, ease: 'none', repeat: -1 })
      const inner = gsap.to('.assistant-orb-orbit-inner', { rotation: -360, duration: 22, ease: 'none', repeat: -1 })
      loops = [idle, orbit, inner]
      // The fixed hit target never moves with scroll. Only this decorative ring does.
      scroll = gsap.to('.assistant-orb-scroll', {
        rotation: 210, ease: 'none',
        scrollTrigger: { start: 0, end: () => Math.max(1, ScrollTrigger.maxScroll(window)), scrub: 0.7, invalidateOnRefresh: true },
      })
      setEngaged(engaged)
      return () => { loops = []; scroll = undefined }
    }, root)
  }
  const layout = new ResizeObserver(refresh)
  layout.observe(document.body)
  void document.fonts.ready.then(() => { if (!destroyed) refresh() })
  return {
    setActive, setEngaged, refresh,
    destroy() {
      destroyed = true
      clearTimeout(refreshTimer)
      layout.disconnect()
      media?.revert()
      media = undefined
    },
  }
}
