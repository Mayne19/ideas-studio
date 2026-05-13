import { Bell, Info } from 'lucide-react'

export default function NotificationsPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <h1 className="text-[20px] font-semibold text-primary tracking-tight">Notifications</h1>
        <p className="mt-0.5 text-[13px] text-secondary">
          Restez informé des événements importants de votre projet.
        </p>
      </div>

      {/* Coming soon banner */}
      <div className="mb-6 flex items-start gap-3 rounded-[14px] border border-accent/20 bg-accent/5 px-4 py-3">
        <Info size={15} className="mt-0.5 shrink-0 text-accent" />
        <div>
          <p className="text-[13px] font-medium text-primary">Notifications — bientôt disponible</p>
          <p className="mt-0.5 text-[12px] text-secondary leading-snug">
            Les alertes en temps réel (article publié, analyse SEO terminée, recommandations disponibles) seront disponibles dans une prochaine version.
          </p>
        </div>
      </div>

      {/* Placeholder list */}
      <div className="flex flex-col gap-2">
        {[
          { title: 'Analyse SEO disponible', desc: "L'analyse de votre article sera notifiée ici.", time: 'Bientôt disponible' },
          { title: 'Article publié avec succès', desc: 'Confirmation de publication et lien vers l\'article.', time: 'Bientôt disponible' },
          { title: 'Nouvelles recommandations', desc: "Des optimisations sont disponibles pour vos articles.", time: 'Bientôt disponible' },
        ].map((item, i) => (
          <div
            key={i}
            className="flex items-start gap-3 rounded-[14px] border border-border bg-surface px-4 py-3 opacity-40"
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] bg-[#f0f0f2] text-tertiary">
              <Bell size={14} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-medium text-primary">{item.title}</p>
              <p className="mt-0.5 text-[12px] text-tertiary leading-snug">{item.desc}</p>
            </div>
            <span className="shrink-0 text-[11px] text-tertiary">{item.time}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
