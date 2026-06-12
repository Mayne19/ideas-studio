export type PublicLocale = 'en' | 'fr' | 'de' | 'es'

export const PUBLIC_LOCALES: PublicLocale[] = ['en', 'fr', 'de', 'es']

type PublicCopy = {
  nav: {
    features: string
    pricing: string
    documentation: string
    support: string
    signIn: string
    start: string
  }
  hero: {
    eyebrow: string
    title: string
    subtitle: string
    primary: string
    secondary: string
  }
}

export const publicCopy: Record<PublicLocale, PublicCopy> = {
  en: {
    nav: {
      features: 'Features',
      pricing: 'Pricing',
      documentation: 'Docs',
      support: 'Support',
      signIn: 'Sign in',
      start: 'Start free',
    },
    hero: {
      eyebrow: 'AI editorial operations for serious content teams',
      title: 'Plan, write, optimize and publish from one studio.',
      subtitle:
        'Ideas Studio connects strategy, AI generation, editorial production, SEO analysis and performance monitoring in a single workflow.',
      primary: 'Open the studio',
      secondary: 'See pricing',
    },
  },
  fr: {
    nav: {
      features: 'Fonctionnalités',
      pricing: 'Tarifs',
      documentation: 'Docs',
      support: 'Support',
      signIn: 'Connexion',
      start: 'Essayer',
    },
    hero: {
      eyebrow: 'Operations editoriales IA pour equipes contenu',
      title: 'Planifiez, redigez, optimisez et publiez depuis un studio.',
      subtitle:
        'Ideas Studio relie strategie, generation IA, production editoriale, analyse SEO et suivi de performance dans un seul workflow.',
      primary: 'Ouvrir le studio',
      secondary: 'Voir les tarifs',
    },
  },
  de: {
    nav: {
      features: 'Funktionen',
      pricing: 'Preise',
      documentation: 'Docs',
      support: 'Support',
      signIn: 'Anmelden',
      start: 'Kostenlos starten',
    },
    hero: {
      eyebrow: 'KI-Redaktionsbetrieb fuer Content-Teams',
      title: 'Planen, schreiben, optimieren und veroeffentlichen.',
      subtitle:
        'Ideas Studio verbindet Strategie, KI-Erstellung, Produktion, SEO-Analyse und Performance-Monitoring in einem Workflow.',
      primary: 'Studio oeffnen',
      secondary: 'Preise ansehen',
    },
  },
  es: {
    nav: {
      features: 'Funciones',
      pricing: 'Precios',
      documentation: 'Docs',
      support: 'Soporte',
      signIn: 'Entrar',
      start: 'Empezar gratis',
    },
    hero: {
      eyebrow: 'Operaciones editoriales con IA para equipos de contenido',
      title: 'Planifica, escribe, optimiza y publica desde un estudio.',
      subtitle:
        'Ideas Studio conecta estrategia, generacion IA, produccion editorial, analisis SEO y rendimiento en un solo flujo.',
      primary: 'Abrir el estudio',
      secondary: 'Ver precios',
    },
  },
}
