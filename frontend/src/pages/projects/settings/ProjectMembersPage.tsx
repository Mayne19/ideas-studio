import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  Activity,
  AtSign,
  Crown,
  Edit2,
  Eye,
  FilePenLine,
  Link,
  Mail,

  PenLine,
  Shield,
  Trash2,
  UserPlus,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { listMembers, addMemberByUsername, inviteByEmail, updateMemberRole, removeMember, listInvitations } from '@/api/members'
import { listActivity } from '@/api/activity'
import type { Invitation, ProjectMember, ProjectRole, ActivityLog } from '@/types'
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
import { formatDate } from '@/utils/format'

const ASSIGNABLE_ROLES = [
  { value: 'admin', label: 'Administrateur' },
  { value: 'editor', label: 'Éditeur' },
  { value: 'writer', label: 'Rédacteur' },
  { value: 'viewer', label: 'Lecteur' },
]

const ROLE_GUIDE: Array<{
  role: ProjectRole
  title: string
  icon: LucideIcon
  permissions: string[]
}> = [
  {
    role: 'owner',
    title: 'Owner',
    icon: Crown,
    permissions: [
      'Contrôle total du projet',
      'Peut supprimer le projet',
      'Gère tous les membres',
    ],
  },
  {
    role: 'admin',
    title: 'Admin',
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
    icon: FilePenLine,
    permissions: [
      'Corrige les contenus',
      'Modifie tous les articles',
      'Valide et marque prêt',
    ],
  },
  {
    role: 'writer',
    title: 'Writer',
    icon: PenLine,
    permissions: [
      'Crée des brouillons',
      'Écrit du contenu',
      'Modifie ses brouillons',
      'Envoie en relecture',
    ],
  },
  {
    role: 'viewer',
    title: 'Viewer',
    icon: Eye,
    permissions: [
      'Lecture seule',
      'Consulte articles et analyses',
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
        <p className="text-[12px] text-tertiary truncate">
          {member.user_username ? `@${member.user_username}` : member.user_email}
        </p>
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
  const [invitations, setInvitations] = useState<Invitation[]>([])
  const [activityLogs, setActivityLogs] = useState<ActivityLog[]>([])
  const [activityStatus, setActivityStatus] = useState<'loading' | 'success' | 'error'>('loading')

  // Add member by username
  const [addOpen, setAddOpen] = useState(false)
  const [addType, setAddType] = useState<'username' | 'email'>('username')
  const [addUsername, setAddUsername] = useState('')
  const [addEmail, setAddEmail] = useState('')
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

  function loadInvitations() {
    if (!projectId) return
    listInvitations(projectId).then(setInvitations).catch(() => {})
  }

  useEffect(() => {
    if (!projectId) return
    listMembers(projectId)
      .then((data) => { setMembers(data); setStatus('success') })
      .catch(() => setStatus('error'))
    listInvitations(projectId).then(setInvitations).catch(() => {})
    listActivity(projectId)
      .then((data) => { setActivityLogs(data); setActivityStatus('success') })
      .catch(() => setActivityStatus('error'))
  }, [projectId])

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    if (!projectId) return
    setAddError('')
    setAdding(true)
    try {
      if (addType === 'username' && addUsername.trim()) {
        await addMemberByUsername(projectId, addUsername.trim(), addRole)
      } else if (addType === 'email' && addEmail.trim()) {
        await inviteByEmail(projectId, addEmail.trim(), addRole)
      } else {
        setAddError('Veuillez remplir le champ.')
        setAdding(false)
        return
      }
      setAddOpen(false)
      setAddUsername('')
      setAddEmail('')
      setAddRole('writer')
      loadMembers()
      loadInvitations()
    } catch (err) {
      setAddError(err instanceof Error ? err.message : "Erreur lors de l'ajout")
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

      {invitations.filter((inv) => !inv.accepted_at).length > 0 && (
        <FormCard
          title="Invitations en attente"
          description="Les invitations créées pour les nouveaux collaborateurs. Copiez le lien si l'envoi email n'est pas configuré."
        >
          <div className="flex flex-col gap-2">
            {invitations.map((invitation) => {
              const expired = new Date(invitation.expires_at) < new Date()
              const accepted = !!invitation.accepted_at

              return (
                <div
                  key={invitation.id}
                  className="flex items-center gap-3 rounded-[14px] bg-[#f9f9fb] px-4 py-3"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-medium text-primary truncate">
                      {invitation.email}
                    </p>
                    <p className="text-[12px] text-tertiary">
                      Envoyée le{' '}
                      {new Date(invitation.created_at).toLocaleDateString('fr-FR', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                      })}
                    </p>
                  </div>
                  <RoleBadge role={invitation.role} />
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${
                      accepted
                        ? 'bg-success/10 text-[#1a7a3a]'
                        : expired
                          ? 'bg-danger/10 text-danger'
                          : 'bg-warning/10 text-[#c07000]'
                    }`}
                  >
                    {accepted
                      ? 'Acceptée'
                      : expired
                        ? 'Expirée'
                        : 'En attente'}
                  </span>
                  {!accepted && (
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(
                          `${window.location.origin}/invitations/${invitation.token}`,
                        )
                      }}
                      className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary hover:bg-[#e5e5e7] hover:text-primary transition-colors"
                      title="Copier le lien d'invitation"
                    >
                      <Link size={13} />
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        </FormCard>
      )}

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
                  <RoleBadge role={item.role} />
                </div>
                <ul className="mt-2 flex flex-col gap-1">
                  {item.permissions.map((permission) => (
                    <li key={permission} className="text-[12px] leading-snug text-secondary">
                      {permission}
                    </li>
                  ))}
                </ul>
              </div>
            )
          })}
        </div>
      </FormCard>

      <FormCard
        title="Activité équipe"
        description="Suivez qui a modifié quoi, ajouté une image ou travaillé sur un article."
      >
        {activityStatus === 'loading' && (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full rounded-[10px]" />
            ))}
          </div>
        )}
        {activityStatus === 'error' && (
          <div className="flex items-start gap-3 rounded-[16px] bg-[#f9f9fb] px-4 py-4">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[12px] bg-[#f0f0f2] text-tertiary">
              <Activity size={16} />
            </span>
            <div>
              <p className="text-[13px] font-medium text-primary">Aucune activité récente</p>
              <p className="mt-0.5 text-[12px] leading-relaxed text-secondary">
                Les actions de l'équipe apparaîtront ici au fur et à mesure.
              </p>
            </div>
          </div>
        )}
        {activityStatus === 'success' && activityLogs.length === 0 && (
          <div className="flex items-start gap-3 rounded-[16px] bg-[#f9f9fb] px-4 py-4">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[12px] bg-[#f0f0f2] text-tertiary">
              <Activity size={16} />
            </span>
            <div>
              <p className="text-[13px] font-medium text-primary">Aucune activité récente</p>
              <p className="mt-0.5 text-[12px] leading-relaxed text-secondary">
                Les actions de l'équipe apparaîtront ici au fur et à mesure.
              </p>
            </div>
          </div>
        )}
        {activityStatus === 'success' && activityLogs.length > 0 && (
          <div className="flex flex-col gap-1.5">
            {activityLogs.map((log) => (
              <div key={log.id} className="flex items-start gap-3 rounded-[10px] bg-[#f9f9fb] px-3 py-2.5">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent/10 text-accent text-[9px] font-bold">
                  {(log.user_name || '?').charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[12px] text-primary">
                    <span className="font-medium">{log.user_name || 'Quelqu\'un'}</span>
                    {' '}{log.description || log.action}
                  </p>
                  <p className="text-[10px] text-tertiary mt-0.5">{formatDate(log.created_at)}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </FormCard>

      {/* Add member modal */}
      <Modal
        open={addOpen}
        onClose={() => { setAddOpen(false); setAddError(''); setAddUsername(''); setAddEmail('') }}
        title="Ajouter un membre"
        size="sm"
      >
        <form onSubmit={handleAdd} className="flex flex-col gap-4">
          {addError && (
            <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger">
              {addError}
            </div>
          )}

          {/* Toggle between username and email */}
          <div className="flex rounded-[10px] border border-border overflow-hidden">
            <button
              type="button"
              onClick={() => setAddType('username')}
              className={`flex-1 px-3 py-2 text-[12px] font-medium transition-colors ${
                addType === 'username'
                  ? 'bg-accent text-white'
                  : 'bg-[#f5f5f7] text-tertiary hover:text-secondary'
              }`}
            >
              <AtSign size={13} className="inline mr-1" />
              @username
            </button>
            <button
              type="button"
              onClick={() => setAddType('email')}
              className={`flex-1 px-3 py-2 text-[12px] font-medium transition-colors ${
                addType === 'email'
                  ? 'bg-accent text-white'
                  : 'bg-[#f5f5f7] text-tertiary hover:text-secondary'
              }`}
            >
              <Mail size={13} className="inline mr-1" />
              Email
            </button>
          </div>

          {addType === 'username' ? (
            <Input
              label="Nom d'utilisateur"
              value={addUsername}
              onChange={(e) => setAddUsername(e.target.value)}
              placeholder="@pseudo"
              hint="L'utilisateur doit déjà avoir un compte Ideas Studio."
            />
          ) : (
            <Input
              label="Adresse e-mail"
              type="email"
              value={addEmail}
              onChange={(e) => setAddEmail(e.target.value)}
              placeholder="collaborateur@example.com"
              hint="Une invitation sera créée. Copiez ensuite le lien d'invitation si l'email transactionnel n'est pas configuré."
            />
          )}

          <Select
            label="Rôle"
            options={ASSIGNABLE_ROLES}
            value={addRole}
            onChange={(e) => setAddRole(e.target.value)}
            hint="Le rôle Designer n'est pas encore assignable."
          />

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
              disabled={
                addType === 'username' ? !addUsername.trim() : !addEmail.trim()
              }
              className="flex-1 justify-center"
            >
              {addType === 'username' ? 'Ajouter' : 'Inviter'}
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
