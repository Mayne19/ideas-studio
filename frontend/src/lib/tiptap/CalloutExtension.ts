import { Node, mergeAttributes } from '@tiptap/core'

export type CalloutType = 'info' | 'conseil' | 'attention' | 'erreur' | 'succes'

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    callout: {
      setCallout: (type: CalloutType) => ReturnType
      toggleCallout: (type: CalloutType) => ReturnType
      unsetCallout: () => ReturnType
    }
  }
}

export const CalloutExtension = Node.create({
  name: 'callout',

  group: 'block',

  content: 'inline*',

  defining: true,

  addAttributes() {
    return {
      'data-block-type': { default: 'callout' },
      'data-callout-type': { default: 'info' },
    }
  },

  parseHTML() {
    return [
      {
        tag: 'div[data-block-type="callout"]',
        getAttrs: (dom) => ({
          'data-block-type': 'callout',
          'data-callout-type': (dom as HTMLElement).getAttribute('data-callout-type') || 'info',
        }),
      },
    ]
  },

  renderHTML({ HTMLAttributes }) {
    const type = (HTMLAttributes['data-callout-type'] as string) || 'info'
    return [
      'div',
      mergeAttributes(HTMLAttributes, {
        'data-block-type': 'callout',
        'data-callout-type': type,
        class: `callout callout-${type}`,
        style: getCalloutStyle(type),
      }),
      0,
    ]
  },

  addCommands() {
    return {
      setCallout: (type: CalloutType) => ({ commands }) => {
        return commands.setNode(this.name, { 'data-callout-type': type })
      },
      toggleCallout: (type: CalloutType) => ({ commands }) => {
        return commands.toggleNode(this.name, 'paragraph', { 'data-callout-type': type })
      },
      unsetCallout: () => ({ commands }) => {
        return commands.setNode('paragraph')
      },
    }
  },
})

function getCalloutStyle(type: string): string {
  const styles: Record<string, string> = {
    info: 'border-left: 3px solid #3b82f6; background: #eff6ff; padding: 12px 16px; border-radius: 8px; margin: 8px 0;',
    conseil: 'border-left: 3px solid #10b981; background: #f0fdf4; padding: 12px 16px; border-radius: 8px; margin: 8px 0;',
    attention: 'border-left: 3px solid #f59e0b; background: #fffbeb; padding: 12px 16px; border-radius: 8px; margin: 8px 0;',
    erreur: 'border-left: 3px solid #ef4444; background: #fef2f2; padding: 12px 16px; border-radius: 8px; margin: 8px 0;',
    succes: 'border-left: 3px solid #8b5cf6; background: #f5f3ff; padding: 12px 16px; border-radius: 8px; margin: 8px 0;',
  }
  return styles[type] || styles.info
}

export { getCalloutStyle }
