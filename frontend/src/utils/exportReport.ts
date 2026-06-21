export function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export function printReport(title: string, subtitle: string, sections: Array<{ title: string; rows: Array<[string, string]> }>) {
  const win = window.open('', '_blank', 'width=960,height=720')
  if (!win) return
  const safe = (value: string) =>
    value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
  win.document.write(`
    <!doctype html>
    <html>
      <head>
        <title>${safe(title)}</title>
        <style>
          body { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #1d1d1f; padding: 32px; }
          h1 { font-size: 24px; margin: 0 0 6px; }
          p { color: #69615b; margin: 0 0 28px; }
          section { break-inside: avoid; margin: 0 0 22px; }
          h2 { font-size: 13px; letter-spacing: .06em; text-transform: uppercase; color: #69615b; margin: 0 0 10px; }
          table { border-collapse: collapse; width: 100%; font-size: 12px; }
          td { border-bottom: 1px solid #eee2d6; padding: 8px 0; vertical-align: top; }
          td:first-child { color: #7a716a; width: 42%; }
          @media print { body { padding: 18mm; } }
        </style>
      </head>
      <body>
        <h1>${safe(title)}</h1>
        <p>${safe(subtitle)}</p>
        ${sections.map((section) => `
          <section>
            <h2>${safe(section.title)}</h2>
            <table>
              <tbody>
                ${section.rows.map(([label, value]) => `<tr><td>${safe(label)}</td><td>${safe(value)}</td></tr>`).join('')}
              </tbody>
            </table>
          </section>
        `).join('')}
        <script>window.onload = () => { window.print() }</script>
      </body>
    </html>
  `)
  win.document.close()
}
