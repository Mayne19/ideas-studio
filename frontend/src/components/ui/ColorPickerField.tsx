import { DEFAULT_ACCENT_COLOR, RADIX_COLOR_SWATCHES, isValidHexColor, normalizeHexColor } from '@/lib/colors'

export default function ColorPickerField({
  label = 'Couleur',
  value,
  onChange,
  paletteLabel = 'Palette Radix',
}: {
  label?: string
  value: string
  onChange: (value: string) => void
  paletteLabel?: string
}) {
  const rawValue = String(value ?? '')
  const selected = normalizeHexColor(value, DEFAULT_ACCENT_COLOR)
  const isManualValid = isValidHexColor(value)

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <label className="text-[13px] font-medium text-primary">{label}</label>
        <div className="flex items-center gap-2 rounded-[10px] border border-border bg-surface-soft px-2 py-1">
          <span
            className="h-4 w-4 rounded-full border border-black/10"
            style={{ backgroundColor: selected }}
            aria-hidden="true"
          />
          <span className="font-mono text-[11px] uppercase text-secondary">{selected}</span>
          <input
            type="color"
            value={selected}
            onChange={(event) => onChange(event.target.value)}
            className="h-6 w-7 cursor-pointer rounded border-0 bg-transparent p-0"
            aria-label="Choisir une couleur personnalisée"
          />
        </div>
      </div>

      <div>
        <p className="mb-2 text-[11px] font-medium uppercase tracking-[0.04em] text-tertiary">{paletteLabel}</p>
        <div className="grid grid-cols-6 gap-2">
          {RADIX_COLOR_SWATCHES.map((color) => (
            <button
              key={color.value}
              type="button"
              onClick={() => onChange(color.value)}
              className={`flex h-8 items-center justify-center rounded-[10px] border bg-white transition-all ${
                selected.toLowerCase() === color.value.toLowerCase()
                  ? 'border-primary ring-2 ring-accent/20'
                  : 'border-black/5 hover:scale-[1.03]'
              }`}
              title={color.name}
              aria-label={`Choisir ${color.name}`}
            >
              <span
                className="h-4 w-4 rounded-full border border-black/10"
                style={{ backgroundColor: color.value }}
                aria-hidden="true"
              />
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-[12px] font-medium text-secondary">Code hexadécimal</label>
        <input
          value={rawValue}
          onChange={(event) => onChange(event.target.value)}
          placeholder="#2563eb"
          className={`h-10 rounded-[12px] border bg-white px-3 font-mono text-[13px] uppercase outline-none transition-colors ${
            isManualValid || rawValue.trim() === ''
              ? 'border-border text-primary focus:border-accent/60 focus:ring-1 focus:ring-accent/25'
              : 'border-danger/40 text-danger focus:border-danger/50 focus:ring-1 focus:ring-danger/20'
          }`}
          spellCheck={false}
        />
        {!isManualValid && rawValue.trim() !== '' && (
          <p className="text-[11px] text-danger">
            Utilisez un code couleur hexadécimal valide, par exemple #2563eb.
          </p>
        )}
      </div>
    </div>
  )
}
