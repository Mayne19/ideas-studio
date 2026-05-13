import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  Activity,
  Crown,
  Edit2,
  Eye,
  FilePenLine,
  Info,
  Palette,
  PenLine,
  Shield,
  Trash2,
  UserPlus,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { listMembers, addMember, updateMemberRole, removeMember } from '@/api/members'
import type { ProjectMember, ProjectRole } from '@/types'
import { useAuth } from '@/context/AuthContext'
import { useProject } from '@/context/ProjectContext'
import FormCard from '@/components/ui/FormCard'
import Button from '@/components/ui/Button'
import Modal from '@/components/ui/Modal'
import ConfirmModal from '@/components/ui/ConfirmModal'
import Input from '@/components/ui/Input'
import Select from '@/components/ui/Select'
import RoleBadge from '@/components/ui/RoleBadge'

import ErrorState from '@/components/ui/ErrorState'
import EmptyState from '@/components/ui/EmptyState'
import { Skeleton } from '@/components/ui/Skeleton'

const ASSIGNABLE_ROLES = [
  { value: 'admin', label: 'Administrateur' },
  { value: 'editor', label: 'Éditeur' },
  { value: 'writer', label: 'Rédacteur' },
  { value: 'viewer', label: 'Lecteur' },
]

const ROLE_GUIDE: Array<{
  role: ProjectRole
  title: string
  backendReady: boolean
  icon: LucideIcon
  permissions: string[]
}> = [
  {
    role: 'owner',
    title: 'Owner',
    backendReady: true,
    icon: Crown,
    permissions: [
      'Contrôle total du projet',
      'Peut supprimer le projet',
      'Gère le billing',
      'Gère tous les membres',
    ],
  },
  {
    role: 'admin',
    title: 'Admin',
    backendReady: true,
    icon: Shield,
    permissions: [
      'Gère le projet',
      'Peut publier',
      'Gère les paramètres',
      'Gère les membres sauf owner',
    ],
  },
  {
    role: 'editor',
    title: 'Editor',
    backendReady: true,
    icon: FilePenLine,
    permissions: [
      'Corrige les contenus',
      'Modifie tous les articles',
      'Valide et marque prêt',
      'Ne publie pas en V1',
    ],
  },
  {
    role: 'writer',
    title: 'Writer',
    backendReady: true,
    icon: PenLine,
    permissions: [
      'Crée des brouillons',
      'Écrit du contenu',
      'Modifie ses brouillons',
      'Envoie en relecture',
      'Ne publie pas',
    ],
  },
  {
    role: 'designer',
    title: 'Designer',
    backendReady: false,
    icon: Palette,
    permissions: [
      'Accès médias',
      'Upload images',
      'Image de couverture',
      'Visuels et bannières',
      'Ne publie pas',
      'Ne modifie pas forcément le texte',
    ],
  },
  {
    role: 'viewer',
    title: 'Viewer',
    backendReady: true,
    icon: Eye,
    permissions: [
      'Lecture seule',
      'Consulte articles et analyses',
      'Ne modifie pas le projet',
    ],
  },
]

