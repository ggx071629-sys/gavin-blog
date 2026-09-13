<template>
  <div class="page-artwork" :class="`page-artwork-${kind}`" :style="artPaint" aria-hidden="true">
    <div class="art-colour-field" />
    <div class="art-cutout" />
    <svg v-if="kind === 'articles'" viewBox="0 0 440 250" fill="none">
      <defs>
        <linearGradient :id="`${paintId}-paper`" x1="0" y1="0" x2="1" y2="1"><stop stop-color="var(--ee-surface)"/><stop offset="1" stop-color="var(--ee-surface-low)"/></linearGradient>
        <linearGradient :id="`${paintId}-accent`" x1="0" y1="0" x2="1" y2="1"><stop stop-color="var(--ee-primary)" stop-opacity=".3"/><stop offset="1" stop-color="var(--ee-primary)" stop-opacity=".06"/></linearGradient>
      </defs>
      <path d="M48 226h330" class="art-ground"/>
      <rect x="73" y="26" width="270" height="174" rx="10" transform="rotate(-5 73 26)" class="art-paper"/>
      <g class="art-back"><rect x="85" y="28" width="278" height="185" rx="12" transform="rotate(7 85 28)" class="art-fill" /></g>
      <g class="art-front"><path d="M51 70a10 10 0 0 1 10-10h77l17-23h62l17 23h135a10 10 0 0 1 10 10v143H51Z" class="art-paper"/><path d="M73 97h284" class="art-line"/><text x="74" y="86" class="art-label">配置 · 开发 · 排障</text><text x="74" y="135" class="art-title">工具配置与排障记录</text><path d="M75 157h160m-160 17h195m-195 17h111" class="art-line"/><rect x="292" y="148" width="65" height="40" rx="6" class="art-accent-fill"/><path d="m310 168 9 8 18-21" class="art-accent-line"/></g>
      <path d="M67 204h294m-291 5h288" class="art-fine"/><path d="M321 27v31a7 7 0 0 1-14 0V21a4 4 0 0 1 8 0v31" class="art-clip"/><rect x="155" y="43" width="61" height="6" rx="3" class="art-solid"/>
      <path d="m49 22 8 12m-30 2 14 4" class="art-accent-line"/>
    </svg>
    <svg v-else-if="kind === 'projects'" viewBox="0 0 440 250" fill="none">
      <defs>
        <linearGradient :id="`${paintId}-paper`" x1="0" y1="0" x2="1" y2="1"><stop stop-color="var(--ee-surface)"/><stop offset="1" stop-color="var(--ee-surface-low)"/></linearGradient>
        <linearGradient :id="`${paintId}-accent`" x1="0" y1="0" x2="1" y2="1"><stop stop-color="var(--ee-primary)" stop-opacity=".3"/><stop offset="1" stop-color="var(--ee-primary)" stop-opacity=".06"/></linearGradient>
      </defs>
      <ellipse cx="226" cy="213" rx="156" ry="20" class="art-shadow"/>
      <path d="m29 185 183-96 203 84-184 62Z" class="art-line"/>
      <g class="art-back"><path d="m75 126 82-43 83 34-83 45Z" class="art-fill"/><path d="m75 126 82 36v48l-82-36Zm82 36 83-45v48l-83 45Z" class="art-paper"/></g>
      <g class="art-front"><path d="m207 93 82-43 82 35-82 43Z" class="art-accent-fill"/><path d="m207 93 82 35v55l-82-35Zm82 35 82-43v55l-82 43Z" class="art-paper"/><path d="m227 116 32 13m-32 2 21 9" class="art-accent-line"/></g>
      <path d="m95 150 44 19m-44-9 44 19m168-36 45-23m-45 34 45-23m-45 34 29-15" class="art-fine"/>
      <path d="m158 89 49-26 39 16m-91 113 50-27" class="art-accent-line" stroke-dasharray="4 5"/><circle cx="247" cy="79" r="4" class="art-solid"/><circle cx="155" cy="192" r="4" class="art-solid"/>
      <path d="M64 70V42h90m189 131v37h54M178 45h37m-7-7 7 7-7 7" class="art-accent-line"/><circle cx="61" cy="71" r="5" class="art-accent-fill"/><text x="61" y="29" class="art-label">项目的实现方式</text><text x="276" y="237" class="art-label">功能与技术选择</text>
    </svg>
    <svg v-else-if="kind === 'books'" viewBox="0 0 440 250" fill="none">
      <defs>
        <linearGradient :id="`${paintId}-paper`" x1="0" y1="0" x2="1" y2="1"><stop stop-color="var(--ee-surface)"/><stop offset="1" stop-color="var(--ee-surface-low)"/></linearGradient>
        <linearGradient :id="`${paintId}-accent`" x1="0" y1="0" x2="1" y2="1"><stop stop-color="var(--ee-primary)" stop-opacity=".3"/><stop offset="1" stop-color="var(--ee-primary)" stop-opacity=".06"/></linearGradient>
      </defs>
      <ellipse cx="217" cy="210" rx="181" ry="17" class="art-shadow"/>
      <g class="art-back"><path d="m37 179 169-19 189 23v30l-189-22-169 17Z" class="art-fill"/></g>
      <g class="art-front"><path d="M36 48q97-20 176 16 94-34 190-9v139q-97-23-190 10-94-32-176-10Z" class="art-paper"/><path d="M212 66v135M62 91q62-7 118 13M62 115q62-7 118 13M62 139q62-7 91 6m-91 17 80 6" class="art-line"/><path d="M320 46v87l18-12 18 12V47" class="art-accent-fill"/><text x="239" y="155" class="art-title">摘录与心得</text><path d="M240 169q61 10 133-2" class="art-accent-line"/></g>
      <path d="M43 194q88-16 164 9m-164-3q88-16 164 9m12-3q92-28 174-4m-174 10q92-28 174-4" class="art-fine"/>
      <path d="M210 65v134" class="art-spine"/><path d="M251 88h17m-17 8h12m11-8h17m-17 8h12" class="art-accent-line"/><path d="M64 137q42-5 78 2" class="art-marker"/>
      <text x="55" y="235" class="art-label">书中摘录与个人读书笔记</text>
    </svg>
    <svg v-else-if="kind === 'archive'" viewBox="0 0 440 250" fill="none">
      <defs>
        <linearGradient :id="`${paintId}-paper`" x1="0" y1="0" x2="1" y2="1"><stop stop-color="var(--ee-surface)"/><stop offset="1" stop-color="var(--ee-surface-low)"/></linearGradient>
        <linearGradient :id="`${paintId}-accent`" x1="0" y1="0" x2="1" y2="1"><stop stop-color="var(--ee-primary)" stop-opacity=".3"/><stop offset="1" stop-color="var(--ee-primary)" stop-opacity=".06"/></linearGradient>
      </defs>
      <rect x="174" y="48" width="106" height="104" rx="9" class="art-fill"/><rect x="48" y="74" width="92" height="76" rx="8" class="art-fill"/>
      <path d="M24 166h391" class="art-line"/><g class="art-back"><rect x="41" y="67" width="92" height="76" rx="8" class="art-paper"/></g>
      <g class="art-front"><rect x="170" y="39" width="103" height="104" rx="9" class="art-paper"/><path d="M170 70h103m-79-41v19m55-19v19" class="art-accent-line"/><text x="188" y="100" class="art-title">文章</text><path d="M188 118h65" class="art-line"/></g>
      <path d="M187 131h69m-69 5h69" class="art-fine"/><path d="M33 177h371" class="art-fine" stroke-dasharray="1 9"/><circle cx="220" cy="166" r="17" class="art-halo"/>
      <rect x="309" y="86" width="92" height="57" rx="8" class="art-fill"/><path d="M54 89h64m-64 18h42m203 0h53m-53 17h35" class="art-line"/><g class="art-accent-fill"><circle cx="86" cy="166" r="6"/><circle cx="220" cy="166" r="8"/><circle cx="355" cy="166" r="6"/></g><text x="67" y="203" class="art-label">过去</text><text x="198" y="203" class="art-label">近期</text><text x="331" y="203" class="art-label">更新</text>
    </svg>
    <svg v-else-if="kind === 'search'" viewBox="0 0 440 250" fill="none">
      <defs>
        <linearGradient :id="`${paintId}-paper`" x1="0" y1="0" x2="1" y2="1"><stop stop-color="var(--ee-surface)"/><stop offset="1" stop-color="var(--ee-surface-low)"/></linearGradient>
        <linearGradient :id="`${paintId}-accent`" x1="0" y1="0" x2="1" y2="1"><stop stop-color="var(--ee-primary)" stop-opacity=".3"/><stop offset="1" stop-color="var(--ee-primary)" stop-opacity=".06"/></linearGradient>
      </defs>
      <rect x="45" y="48" width="275" height="159" rx="12" class="art-fill"/>
      <g class="art-back"><rect x="54" y="39" width="275" height="159" rx="12" class="art-paper"/><path d="M54 76h275" class="art-line"/><circle cx="73" cy="57" r="3" class="art-accent-fill"/><circle cx="85" cy="57" r="3" class="art-accent-fill"/><path d="M79 103h174m-174 23h144m-144 23h160m-160 23h95" class="art-line"/></g>
      <rect x="72" y="91" width="139" height="21" rx="4" class="art-halo"/><rect x="72" y="139" width="91" height="18" rx="4" class="art-halo"/>
      <g class="art-front"><circle cx="280" cy="125" r="66" class="art-lens"/><circle cx="280" cy="125" r="53" class="art-accent-line"/><path d="m328 173 54 49" class="art-handle"/><path d="M245 88q31-24 59-4" class="art-reflection"/><rect x="238" y="115" width="84" height="24" rx="4" class="art-accent-fill"/><text x="251" y="133" class="art-label">关键词</text></g>
    </svg>
    <svg v-else viewBox="0 0 440 250" fill="none">
      <defs>
        <linearGradient :id="`${paintId}-paper`" x1="0" y1="0" x2="1" y2="1"><stop stop-color="var(--ee-surface)"/><stop offset="1" stop-color="var(--ee-surface-low)"/></linearGradient>
        <linearGradient :id="`${paintId}-accent`" x1="0" y1="0" x2="1" y2="1"><stop stop-color="var(--ee-primary)" stop-opacity=".3"/><stop offset="1" stop-color="var(--ee-primary)" stop-opacity=".06"/></linearGradient>
      </defs>
      <path d="M82 231h278" class="art-ground"/>
      <g class="art-back"><rect x="58" y="39" width="306" height="175" rx="12" transform="rotate(-5 58 39)" class="art-fill"/></g>
      <g class="art-front"><rect x="60" y="37" width="309" height="177" rx="12" class="art-paper"/><text x="88" y="77" class="art-label">技术方向与联系方式</text><text x="85" y="137" class="art-signature">{{ name || 'Gavin' }}</text><path d="M88 154q105 25 219-5m-108 17 84-4" class="art-accent-line"/><path d="m329 63 9 9-36 36-13 4 4-13Z" class="art-accent-fill"/></g>
      <rect x="72" y="49" width="285" height="153" rx="7" class="art-fine" stroke-dasharray="2 5"/>
      <circle cx="330" cy="179" r="17" class="art-accent-fill"/><path d="m323 179 5 5 9-11" class="art-accent-line"/>
    </svg>
  </div>
