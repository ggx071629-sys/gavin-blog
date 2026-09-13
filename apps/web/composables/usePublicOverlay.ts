export type PublicOverlayOwner = 'nav' | 'assistant' | null

export function usePublicOverlay() {
  const owner = useState<PublicOverlayOwner>('public-overlay-owner', () => null)
  const restoreFocus = useState('public-overlay-restore-focus', () => true)

  const claim = (next: Exclude<PublicOverlayOwner, null>, options?: { restoreFocus?: boolean }) => {
    restoreFocus.value = options?.restoreFocus ?? false
    owner.value = next
  }

  const release = (who: Exclude<PublicOverlayOwner, null>, options?: { restoreFocus?: boolean }) => {
    if (owner.value !== who) return
    restoreFocus.value = options?.restoreFocus ?? true
    owner.value = null
  }

  return { owner, restoreFocus, claim, release }
}