function MemberRow({
  member,
  isSelf,
  canManage,
  onEditRole,
  onRemove,
}: {
  member: ProjectMember
  isSelf: boolean
  canManage: boolean
  onEditRole: (member: ProjectMember) => void
  onRemove: (member: ProjectMember) => void
}) {
  const displayName = member.user_name ?? member.user_email ?? 'Utilisateur inconnu'
  const isOwnerMember = member.role === 'owner'

  return (
    <div className="flex items-center gap-3 rounded-[14px] bg-[#f9f9fb] px-4 py-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent/10 text-accent text-[12px] font-semibold">
        {displayName.charAt(0).toUpperCase()}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-[13px] font-medium text-primary truncate">
            {displayName}
            {isSelf && <span className="ml-1 text-tertiary text-[11px]">(vous)</span>}
          </p>
        </div>
        {member.user_email && member.user_name && (
          <p className="text-[12px] text-tertiary truncate">{member.user_email}</p>
        )}
      </div>
      <RoleBadge role={member.role} />
      {canManage && !isOwnerMember && !isSelf && (
        <div className="flex items-center gap-1">
          <button
            onClick={() => onEditRole(member)}
            className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary hover:bg-[#e5e5e7] hover:text-primary transition-colors"
            title="Modifier le rôle"
          >
            <Edit2 size={13} />
          </button>
          <button
            onClick={() => onRemove(member)}
            className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary hover:bg-danger/10 hover:text-danger transition-colors"
            title="Retirer du projet"
          >
            <Trash2 size={13} />
          </button>
        </div>
      )}
      {(!canManage || isOwnerMember) && <div className="w-[60px]" />}
    </div>
  )
}

export default function ProjectMembersPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { user } = useAuth()
  const { project } = useProject()
  const [members, setMembers] = useState<ProjectMember[]>([])
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')

  // Add member modal
  const [addOpen, setAddOpen] = useState(false)
  const [addUserId, setAddUserId] = useState('')
  const [addRole, setAddRole] = useState('writer')
  const [addError, setAddError] = useState('')
  const [adding, setAdding] = useState(false)

  // Edit role modal
  const [editMember, setEditMember] = useState<ProjectMember | null>(null)
  const [editRole, setEditRole] = useState('writer')
  const [editError, setEditError] = useState('')
  const [editing, setEditing] = useState(false)

  // Confirm remove
  const [removeMemberTarget, setRemoveMemberTarget] = useState<ProjectMember | null>(null)
  const [removing, setRemoving] = useState(false)

  const currentMember = members.find((m) => m.user_id === user?.id)
  const canManage = ['owner', 'admin'].includes(currentMember?.role ?? '')
  const isProjectOwner = project?.owner_id === user?.id

  function loadMembers() {
    if (!projectId) return
    listMembers(projectId)
      .then((data) => { setMembers(data); setStatus('success') })
      .catch(() => setStatus('error'))
  }

  useEffect(() => {
    if (!projectId) return
    listMembers(projectId)
      .then((data) => { setMembers(data); setStatus('success') })
      .catch(() => setStatus('error'))
  }, [projectId])

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    if (!projectId || !addUserId.trim()) return
    setAddError('')
    setAdding(true)
    try {
      await addMember(projectId, addUserId.trim(), addRole)
      setAddOpen(false)
      setAddUserId('')
      setAddRole('writer')
      loadMembers()
    } catch (err) {
      setAddError(err instanceof Error ? err.message : 'Erreur lors de l\'ajout')
    } finally {
      setAdding(false)
    }
  }

  async function handleEditRole(e: React.FormEvent) {
    e.preventDefault()
    if (!projectId || !editMember) return
    setEditError('')
    setEditing(true)
    try {
      await updateMemberRole(projectId, editMember.user_id, editRole)
      setEditMember(null)
      loadMembers()
    } catch (err) {
      setEditError(err instanceof Error ? err.message : 'Erreur lors de la modification')
    } finally {
      setEditing(false)
    }
  }

  async function handleRemove() {
    if (!projectId || !removeMemberTarget) return
    setRemoving(true)
    try {
      await removeMember(projectId, removeMemberTarget.user_id)
      setRemoveMemberTarget(null)
      loadMembers()
    } catch (err) {
      console.error(err)
    } finally {
      setRemoving(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <FormCard
        title="Membres de l'équipe"
        description="Gérez les accès et les rôles des membres de ce projet."
        footer={
          (canManage || isProjectOwner) ? (
            <Button
              size="sm"
              icon={<UserPlus size={14} />}
              onClick={() => setAddOpen(true)}
            >
              Ajouter un membre
            </Button>
          ) : undefined
        }
      >
        {status === 'loading' && (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full rounded-[14px]" />
            ))}
          </div>
        )}
        {status === 'error' && (
          <ErrorState message="Impossible de charger les membres." onRetry={loadMembers} />
        )}
        {status === 'success' && members.length === 0 && (
          <EmptyState
            title="Aucun membre"
            description="Ajoutez des collaborateurs pour travailler ensemble sur ce projet."
          />
        )}
        {status === 'success' && members.length > 0 && (
          <div className="flex flex-col gap-2">
            {members.map((member) => (
              <MemberRow
                key={member.id}
                member={member}
                isSelf={member.user_id === user?.id}
                canManage={canManage || isProjectOwner}
                onEditRole={(m) => { setEditMember(m); setEditRole(m.role) }}
                onRemove={setRemoveMemberTarget}
              />
            ))}
          </div>
        )}
      </FormCard>

      <FormCard
        title="Rôles et permissions"
        description="Comprenez rapidement ce que chaque rôle peut faire dans Ideas Studio."
      >
        <div className="grid gap-2 md:grid-cols-2">
          {ROLE_GUIDE.map((item) => {
            const RoleIcon = item.icon

            return (
              <div key={item.role} className="rounded-[16px] bg-[#f9f9fb] px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[10px] bg-white text-tertiary">
                      <RoleIcon size={14} />
                    </span>
                    <p className="text-[13px] font-semibold text-primary">{item.title}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <RoleBadge role={item.role} />
                    {!item.backendReady && (
                      <span className="rounded-full bg-[#f0f0f2] px-2 py-0.5 text-[10px] font-medium text-tertiary">
                        Bientôt disponible
                      </span>
                    )}
                  </div>
                </div>
                <ul className="mt-2 flex flex-col gap-1">
                  {item.permissions.map((permission) => (
                    <li key={permission} className="text-[12px] leading-snug text-secondary">
                      {permission}
                    </li>
                  ))}
                </ul>
                {!item.backendReady && (
                  <p className="mt-2 text-[11px] leading-snug text-tertiary">
                    Designer est documenté dans l'UI, mais n'est pas encore assignable côté API.
                  </p>
                )}
              </div>
            )
          })}
        </div>
      </FormCard>

      <FormCard
        title="Activité équipe"
        description="Suivez qui a modifié quoi, ajouté une image ou travaillé sur un article."
      >
        <div className="flex items-start gap-3 rounded-[16px] bg-[#f9f9fb] px-4 py-4">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[12px] bg-[#f0f0f2] text-tertiary">
            <Activity size={16} />
          </span>
          <div>
            <p className="text-[13px] font-medium text-primary">Activité équipe bientôt disponible</p>
            <p className="mt-0.5 text-[12px] leading-relaxed text-secondary">
              Le backend ne fournit pas encore de journal d'activité membre. Aucun faux événement n'est affiché.
            </p>
          </div>
        </div>
      </FormCard>

      {/* Add member modal */}
      <Modal
        open={addOpen}
        onClose={() => { setAddOpen(false); setAddError(''); setAddUserId('') }}
        title="Ajouter un membre"
        size="sm"
      >
        <form onSubmit={handleAdd} className="flex flex-col gap-4">
          {addError && (
            <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger">
              {addError}
            </div>
          )}

          {/* Email invitation — coming soon */}
          <div className="rounded-[16px] bg-[#f9f9fb] px-4 py-3 flex flex-col gap-2">
            <p className="text-[13px] font-medium text-primary">Invitation par email</p>
            <p className="text-[12px] text-secondary leading-snug">
              L'invitation par email sera disponible prochainement.
            </p>
            <input
              type="email"
              placeholder="collaborateur@example.com"
              disabled
              className="w-full rounded-[10px] border border-border bg-[#f0f0f2] px-3 py-2 text-[13px] text-tertiary opacity-50 cursor-not-allowed outline-none"
            />
          </div>

          <Select
            label="Rôle"
            options={ASSIGNABLE_ROLES}
            value={addRole}
            onChange={(e) => setAddRole(e.target.value)}
            hint="Le rôle Designer est préparé dans l'UI, mais pas encore assignable côté backend."
          />

          {/* Developer section — collapsible */}
          <details className="rounded-[10px] border border-border">
            <summary className="cursor-pointer px-3 py-2 text-[12px] font-medium text-tertiary hover:text-secondary transition-colors select-none">
              Section développeur — ajouter par ID utilisateur
            </summary>
            <div className="px-3 pb-3 pt-2 flex flex-col gap-3">
              <div className="flex items-start gap-2">
                <Info size={12} className="mt-0.5 shrink-0 text-tertiary" />
                <p className="text-[11px] text-tertiary leading-snug">
                  L'utilisateur doit déjà avoir un compte Ideas Studio. L'ID se trouve dans son profil.
                </p>
              </div>
              <Input
                label="ID utilisateur"
                value={addUserId}
                onChange={(e) => setAddUserId(e.target.value)}
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                required={false}
              />
            </div>
          </details>

          <div className="flex gap-2 pt-1">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="flex-1 justify-center"
              onClick={() => setAddOpen(false)}
            >
              Annuler
            </Button>
            <Button
              type="submit"
              size="sm"
              loading={adding}
              disabled={!addUserId.trim()}
              className="flex-1 justify-center"
            >
              Ajouter
            </Button>
          </div>
        </form>
      </Modal>

      {/* Edit role modal */}
      <Modal
        open={!!editMember}
        onClose={() => { setEditMember(null); setEditError('') }}
        title="Modifier le rôle"
        size="sm"
      >
        <form onSubmit={handleEditRole} className="flex flex-col gap-4">
          {editError && (
            <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger">
              {editError}
            </div>
          )}
          <p className="text-[13px] text-secondary">
            Modifier le rôle de{' '}
            <strong className="text-primary">
              {editMember?.user_name ?? editMember?.user_email}
            </strong>
          </p>
          <Select
            label="Nouveau rôle"
            options={ASSIGNABLE_ROLES}
            value={editRole}
            onChange={(e) => setEditRole(e.target.value)}
            hint="Designer n'est pas proposé ici pour éviter d'envoyer un rôle non supporté par l'API."
          />
          <div className="flex gap-2 pt-1">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="flex-1 justify-center"
              onClick={() => setEditMember(null)}
            >
              Annuler
            </Button>
            <Button type="submit" size="sm" loading={editing} className="flex-1 justify-center">
              Modifier
            </Button>
          </div>
        </form>
      </Modal>

      {/* Confirm remove */}
      <ConfirmModal
        open={!!removeMemberTarget}
        onClose={() => setRemoveMemberTarget(null)}
        onConfirm={handleRemove}
        title="Retirer ce membre ?"
        description={`${removeMemberTarget?.user_name ?? removeMemberTarget?.user_email} n'aura plus accès à ce projet.`}
        confirmLabel="Retirer"
        loading={removing}
        variant="danger"
      />

    </div>
  )
}