</template>

<script setup lang="ts">
const paintId = useId()
const artPaint = computed(() => ({ '--art-paper-paint': `url(#${paintId}-paper)`, '--art-accent-paint': `url(#${paintId}-accent)` }))
defineProps<{ kind: 'articles' | 'projects' | 'books' | 'archive' | 'search' | 'about'; name?: string }>()
</script>

<style scoped>
.page-artwork {position:relative;isolation:isolate;min-width:0;width:100%;max-width:540px;justify-self:end;padding:36px 4px;margin-block:12px;}
.art-colour-field {position:absolute;inset:8% 8% 8% 12%;z-index:-2;background:var(--ee-primary);border-radius:18px;transform:rotate(-9deg);}
.art-cutout {position:absolute;z-index:-1;inset:0 1% 0 3%;border:1px solid color-mix(in srgb,var(--ee-primary) 40%,var(--ee-line));border-radius:22px;transform:rotate(5deg);background:repeating-linear-gradient(135deg,transparent 0 8px,color-mix(in srgb,var(--ee-primary) 15%,transparent) 8px 9px);}
.page-artwork::after {content:'';position:absolute;right:4%;top:7%;width:34px;height:34px;background:var(--ee-primary);clip-path:polygon(40% 0,60% 0,60% 40%,100% 40%,100% 60%,60% 60%,60% 100%,40% 100%,40% 60%,0 60%,0 40%,40% 40%);transform:rotate(15deg);}
.page-artwork svg {position:relative;width:100%;height:auto;overflow:visible;transform:rotate(-4deg);}
.page-artwork-projects .art-colour-field {inset:12% 10%;border-radius:0;clip-path:polygon(0 30%,65% 0,100% 25%,100% 73%,37% 100%,0 73%);transform:rotate(0);background:linear-gradient(135deg,var(--ee-primary),color-mix(in srgb,var(--ee-primary) 30%,var(--ee-surface)));}
.page-artwork-projects .art-cutout {inset:6%;border-radius:0;transform:rotate(-5deg);}
.page-artwork-projects svg {transform:rotate(0);}
.page-artwork-books .art-colour-field {inset:5% 20% 7% 17%;border-radius:50% 50% 10px 10px;transform:rotate(12deg);}
.page-artwork-books .art-cutout {inset:10% 7%;transform:rotate(-7deg);border-radius:8px;}
.page-artwork-books svg {transform:rotate(5deg);}
.page-artwork-archive .art-colour-field {inset:28% 3% 27%;border-radius:80px;transform:rotate(-14deg);}
.page-artwork-archive .art-cutout {inset:13% 7%;border-radius:50%;transform:rotate(-14deg);}
.page-artwork-search .art-colour-field {inset:4% 8% 3% 28%;border-radius:50%;transform:none;}
.page-artwork-search .art-cutout {inset:8% 4% 10% 18%;border-radius:50%;transform:rotate(9deg);border-width:2px;}
.page-artwork-about .art-colour-field {inset:13% 10%;border-radius:3px;transform:rotate(-12deg);}
.page-artwork-about svg {transform:rotate(4deg);}
.art-label {paint-order:stroke;stroke:var(--ee-surface);stroke-width:3px;stroke-linejoin:round;}
.page-artwork-books svg > .art-label,.page-artwork-projects svg > .art-label {display:none;}
.art-paper {fill:var(--art-paper-paint);stroke:var(--ee-line);stroke-width:1.4;}
.art-fill {fill:var(--ee-surface-low);stroke:var(--ee-line);stroke-width:1.4;}
.art-line {stroke:var(--ee-line);stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round;}
.art-accent-line {stroke:var(--ee-primary-strong);stroke-width:2;stroke-linecap:round;stroke-linejoin:round;}
.art-accent-fill {fill:var(--art-accent-paint);stroke:var(--ee-primary);stroke-width:1.5;}
.art-lens {fill:color-mix(in srgb,var(--ee-surface) 90%,transparent);stroke:var(--ee-primary);stroke-width:3;}
.art-label {fill:var(--ee-ink-muted);font:500 14px var(--ee-heading);}
.art-title {fill:var(--ee-ink);font:700 19px var(--ee-heading);}
.art-signature {fill:var(--ee-primary-strong);font:italic 600 43px Georgia,serif;}
.art-ground {stroke:var(--ee-line);stroke-width:6;stroke-linecap:round;opacity:.35;}
.art-shadow {fill:var(--ee-ink);opacity:.07;}
.art-fine {stroke:var(--ee-line);stroke-width:1;fill:none;stroke-linecap:round;}
.art-clip {stroke:var(--ee-primary-strong);stroke-width:3;stroke-linecap:round;}
.art-solid {fill:var(--ee-primary);}
.art-spine {stroke:var(--ee-line);stroke-width:8;opacity:.35;}
.art-marker {stroke:var(--ee-primary);stroke-width:10;opacity:.2;stroke-linecap:round;}
.art-halo {fill:var(--ee-primary);opacity:.1;}
.art-handle {stroke:var(--ee-primary-strong);stroke-width:16;stroke-linecap:round;}
.art-reflection {stroke:var(--ee-primary);stroke-width:6;stroke-linecap:round;opacity:.2;}
.art-front {filter:drop-shadow(0 8px 7px color-mix(in srgb,var(--ee-ink) 12%,transparent));}
.art-front,.art-back {transform-box:fill-box;transform-origin:center;}
@media(hover:hover) and (prefers-reduced-motion:no-preference) {
 .art-colour-field,.art-cutout {transition:transform var(--ee-motion-fast) ease-out;}
 .page-artwork:hover .art-cutout {transform:rotate(0) scale(1.04);}
 .art-front,.art-back {transition:transform var(--ee-motion-fast) ease-out;}
 .page-artwork:hover .art-front {transform:translateY(-12px) rotate(-5deg);}
 .page-artwork:hover .art-back {transform:translate(4px,5px) rotate(2deg);}
 .page-artwork-projects:hover .art-front {transform:translateY(-16px);}
 .page-artwork-search:hover .art-front {transform:translate(-15px,4px);}
}
@media(max-width:639px) {.page-artwork{max-width:340px;justify-self:center;padding:28px 8px;margin-block:12px;} .art-label{font-size:18px;} .art-title{font-size:21px;}}
</style>
