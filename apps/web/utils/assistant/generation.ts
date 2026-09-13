export class AssistantGenerationFence {
  private generation = 0
  private controllers = new Set<AbortController>()

  get value() {
    return this.generation
  }

  isCurrent(value: number) {
    return value === this.generation
  }

  controller() {
    const item = new AbortController()
    this.controllers.add(item)
    return item
  }

  release(item: AbortController) {
    this.controllers.delete(item)
  }

  abortAll() {
    for (const item of this.controllers) item.abort()
    this.controllers.clear()
  }

  advance() {
    this.generation += 1
    this.abortAll()
    return this.generation
  }
}
