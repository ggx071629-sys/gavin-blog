<template>
  <div class="notebook-hero">
    <div class="notebook-intro">
      <p class="notebook-kicker">一个记录开发与阅读的个人博客</p>
      <h1 id="home-heading">开发笔记、项目记录，<br>还有<span>读书心得</span>。</h1>
      <div class="notebook-actions">
        <NuxtLink to="/articles" class="blueprint-button blueprint-button-primary">浏览文章 <NavigationArrow /></NuxtLink>
        <NuxtLink to="/projects" class="notebook-project-link">查看项目 <NavigationArrow direction="up-right" /></NuxtLink>
      </div>
    </div>
    <div ref="scene" class="notebook-scene" @pointermove="moveNotebook" @pointerleave="resetNotebook">
      <div class="notebook-loose-sheet" aria-hidden="true" />
      <div class="notebook-book" aria-hidden="true">
        <div class="notebook-page notebook-page-left">
          <span class="notebook-page-label">开发手记</span>
          <strong>开发中遇到的问题</strong>
          <div class="notebook-code"><span>const note = {</span><span>&nbsp; topic: <em>'开发'</em>,</span><span>&nbsp; type: <em>'排障笔记'</em></span><span>}</span></div>
          <svg class="notebook-sketch" viewBox="0 0 210 76" fill="none"><g stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="18" width="52" height="34" rx="7"/><path d="M58 35h27m-6-5 6 5-6 5"/><rect x="87" y="18" width="52" height="34" rx="7"/><path d="M140 35h20m-6-5 6 5-6 5"/><circle cx="182" cy="35" r="20"/><path d="m173 35 6 6 12-13M17 64q70 13 139-1"/></g></svg>
        </div>
        <div class="notebook-page notebook-page-right">
          <span class="notebook-page-label">笔记里有什么</span>
          <strong>记录解决问题的过程</strong>
          <div class="notebook-checks"><span>问题和使用场景</span><span>尝试过的解决方法</span><span>结果与注意事项</span></div>
          <div class="notebook-margin-note">文章、项目与读书笔记<br>按栏目查看。</div>
        </div>
      </div>
      <nav class="notebook-bookmarks" aria-label="翻阅笔记栏目">
        <NuxtLink to="/articles">开发笔记 <NavigationArrow /></NuxtLink>
        <NuxtLink to="/projects">项目实践 <NavigationArrow /></NuxtLink>
        <NuxtLink to="/books">阅读随记 <NavigationArrow /></NuxtLink>
      </nav>
      <span class="notebook-caption" aria-hidden="true">开发实践 · 项目记录 · 阅读心得</span>
    </div>
  </div>
</template>

<script setup lang="ts">
const scene = ref<HTMLElement | null>(null)
let frame = 0
let motionQuery: MediaQueryList | undefined
let pointerX = 0
let pointerY = 0
function resetNotebook() {
  cancelAnimationFrame(frame)
  frame = 0
  scene.value?.style.removeProperty('--tilt-x')
  scene.value?.style.removeProperty('--tilt-y')
  scene.value?.style.removeProperty('--drift-x')
  scene.value?.style.removeProperty('--drift-y')
}
function moveNotebook(event: PointerEvent) {
  if (event.pointerType !== 'mouse' || !motionQuery?.matches) return
  pointerX = event.clientX
  pointerY = event.clientY
  if (frame) return
  frame = requestAnimationFrame(() => {
    frame = 0
    if (!scene.value) return
    const box = scene.value.getBoundingClientRect()
    const x = Math.max(-1, Math.min(1, (pointerX - box.left) / box.width * 2 - 1))
    const y = Math.max(-1, Math.min(1, (pointerY - box.top) / box.height * 2 - 1))
    scene.value.style.setProperty('--tilt-x', `${-y * 9}deg`)
    scene.value.style.setProperty('--tilt-y', `${x * 12}deg`)
    scene.value.style.setProperty('--drift-x', `${x * 9}px`)
    scene.value.style.setProperty('--drift-y', `${y * 7}px`)
  })
}
onMounted(() => {
  motionQuery = window.matchMedia('(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)')
  motionQuery.addEventListener('change', resetNotebook)
})
onBeforeUnmount(() => {
  cancelAnimationFrame(frame)
  motionQuery?.removeEventListener('change', resetNotebook)
})
</script>

