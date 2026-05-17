import { Node, mergeAttributes } from '@tiptap/core'

export type CalloutAttrs = {
  'data-block-type'?: string
  'data-callout-style'?: string
  'data-callout-type'?: string
  'data-template-id'?: string
  'data-template-key'?: string
  'data-callout-label'?: string
  'data-callout-title'?: string
  'data-callout-icon'?: string
  'data-callout-class-name'?: string
  'data-callout-source'?: string
  'data-color-background'?: string
  'data-color-border'?: string
  'data-color-text'?: string
  'data-callout-color-background'?: string
  'data-callout-color-border'?: string
  'data-callout-color-text'?: string
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    callout: {
      setCallout: (attrs?: CalloutAttrs) => ReturnType
      updateCallout: (attrs: CalloutAttrs) => ReturnType
      unsetCallout: () => ReturnType
    }
  }
}

function getDefaultColors(style?: string) {
  switch (style) {
    case 'conseil':
    case 'success':
      return { background: '#f0fdf4', border: '#10b981', text: '#065f46' }
    case 'attention':
    case 'warning':
      return { background: '#fffbeb', border: '#f59e0b', text: '#92400e' }
    case 'erreur':
    case 'error':
      return { background: '#fef2f2', border: '#ef4444', text: '#991b1b' }
    case 'succes':
      return { background: '#f5f3ff', border: '#8b5cf6', text: '#5b21b6' }
    default:
      return { background: '#eff6ff', border: '#3b82f6', text: '#1e3a8a' }
  }
}

function buildCalloutStyle(attrs: Record<string, unknown>) {
  const colors = getDefaultColors(String(attrs['data-callout-style'] || attrs['data-callout-type'] || 'info'))
  const background = String(attrs['data-callout-color-background'] || attrs['data-color-background'] || colors.background)
  const border = String(attrs['data-callout-color-border'] || attrs['data-color-border'] || colors.border)
  const text = String(attrs['data-callout-color-text'] || attrs['data-color-text'] || colors.text)
  return [
    `background:${background}`,
    `border-left:3px solid ${border}`,
    `color:${text}`,
    'padding:12px 16px',
    'border-radius:10px',
    'margin:8px 0',
  ].join(';')
}

export const CalloutExtension = Node.create({
  name: 'callout',
  group: 'block',
  content: 'block+',
  defining: true,

  addAttributes() {
    return {
      'data-block-type': { default: 'callout' },
      'data-callout-style': { default: 'info' },
      'data-callout-type': { default: 'info' },
      'data-template-id': { default: null },
      'data-template-key': { default: null },
      'data-callout-label': { default: null },
      'data-callout-title': { default: null },
      'data-callout-icon': { default: null },
      'data-callout-class-name': { default: null },
      'data-callout-source': { default: null },
      'data-color-background': { default: null },
      'data-color-border': { default: null },
      'data-color-text': { default: null },
      'data-callout-color-background': { default: null },
      'data-callout-color-border': { default: null },
      'data-callout-color-text': { default: null },
    }
  },

  parseHTML() {
    return [
      {
        tag: 'div[data-block-type="callout"]',
        contentElement: '.callout-body',
        getAttrs: (dom) => {
          const element = dom as HTMLElement
          const style = element.getAttribute('data-callout-style')
            || element.getAttribute('data-callout-type')
            || 'info'
          return {
            'data-block-type': 'callout',
            'data-callout-style': style,
            'data-callout-type': style,
            'data-template-id': element.getAttribute('data-template-id'),
            'data-template-key': element.getAttribute('data-template-key'),
            'data-callout-label': element.getAttribute('data-callout-label'),
            'data-callout-title': element.getAttribute('data-callout-title'),
            'data-callout-icon': element.getAttribute('data-callout-icon'),
            'data-callout-class-name': element.getAttribute('data-callout-class-name'),
            'data-callout-source': element.getAttribute('data-callout-source'),
            'data-color-background': element.getAttribute('data-color-background'),
            'data-color-border': element.getAttribute('data-color-border'),
            'data-color-text': element.getAttribute('data-color-text'),
            'data-callout-color-background': element.getAttribute('data-callout-color-background'),
            'data-callout-color-border': element.getAttribute('data-callout-color-border'),
            'data-callout-color-text': element.getAttribute('data-callout-color-text'),
          }
        },
      },
    ]
  },

  renderHTML({ HTMLAttributes }) {
    const title = HTMLAttributes['data-callout-title'] as string | undefined
    const className = [
      'callout',
      HTMLAttributes['data-callout-class-name'],
      `callout-${HTMLAttributes['data-callout-style'] || 'info'}`,
    ]
      .filter(Boolean)
      .join(' ')

    const attrs = mergeAttributes(HTMLAttributes, {
      'data-block-type': 'callout',
      'data-callout-style': HTMLAttributes['data-callout-style'] || 'info',
      'data-callout-type': HTMLAttributes['data-callout-style'] || 'info',
      class: className,
      style: buildCalloutStyle(HTMLAttributes),
    })

    return [
      'div',
      attrs,
      ...(title
        ? [['div', { class: 'callout-title', contenteditable: 'false', style: 'font-weight:600;margin-bottom:6px;' }, title]]
        : []),
      ['div', { class: 'callout-body' }, 0],
    ]
  },

  addCommands() {
    return {
      setCallout: (attrs: CalloutAttrs = {}) => ({ commands }) => commands.setNode(this.name, attrs),
      updateCallout: (attrs: CalloutAttrs) => ({ commands }) => commands.updateAttributes(this.name, attrs),
      unsetCallout: () => ({ commands }) => commands.setNode('paragraph'),
    }
  },
})
