import jsQR from 'jsqr'

const MAX_SIDE = 1600

/** Распознаёт QR-код на фотографии. Возвращает строку или null. */
export async function decodeQrFromFile(file: Blob): Promise<string | null> {
  const bitmap = await createImageBitmap(file)
  // Пробуем несколько масштабов: мелкий QR на большом фото лучше читается без сильного уменьшения
  for (const target of [MAX_SIDE, 1000, 600]) {
    const scale = Math.min(1, target / Math.max(bitmap.width, bitmap.height))
    const w = Math.round(bitmap.width * scale)
    const h = Math.round(bitmap.height * scale)
    const canvas = document.createElement('canvas')
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d', { willReadFrequently: true })
    if (!ctx) return null
    ctx.drawImage(bitmap, 0, 0, w, h)
    const { data } = ctx.getImageData(0, 0, w, h)
    const code = jsQR(data, w, h, { inversionAttempts: 'attemptBoth' })
    if (code?.data) return code.data
  }
  return null
}
