export type SettingsSectionKey =
  | 'general'
  | 'strategy'
  | 'team'
  | 'integration'
  | 'callouts'
  | 'providers'
  | 'agents'
  | 'pipeline'
  | 'profile'

export type SettingsSection = {
  key: SettingsSectionKey
  label: string
  description: string
  path: string
  end?: boolean
}

export function getSettingsSections(projectId: string | undefined): SettingsSection[] {
  const projectBase = projectId ? `/projects/${projectId}/settings` : '/projects'

  return [
    { key: 'general', label: 'Général', description: 'Nom, domaine, langue', path: projectBase, end: true },
    { key: 'strategy', label: 'Stratégie', description: 'Audience et ton éditorial', path: `${projectBase}/strategy` },
    { key: 'team', label: 'Équipe', description: 'Membres, rôles et accès', path: `${projectBase}/team` },
    { key: 'integration', label: 'Intégration', description: 'Site connecté et API', path: `${projectBase}/integration` },
    { key: 'callouts', label: 'Callouts', description: 'Templates éditoriaux', path: `${projectBase}/callouts` },
    { key: 'providers', label: 'Providers', description: 'Services IA connectés', path: `${projectBase}/providers` },
    { key: 'agents', label: 'Agents', description: 'Routage des agents IA', path: `${projectBase}/agents` },
    { key: 'pipeline', label: 'Pipeline', description: 'Automatisations éditoriales', path: `${projectBase}/pipeline` },
    { key: 'profile', label: 'Profil', description: 'Compte utilisateur', path: `${projectBase}/profile` },
  ]
}
