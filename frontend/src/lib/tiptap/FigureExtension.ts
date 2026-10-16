import { Node, mergeAttributes } from '@tiptap/core'

// Les images sourcées automatiquement sont insérées dans un <figure> avec un
// <figcaption> de crédit (attribution Unsplash obligatoire). Sans ces nœuds,
// TipTap aplatirait la structure à la première sauvegarde depuis l'éditeur.

export const FigureCaptionExtension = Node.create({
  name: 'figcaption',
  content: 'inline*',
  marks: '_',
  defining: true,
  parseHTML() {
    return [{ tag: 'figcaption' }]
  },
  renderHTML({ HTMLAttributes }) {
    return ['figcaption', mergeAttributes(HTMLAttributes), 0]
  },
})

export const FigureExtension = Node.create({
  name: 'figure',
  group: 'block',
  content: 'image figcaption?',
  defining: true,
  isolating: true,
  draggable: true,
  parseHTML() {
    return [{ tag: 'figure' }]
  },
  renderHTML({ HTMLAttributes }) {
    return ['figure', mergeAttributes(HTMLAttributes), 0]
  },
})
