import type { Category } from '@/types'

export type MetaFields = {
  title: string
  slug: string
  excerpt: string
  meta_title: string
  meta_description: string
  keyword: string
  category_id: string
}

function MetaField({
  label,
  name,
  value,
  onChange,
  multiline,
  hint,
}: {
  label: string
  name: keyof MetaFields
  value: string
  onChange: (name: keyof MetaFields, value: string) => void
  multiline?: boolean
  hint?: string
}) {
  const base = "w-full rounded-[8px] border border-border bg-surface px-2.5 py-1.5 text-[12px] text-primary placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent/50 focus:border-accent/60 transition-colors"
  return (
    <div>
      <label className="block text-[11px] font-medium text-secondary mb-1">{label}</label>
      {multiline ? (
        <textarea
          rows={3}
          value={value}
          onChange={(e) => onChange(name, e.target.value)}
          className={`${base} resize-none`}
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(name, e.target.value)}
          className={base}
        />
      )}
      {hint && <p className="mt-0.5 text-[10px] text-tertiary">{hint}</p>}
    </div>
  )
}

export default function MetaPanel({
  fields,
  onChange,
  categories = [],
}: {
  fields: MetaFields
  onChange: (name: keyof MetaFields, value: string) => void
  categories?: Category[]
}) {
  const selectBase = "w-full rounded-[8px] border border-border bg-surface px-2.5 py-1.5 text-[12px] text-primary focus:outline-none focus:ring-1 focus:ring-accent/50 focus:border-accent/60 transition-colors"

  return (
    <div className="flex flex-col gap-3">
      <MetaField label="Titre" name="title" value={fields.title} onChange={onChange} />
      <MetaField label="Slug" name="slug" value={fields.slug} onChange={onChange} hint="URL de l'article" />
      <MetaField label="Mot-clé" name="keyword" value={fields.keyword} onChange={onChange} />
      {categories.length > 0 && (
        <div>
          <label className="block text-[11px] font-medium text-secondary mb-1">Catégorie</label>
          <select
            value={fields.category_id}
            onChange={(e) => onChange('category_id', e.target.value)}
            className={selectBase}
          >
            <option value="">— Aucune catégorie —</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.name}
              </option>
            ))}
          </select>
        </div>
      )}
      <MetaField label="Extrait" name="excerpt" value={fields.excerpt} onChange={onChange} multiline />
      <MetaField label="Meta title" name="meta_title" value={fields.meta_title} onChange={onChange} />
      <MetaField label="Meta description" name="meta_description" value={fields.meta_description} onChange={onChange} multiline />
    </div>
  )
}
