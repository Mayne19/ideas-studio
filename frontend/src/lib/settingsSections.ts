export type SettingsSectionKey =
  | 'general'
  | 'strategy'
  | 'team'
  | 'integration'
  | 'callouts'
  | 'providers'
  | 'agents'
  | 'pipeline'
  | 'ia'

export type SettingsSection = {
  key: SettingsSectionKey
  label: string
  description: string
  path: string
  end?: boolean
  adminOnly?: boolean
}

const ADMIN_ONLY_KEYS: SettingsSectionKey[] = ['providers', 'agents', 'pipeline', 'ia']

export function getSettingsSections(
  projectId: string | undefined,
  options?: { showAdminOnly?: boolean },
): SettingsSection[] {
  const projectBase = projectId ? `/projects/${projectId}/settings` : '/projects'
  const showAdminOnly = options?.showAdminOnly ?? true

  const all: SettingsSection[] = [
    { key: 'general', label: 'Général', description: 'Nom, domaine, langue', path: projectBase, end: true },
    { key: 'strategy', label: 'Stratégie', description: 'Audience et ton éditorial', path: `${projectBase}/strategy` },
    { key: 'team', label: 'Équipe', description: 'Membres, rôles et accès', path: `${projectBase}/members` },
    { key: 'integration', label: 'Intégration', description: 'Site connecté et API', path: `${projectBase}/integration` },
    { key: 'callouts', label: 'Callouts', description: 'Templates éditoriaux', path: `${projectBase}/callouts` },
    { key: 'providers', label: 'Providers', description: 'Services IA connectés', path: `${projectBase}/providers`, adminOnly: true },
    { key: 'agents', label: 'Agents', description: 'Routage des agents IA', path: `${projectBase}/agents`, adminOnly: true },
    { key: 'pipeline', label: 'Pipeline', description: 'Automatisations éditoriales', path: `${projectBase}/pipeline`, adminOnly: true },
    { key: 'ia', label: 'IA & Workflows', description: 'Providers, agents, pipeline IA', path: `${projectBase}/ia`, adminOnly: true },
  ]

  if (!showAdminOnly) {
    return all.filter((s) => !ADMIN_ONLY_KEYS.includes(s.key))
  }
  return all
}
