// front/composables/useModule1.ts
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { BufferPayload } from '~/utils/ArtineoClient'
import { useArtineo } from './useArtineo'; // notre composable générique

export default function useModule1() {
  const moduleId     = 1
  const { fetchConfig, getBuffer, onMessage, close } = useArtineo(moduleId)

  const cfg = ref<{ realDiameter?: number; focalLength?: number; background?: string }>({})
  const backgroundPath = ref<string>('')
  const realDiameter   = ref(6)
  const focalLength    = ref(400)

  // données IR
  const x      = ref(0)
  const y      = ref(0)
  const diamPx = ref(1)

  // brightness pivotée
  const frameHeight  = 240
  const minBrightPct = 50
  const maxBrightPct = 150

  const bright = computed(() => {
    const r = y.value / frameHeight
    const v = (1 - r) * (maxBrightPct - minBrightPct) + minBrightPct
    return Math.max(minBrightPct, Math.min(maxBrightPct, v))
  })
  const hue = computed(() => (x.value / 320) * 360)
  const sat = computed(() => (y.value / 240) * 200 + 50)
  const filterStyle = computed(
    () => `hue-rotate(${hue.value}deg) saturate(${sat.value}%) brightness(${bright.value}%)`
  )

  let intervalId: number

  onMounted(async () => {
    // 1) config
    const c = await fetchConfig()
    if (c.realDiameter)   realDiameter.value  = c.realDiameter
    if (c.focalLength)    focalLength.value   = c.focalLength
    if (c.background)     backgroundPath.value = c.background

    // 2) WS temps réel
    onMessage((msg: any) => {
      if (msg.action === 'get_buffer') {
        const buf = msg.buffer as BufferPayload
        x.value      = buf.x      ?? x.value
        y.value      = buf.y      ?? y.value
        diamPx.value = buf.diameter ?? diamPx.value
      }
    })

    // 3) requête initiale + polling
    const applyBuf = (buf: BufferPayload) => {
      x.value      = buf.x
      y.value      = buf.y
      diamPx.value = buf.diameter
    }
    applyBuf(await getBuffer())
    intervalId = window.setInterval(() => {
      getBuffer().then(applyBuf)
    }, 100)
  })

  onBeforeUnmount(() => {
    clearInterval(intervalId)
    close()
  })

  return {
    backgroundPath,
    filterStyle,
    x, y, diamPx,
  }
}
