import Image from '@tiptap/extension-image'

function normalizeWidth(value: unknown) {
  if (value === null || value === undefined || value === '') return null
  const numeric = typeof value === 'number' ? value : Number.parseInt(String(value), 10)
  if (!Number.isFinite(numeric)) return null
  return Math.max(20, Math.min(100, Math.round(numeric)))
}

export const EditorImageExtension = Image.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      alt: {
        default: null,
        parseHTML: (element) => element.getAttribute('alt'),
      },
      title: {
        default: null,
        parseHTML: (element) => element.getAttribute('title'),
      },
      width: {
        default: null,
        parseHTML: (element) => {
          const fromData = element.getAttribute('data-image-width')
          const fromStyle = element instanceof HTMLElement ? element.style.width : null
          return normalizeWidth(fromData || fromStyle?.replace('%', ''))
        },
        renderHTML: (attributes) => {
          const width = normalizeWidth(attributes['width'])
          if (!width) return {}
          return {
            'data-image-width': String(width),
            style: `width:${width}%;`,
          }
        },
      },
      'data-media-id': {
        default: null,
        parseHTML: (element) => element.getAttribute('data-media-id'),
      },
    }
  },
})
