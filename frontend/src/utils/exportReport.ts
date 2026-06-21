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
  const win = window.open('', '_blank', 'width=1200,height=820')
  if (!win) return
  const safe = (value: string) =>
    value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
  const exportedAt = new Date().toLocaleString('fr-FR')
  win.document.write(`
    <!doctype html>
    <html>
      <head>
        <title>${safe(title)}</title>
        <style>
          @page { size: A4 landscape; margin: 12mm; }
          * { box-sizing: border-box; }
          body { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #1d1d1f; padding: 28px; background: #fbf8f4; }
          header { display: flex; justify-content: space-between; gap: 24px; align-items: flex-start; margin: 0 0 22px; border-bottom: 1px solid #eadfd3; padding-bottom: 14px; }
          h1 { font-size: 24px; line-height: 1.15; margin: 0 0 6px; }
          p { color: #69615b; margin: 0; font-size: 12px; }
          .meta { text-align: right; white-space: nowrap; }
          .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
          section { break-inside: avoid; border-radius: 14px; background: #fffdfb; border: 1px solid #eadfd3; padding: 14px; }
          h2 { font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: #69615b; margin: 0 0 10px; }
          table { border-collapse: collapse; width: 100%; font-size: 11px; }
          td { border-bottom: 1px solid #f0e7df; padding: 7px 0; vertical-align: top; }
          tr:last-child td { border-bottom: 0; }
          td:first-child { color: #7a716a; width: 38%; padding-right: 12px; }
          td:last-child { color: #1d1d1f; font-weight: 500; }
          @media print {
            body { padding: 0; background: #fff; }
            section { box-shadow: none; }
          }
        </style>
      </head>
      <body>
        <header>
          <div>
            <h1>${safe(title)}</h1>
            <p>${safe(subtitle)}</p>
          </div>
          <div class="meta">
            <p>Export Ideas Studio</p>
            <p>${safe(exportedAt)}</p>
          </div>
        </header>
        <main class="grid">
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
        </main>
        <script>window.onload = () => { window.print() }</script>
      </body>
    </html>
  `)
  win.document.close()
}