<style scoped>
.notebook-hero {display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);align-items:center;gap:36px;margin:12px 0 44px;}
.notebook-kicker {font-size:14px;color:var(--ee-ink-muted);margin:0 0 16px;}
.notebook-intro h1 {font:700 clamp(28px,2.7vw,42px)/1.4 var(--ee-heading);letter-spacing:-.035em;color:var(--ee-ink);}
.notebook-intro h1 span {color:var(--ee-primary-strong);}
.notebook-actions {display:flex;align-items:center;flex-wrap:wrap;gap:12px 20px;margin-top:28px;}
.notebook-project-link {display:inline-flex;align-items:center;gap:6px;min-height:44px;font-size:14px;font-weight:600;color:var(--ee-ink-muted);}
.notebook-project-link:hover {color:var(--ee-primary-strong);}
.notebook-scene {position:relative;min-width:0;height:350px;isolation:isolate;}
.notebook-loose-sheet {position:absolute;inset:35px 28px 37px 24px;background:var(--ee-surface-low);border:1px solid var(--ee-line);border-radius:8px;transform:rotate(-7deg);}
.notebook-book {position:absolute;inset:24px 44px 40px 4px;display:grid;grid-template-columns:1fr 1fr;transform:rotate(-3deg);border:1px solid var(--ee-line);border-radius:8px 16px 16px 8px;background:var(--ee-surface);box-shadow:0 16px 30px color-mix(in srgb,var(--ee-ink) 8%,transparent);}
.notebook-page {min-width:0;padding:22px 18px;background:repeating-linear-gradient(transparent 0 27px,color-mix(in srgb,var(--ee-line) 25%,transparent) 27px 28px);}
.notebook-page-left {border-right:1px solid var(--ee-line);box-shadow:inset -10px 0 16px -16px var(--ee-ink);}
.notebook-page-right {box-shadow:inset 10px 0 16px -16px var(--ee-ink);}
.notebook-page-label {display:block;font-size:14px;line-height:1.5;color:var(--ee-ink-muted);margin-bottom:14px;}
.notebook-page strong {font:700 18px/1.6 var(--ee-heading);color:var(--ee-ink);}
.notebook-code {display:grid;margin-top:16px;font:400 14px/1.7 var(--ee-mono);color:var(--ee-primary-strong);white-space:nowrap;}
.notebook-code em {font-style:normal;color:var(--ee-ink-muted);}
.notebook-sketch {width:100%;height:65px;color:var(--ee-primary);margin-top:5px;}
.notebook-checks {display:grid;gap:13px;font-size:14px;color:var(--ee-ink-muted);margin-top:20px;}
.notebook-checks span::before {content:'✓';margin-right:8px;color:var(--ee-primary-strong);}
.notebook-margin-note {margin-top:20px;margin-left:8px;border-left:2px solid var(--ee-primary);padding-left:10px;transform:rotate(3deg);font-size:14px;line-height:1.6;color:var(--ee-primary-strong);}
.notebook-bookmarks {position:absolute;right:0;top:60px;display:grid;gap:14px;}
.notebook-bookmarks a {display:flex;align-items:center;gap:12px;min-height:44px;padding:8px 12px;border:1px solid var(--ee-line);border-radius:4px 9px 9px 4px;background:var(--ee-surface-low);color:var(--ee-ink);font-size:14px;font-weight:600;box-shadow:0 3px 8px color-mix(in srgb,var(--ee-ink) 5%,transparent);}
.notebook-bookmarks a:first-child {background:var(--ee-primary);border-color:var(--ee-primary);color:var(--ee-primary-contrast);}
.notebook-caption {position:absolute;bottom:4px;left:25%;font-size:14px;letter-spacing:.04em;color:var(--ee-ink-muted);}
/* Bookmark feedback is also available to keyboard and touch users. */
.notebook-scene:has(.notebook-bookmarks a:nth-child(1):is(:hover,:focus-visible)) .notebook-page-left,
.notebook-scene:has(.notebook-bookmarks a:nth-child(2):is(:hover,:focus-visible)) .notebook-sketch,
.notebook-scene:has(.notebook-bookmarks a:nth-child(3):is(:hover,:focus-visible)) .notebook-page-right {background-color:color-mix(in srgb,var(--ee-primary) 8%,transparent);}
.notebook-bookmarks a:is(:hover,:focus-visible) {background:var(--ee-primary);color:var(--ee-primary-contrast);border-color:var(--ee-primary);}
.notebook-bookmarks a:active {filter:brightness(.9);}
@media(hover:hover) and (prefers-reduced-motion:no-preference) {
  .notebook-scene {perspective:1000px;}
  .notebook-book {transition:transform var(--ee-motion-fast) ease-out,box-shadow var(--ee-motion-fast) ease-out;transform:translate3d(var(--drift-x,0px),var(--drift-y,0px),0) rotateX(var(--tilt-x,0deg)) rotateY(var(--tilt-y,0deg)) rotate(-3deg);}
  .notebook-scene:hover .notebook-book {box-shadow:0 26px 44px color-mix(in srgb,var(--ee-ink) 16%,transparent);}
  .notebook-loose-sheet {transition:transform var(--ee-motion-fast) ease-out;}
  .notebook-scene:hover .notebook-loose-sheet {transform:translate(-8px,10px) rotate(-10deg);}
  .notebook-bookmarks a {transition:transform var(--ee-motion-fast) ease-out,background-color var(--ee-motion-fast) ease-out;}
  .notebook-bookmarks a:hover {transform:translateX(12px) rotate(2deg) scale(1.04);}
  .notebook-bookmarks a:active {transform:translateX(8px) scale(.97);}
}
@media(hover:none) and (prefers-reduced-motion:no-preference) {.notebook-bookmarks a:active {transform:scale(.96);}}
@media(max-width:1100px) {.notebook-hero{grid-template-columns:minmax(0,1fr);gap:24px;}.notebook-intro{display:grid;grid-template-columns:1fr auto;align-items:center;gap:0 20px;}.notebook-kicker{grid-column:1/-1;}.notebook-actions{margin-top:0;}.notebook-scene{width:min(650px,100%);justify-self:center;}.notebook-intro h1{font-size:32px;}}
@media(max-width:639px) {.notebook-hero{margin-bottom:32px;}.notebook-intro{display:block;}.notebook-intro h1{font-size:28px;}.notebook-actions{margin-top:20px;gap:10px 16px;}.notebook-scene{height:350px;}.notebook-book{inset:16px 12px 100px 4px;}.notebook-loose-sheet{inset:28px 6px 95px 14px;}.notebook-page{padding:18px 12px;}.notebook-page strong{font-size:16px;}.notebook-code{font-size:14px;}.notebook-page-right{display:none;}.notebook-book{grid-template-columns:1fr;}.notebook-page-left{border-right:0;padding-right:18px;}.notebook-bookmarks{top:auto;bottom:36px;left:0;right:0;display:flex;justify-content:space-between;gap:6px;}.notebook-bookmarks a{padding:6px 8px;gap:0;border-radius:6px;}.notebook-bookmarks :deep(svg){display:none;}.notebook-caption{left:8px;bottom:0;}.notebook-sketch{height:58px;}.notebook-page-label{margin-bottom:8px;}}
</style>
