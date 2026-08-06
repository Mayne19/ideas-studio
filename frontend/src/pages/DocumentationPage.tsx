import { useEffect, useMemo, useRef, useState } from 'react'
import type { ComponentType, KeyboardEvent as ReactKeyboardEvent } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight, Download, Search, Menu, X,
  Zap, BookOpen, FolderOpen, Globe, ClipboardList, FileText, TrendingUp,
  RefreshCw, Cpu, Bot, ShieldCheck, Users, Code, BarChart2, Lock, HelpCircle,
  ChevronLeft, ChevronRight,
} from '@/components/ui/hugeIcons'
import { Card } from '@/components/ui/Card'

type IconType = ComponentType<{ size?: number; className?: string }>

const configuredApiUrl = (import.meta.env['VITE_API_URL'] as string | undefined)?.trim().replace(/\/$/, '')
const documentationApiUrl = configuredApiUrl || 'http://localhost:8000'

const NAV_ITEMS = [
  { label: 'Produits', href: '#getting-started' },
  { label: 'Documentation', href: '/documentation' },
  { label: 'Blog', href: '#' },
  { label: 'Contact', href: '#' },
]

interface Chapter {
  id: string
  label: string
  icon: IconType
  sections: { id: string; label: string; depth: number }[]
  content: string
}

const CHAPTERS: Chapter[] = [
  {
    id: 'prise-en-main',
    label: 'Prise en main',
    icon: Zap,
    sections: [
      { id: 'quest-ce-que-ideas-studio', label: "Qu'est-ce que Ideas Studio", depth: 2 },
      { id: 'a-qui-sadresse-cet-outil', label: 'À qui sadresse cet outil', depth: 2 },
      { id: 'prerequis', label: 'Prérequis', depth: 2 },
      { id: 'premiers-pas', label: 'Premiers pas', depth: 2 },
      { id: 'prochaine-etapes', label: 'Prochaines étapes', depth: 2 },
    ],
    content: `
      <h2 id="quest-ce-que-ideas-studio">Qu'est-ce que Ideas Studio</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Ideas Studio est un espace de production éditoriale assistée par IA. Il aide votre équipe à passer de la stratégie aux articles publiables, avec contrôle humain à chaque étape. La plateforme combine un moteur de génération piloté par des agents IA spécialisés, des dashboards de performance et de trafic, un pipeline de publication automatisé, et des outils de collaboration éditoriale.</p>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Contrairement aux générateurs d'articles basiques qui produisent du contenu générique, Ideas Studio orchestre 62 agents IA répartis en quatre catégories (recherche, stratégie, création, révision) pour produire des articles contextualisés, optimisés pour le SEO et adaptés à votre audience.</p>

      <h2 id="a-qui-sadresse-cet-outil" class="mt-12">À qui s'adresse cet outil</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Ideas Studio est conçu pour les équipes éditoriales, les rédacteurs solo, les agences de contenu et les services marketing qui produisent du contenu régulier. Il convient aussi bien aux blogs personnels qu'aux sites d'actualité ou aux magazines en ligne.</p>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le studio s'adresse à des utilisateurs ayant des compétences techniques minimales : savoir installer un snippet JavaScript sur un site existant. Si vous utilisez un CMS comme WordPress, Next.js, Hugo ou tout autre générateur de site, l'intégration est possible.</p>

      <h2 id="prerequis" class="mt-12">Prérequis</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Avant d'utiliser Ideas Studio, vous avez besoin de :</p>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li>Un site public où installer le snippet de tracking.</li>
        <li>Une clé API d'un service d'IA (Gemini, OpenAI, OpenRouter ou Ollama).</li>
        <li>Un compte Ideas Studio (auto-hébergé ou hébergé).</li>
      </ul>

      <h2 id="premiers-pas" class="mt-12">Premiers pas</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le parcours typique d'un nouvel utilisateur se déroule en cinq étapes :</p>
      <ol class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-decimal pl-6">
        <li><strong class="text-primary">Créer un projet</strong> — Définissez votre domaine, votre équipe et votre stratégie éditoriale.</li>
        <li><strong class="text-primary">Connecter votre site</strong> — Installez le snippet de tracking pour collecter les données de visite.</li>
        <li><strong class="text-primary">Configurer un provider IA</strong> — Ajoutez votre clé API et choisissez un modèle.</li>
        <li><strong class="text-primary">Assigner des agents</strong> — Répartissez les tâches de génération entre vos providers.</li>
        <li><strong class="text-primary">Générer vos premiers articles</strong> — Lancez la production et validez les brouillons.</li>
      </ol>

      <h2 id="prochaine-etapes" class="mt-12">Prochaines étapes</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Une fois les bases installées, explorez le pipeline automatique pour planifier une production régulière, les dashboards de performance pour suivre l'impact de vos articles, et les rapports SEO pour optimiser votre référencement.</p>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">La documentation détaille chaque fonctionnalité dans les chapitres suivants.</p>
    `,
  },
  {
    id: 'concepts',
    label: 'Concepts fondamentaux',
    icon: BookOpen,
    sections: [
      { id: 'projet', label: 'Projet', depth: 2 },
      { id: 'membres-et-roles', label: 'Membres et rôles', depth: 2 },
      { id: 'sites-publics-vs-studio', label: 'Sites publics vs studio', depth: 2 },
      { id: 'agents-ia', label: 'Agents IA', depth: 2 },
      { id: 'pipeline-editorial', label: 'Pipeline éditorial', depth: 2 },
      { id: 'tracking-analytics', label: 'Tracking et analytics', depth: 2 },
      { id: 'cycle-de-vie-article', label: 'Cycle de vie article', depth: 2 },
    ],
    content: `
      <h2 id="projet">Projet</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Un projet regroupe un domaine, des membres, une stratégie éditoriale, des articles, des catégories et des analytics. Chaque projet est indépendant : ses données, sa configuration IA et son équipe lui sont propres. Un utilisateur peut appartenir à plusieurs projets avec des rôles différents.</p>

      <h2 id="membres-et-roles" class="mt-12">Membres et rôles</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Chaque projet a son propre système de rôles (Owner, Admin, Editor, Designer, Viewer) qui détermine ce que chaque membre peut faire — voir le détail dans le chapitre <em>Accès et permissions</em>.</p>

      <h2 id="sites-publics-vs-studio" class="mt-12">Sites publics vs studio</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le studio et le site public sont deux entités distinctes. Le studio gère la production éditoriale, les workflows et les analytics. Le site public affiche les articles et envoie les données de tracking via un snippet JavaScript. Cette séparation permet de travailler sur le contenu sans impacter le site en production.</p>

      <h2 id="agents-ia" class="mt-12">Agents IA</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Les agents IA sont des modules spécialisés chacun dans une tâche précise : recherche de mots-clés, génération d'idées, rédaction, relecture, analyse SEO, etc. Le système compte 62 agents répartis en quatre catégories. Chaque agent peut être assigné à un provider IA ; les agents purement heuristiques (sans appel LLM) ne peuvent pas recevoir de provider.</p>

      <h2 id="pipeline-editorial" class="mt-12">Pipeline éditorial</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le pipeline est un flux de production automatisé qui enchaîne les agents IA selon un ordre défini. Il peut être déclenché manuellement ou planifié. Le pipeline ne publie jamais d'article sans validation humaine : il produit des brouillons qui attendent relecture et approbation.</p>

      <h2 id="tracking-analytics" class="mt-12">Tracking et analytics</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le tracking collecte les données de visite du site public via un snippet JavaScript. Chaque page visitée envoie un événement au studio, qui les agrège dans les dashboards de performance et de trafic. Les données sont consultables par période : 1 jour, 7 jours, 30 jours, 90 jours, 6 mois ou 1 an.</p>

      <h2 id="cycle-de-vie-article" class="mt-12">Cycle de vie d'un article</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Un article parcourt plusieurs statuts : idée proposée, prioritaire, en rédaction, brouillon prêt, à relire, prêt, programmé, publié ou archivé. Ce cycle permet à l'équipe de suivre l'avancement de chaque contenu et de valider chaque étape avant publication.</p>
    `,
  },
  {
    id: 'creer-projet',
    label: 'Créer un projet',
    icon: FolderOpen,
    sections: [
      { id: 'configuration-initiale', label: 'Configuration initiale', depth: 2 },
      { id: 'champs-obligatoires', label: 'Champs obligatoires', depth: 2 },
      { id: 'strategie-editoriale', label: 'Stratégie éditoriale', depth: 2 },
      { id: 'inviter-equipe', label: 'Inviter l\'équipe', depth: 2 },
      { id: 'erreurs-frequentes', label: 'Erreurs fréquentes', depth: 2 },
    ],
    content: `
      <h2 id="configuration-initiale">Configuration initiale</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">La création d'un projet est la première action dans le studio. Depuis la page Mes projets, cliquez sur Nouveau projet et renseignez les informations demandées. Le projet est immédiatement créé et vous devenez son owner.</p>

      <h2 id="champs-obligatoires" class="mt-12">Champs obligatoires</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le formulaire de création demande les informations suivantes :</p>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li><strong class="text-primary">Nom du projet</strong> — Interne au studio, visible uniquement par les membres.</li>
        <li><strong class="text-primary">Domaine</strong> — Le domaine public du site (ex: <code class="text-accent">monblog.com</code>).</li>
        <li><strong class="text-primary">Langue principale</strong> — La langue de vos contenus.</li>
        <li><strong class="text-primary">Pays cible</strong> — Optionnel, pour le ciblage SEO.</li>
      </ul>

      <h2 id="strategie-editoriale" class="mt-12">Stratégie éditoriale</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Dans les paramètres du projet, la section Stratégie vous permet de définir l'audience cible et le ton éditorial. Ces informations sont utilisées par les agents IA pour adapter la génération de contenu au contexte de votre marque.</p>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">L'assistant de configuration IA peut vous aider à définir ces paramètres en analysant votre site existant. Il suffit de fournir l'URL de votre site et l'assistant suggère une audience et un ton adaptés.</p>

      <h2 id="inviter-equipe" class="mt-12">Inviter l'équipe</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Dans Paramètres / Équipe, vous pouvez inviter des collaborateurs par email ou par nom d'utilisateur. Choisissez le rôle approprié pour chaque membre selon ses responsabilités. L'invité reçoit une notification et accède au projet après acceptation.</p>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Vous pouvez à tout moment modifier le rôle d'un membre ou le retirer du projet.</p>

      <h2 id="erreurs-frequentes" class="mt-12">Erreurs fréquentes</h2>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li><strong class="text-primary">Domaine manquant</strong> — Sans domaine, le snippet ne peut pas être configuré et le statut reste "Non configuré".</li>
        <li><strong class="text-primary">Projet sans stratégie</strong> — La génération d'articles manque de contexte si l'audience et le ton ne sont pas définis.</li>
        <li><strong class="text-primary">Invitation sans rôle défini</strong> — Un nouveau membre doit toujours recevoir un rôle explicite.</li>
      </ul>
    `,
  },
  {
    id: 'connecter-site',
    label: 'Connecter un site',
    icon: Globe,
    sections: [
      { id: 'pourquoi-connecter', label: 'Pourquoi connecter un site', depth: 2 },
      { id: 'donnees-collectees', label: 'Le snippet et les données collectées', depth: 2 },
      { id: 'ou-trouver-le-snippet', label: 'Où trouver le snippet', depth: 2 },
      { id: 'installer-sur-votre-site', label: 'Installer sur votre site', depth: 2 },
      { id: 'verifier-la-connexion', label: 'Vérifier que ça fonctionne', depth: 2 },
      { id: 'erreurs-frequentes', label: 'Erreurs fréquentes', depth: 2 },
    ],
    content: `
      <h2 id="pourquoi-connecter">Pourquoi connecter un site</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Connecter votre site public à Ideas Studio permet de collecter les données de navigation (pages vues, sources de trafic, appareils) et de les visualiser dans le dashboard Analytics. Sans connexion, ce dashboard reste vide.</p>

      <h2 id="donnees-collectees" class="mt-12">Le snippet et les données collectées</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le snippet est un petit script JavaScript, généré automatiquement pour chaque projet, qui collecte les visites de votre site public sans dégrader ses performances. Il envoie uniquement :</p>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li>L'URL et le chemin de la page visitée.</li>
        <li>Le referrer (d'où vient le visiteur).</li>
        <li>Le type d'appareil et le navigateur utilisés.</li>
        <li>Une empreinte anonyme (hash) pour estimer les visiteurs uniques.</li>
      </ul>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Aucun cookie n'est déposé et aucune donnée personnelle identifiable (email, nom, IP en clair) n'est stockée.</p>

      <h2 id="ou-trouver-le-snippet" class="mt-12">Où trouver le snippet</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le snippet est disponible dans Paramètres / Intégration de votre projet, avec l'ID du projet, la clé de tracking publique et le statut de connexion. Il est unique par projet et ne doit pas être partagé entre plusieurs sites.</p>

      <h2 id="installer-sur-votre-site" class="mt-12">Installer sur votre site</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Copiez le snippet et placez-le dans la balise <code class="text-accent">&lt;head&gt;</code> de votre site. Il fonctionne sur tout site HTML, quel que soit le framework — aucune dépendance supplémentaire n'est requise. Le script se charge de manière asynchrone.</p>

      <h3 id="installation-nextjs" class="mt-8">Next.js</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Intégrez le snippet via un composant <code class="text-accent">Script</code> dans votre layout racine, en veillant à ce qu'il s'exécute côté client.</p>

      <h3 id="installation-wordpress" class="mt-8">WordPress</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Ajoutez le snippet dans <code class="text-accent">header.php</code> de votre thème, ou utilisez un plugin d'injection de code comme Header Footer Code Manager.</p>

      <h3 id="installation-gtm" class="mt-8">Google Tag Manager</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Créez un tag HTML personnalisé dans GTM avec le snippet, et déclenchez-le sur toutes les pages.</p>

      <h2 id="verifier-la-connexion" class="mt-12">Vérifier que ça fonctionne</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Ouvrez la console développeur (F12) de votre navigateur sur une page du site : aucune erreur JavaScript ne doit apparaître, et l'onglet Réseau doit montrer une requête envoyée au studio à chaque chargement. Rafraîchissez ensuite le statut dans le studio — il passe à "Connecté" dès la première visite reçue. Dans le dashboard Analytics, le message "Snippet connecté, aucune donnée reçue pour cette période" signifie que l'installation est correcte mais qu'aucune visite n'a encore eu lieu sur la période sélectionnée.</p>

      <h2 id="erreurs-frequentes" class="mt-12">Erreurs fréquentes</h2>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li><strong class="text-primary">Le snippet n'est pas exécuté</strong> — Vérifiez qu'il est bien dans le <code class="text-accent">&lt;head&gt;</code> et qu'aucun bloqueur de scripts ne l'empêche de s'exécuter.</li>
        <li><strong class="text-primary">Le domaine ne correspond pas</strong> — Le domaine renseigné dans le projet doit correspondre au domaine où le snippet est installé, sinon le statut reste "Non connecté".</li>
        <li><strong class="text-primary">Aucune donnée après installation</strong> — Visitez une page après l'installation pour générer un premier événement.</li>
      </ul>
    `,
  },
  {
    id: 'checklist',
    label: 'Checklist de production',
    icon: ClipboardList,
    sections: [
      { id: 'avant-le-lancement', label: 'Avant le lancement', depth: 2 },
      { id: 'configuration-ia', label: 'Configuration IA', depth: 2 },
      { id: 'equipe-et-permissions', label: 'Équipe et permissions', depth: 2 },
      { id: 'contenu-et-strategie', label: 'Contenu et stratégie', depth: 2 },
      { id: 'derniers-controles', label: 'Derniers contrôles', depth: 2 },
    ],
    content: `
      <h2 id="avant-le-lancement">Avant le lancement</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Avant de lancer votre projet en production, vérifiez que les éléments de base sont en place. Une vérification systématique évite les mauvaises surprises après le démarrage.</p>

      <h2 id="configuration-ia" class="mt-12">Configuration IA</h2>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li>Au moins un provider IA est configuré et testé avec succès.</li>
        <li>Les agents IA sont assignés aux providers appropriés.</li>
        <li>Le provider par défaut du projet est défini.</li>
        <li>Les clés API sont stockées de manière sécurisée (chiffrées).</li>
        <li>Un test de génération a été effectué avec succès.</li>
      </ul>

      <h2 id="equipe-et-permissions" class="mt-12">Équipe et permissions</h2>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li>Les rôles des membres de l'équipe sont correctement définis.</li>
        <li>Les membres non autorisés n'ont pas accès aux paramètres sensibles.</li>
        <li>Le owner du projet est bien défini.</li>
        <li>Chaque membre a reçu une notification d'invitation.</li>
      </ul>

      <h2 id="contenu-et-strategie" class="mt-12">Contenu et stratégie</h2>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li>La stratégie éditoriale (audience, ton) est renseignée dans les paramètres.</li>
        <li>Les callouts éditoriaux sont configurés.</li>
        <li>Les catégories d'articles sont créées.</li>
        <li>Le pipeline est configuré si vous utilisez la génération automatique.</li>
      </ul>

      <h2 id="derniers-controles" class="mt-12">Derniers contrôles</h2>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li>Le domaine du projet est correctement renseigné.</li>
        <li>Le snippet est installé sur le site public et fonctionne.</li>
        <li>Un premier événement de tracking a bien été reçu.</li>
        <li>Le dashboard Performance affiche des données.</li>
      </ul>
    `,
  },
  {
    id: 'articles',
    label: 'Articles et éditeur',
    icon: FileText,
    sections: [
      { id: 'vue-ensemble', label: "Vue d'ensemble", depth: 2 },
      { id: 'flux-travail-editorial', label: 'Flux de travail éditorial', depth: 2 },
      { id: 'generation-articles', label: 'Génération d\'articles', depth: 2 },
      { id: 'editeur-riche', label: 'Éditeur riche', depth: 2 },
      { id: 'gestion-medias', label: 'Gestion des médias', depth: 2 },
      { id: 'callouts-editoriaux', label: 'Callouts éditoriaux', depth: 2 },
      { id: 'bonnes-pratiques', label: 'Bonnes pratiques', depth: 2 },
    ],
    content: `
      <h2 id="vue-ensemble">Vue d'ensemble</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">L'éditeur centralise la rédaction, les médias, les commentaires, les versions, les rapports SEO et la préparation de publication. C'est le cœur opérationnel du studio.</p>

      <h2 id="flux-travail-editorial" class="mt-12">Flux de travail éditorial</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Un article peut passer par plusieurs statuts : idée proposée, prioritaire, en rédaction, brouillon prêt, à relire, prêt, programmé, publié ou archivé. Le kanban et le calendrier offrent une vue d'ensemble du workflow.</p>

      <h3 id="statuts-detailles" class="mt-8">Statuts détaillés</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Chaque statut correspond à une étape du cycle de production :</p>
      <ul class="mt-2 space-y-1 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li><strong class="text-primary">Idée proposée</strong> — Une suggestion d'article en attente d'approbation.</li>
        <li><strong class="text-primary">Prioritaire</strong> — L'idée a été validée et passe en production.</li>
        <li><strong class="text-primary">En rédaction</strong> — L'article est en cours d'écriture.</li>
        <li><strong class="text-primary">Brouillon prêt</strong> — La rédaction est terminée, en attente de relecture.</li>
        <li><strong class="text-primary">À relire</strong> — Une relecture est demandée à un membre de l'équipe.</li>
        <li><strong class="text-primary">Prêt</strong> — L'article est validé, peut être programmé ou publié.</li>
        <li><strong class="text-primary">Programmé</strong> — Publication automatique à une date définie.</li>
        <li><strong class="text-primary">Publié</strong> — Visible sur le site public.</li>
        <li><strong class="text-primary">Archivé</strong> — Retiré de la production mais conservé.</li>
      </ul>

      <h2 id="generation-articles" class="mt-12">Génération d'articles</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">La page Générer permet de lancer la production d'articles via le pipeline IA. Vous pouvez choisir le nombre d'articles, la catégorie et laisser le système produire un brouillon complet avec SEO, médias et callouts.</p>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Les articles générés sont toujours des brouillons. La validation humaine et la relecture sont obligatoires avant publication.</p>

      <h2 id="editeur-riche" class="mt-12">Éditeur riche</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">L'éditeur propose une interface de rédaction avec mise en forme, insertion d'images, de callouts et de blocs de contenu. Le panneau SEO intégré permet de vérifier et d'optimiser chaque article avant publication.</p>

      <h2 id="gestion-medias" class="mt-12">Gestion des médias</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">La médiathèque du projet permet d'importer et d'organiser les images, vidéos et autres fichiers. Les médias peuvent être insérés directement dans l'éditeur.</p>

      <h2 id="callouts-editoriaux" class="mt-12">Callouts éditoriaux</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Les callouts sont des encadrés de contenu qui peuvent être insérés dans les articles : conseils, rappels, mises en garde ou informations clés. Ils sont configurables dans les paramètres du projet et peuvent être réutilisés.</p>

      <h2 id="bonnes-pratiques" class="mt-12">Bonnes pratiques</h2>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li>Relisez toujours un article généré avant publication.</li>
        <li>Utilisez le panneau SEO pour vérifier les scores avant de publier.</li>
        <li>Programmez les articles non urgents pour éviter les publications groupées.</li>
        <li>Archivez les articles obsolètes plutôt que de les supprimer.</li>
      </ul>
    `,
  },
  {
    id: 'seo',
    label: 'SEO et rapports',
    icon: TrendingUp,
    sections: [
      { id: 'seo-integre', label: 'SEO intégré', depth: 2 },
      { id: 'scores-editoriaux', label: 'Scores éditoriaux', depth: 2 },
      { id: 'rapport-seo', label: 'Rapport SEO', depth: 2 },
      { id: 'optimisations', label: 'Page Optimisations', depth: 2 },
      { id: 'expert-seo', label: 'Expert SEO', depth: 2 },
      { id: 'workflow-seo', label: 'Workflow SEO', depth: 2 },
      { id: 'bonnes-pratiques-seo', label: 'Bonnes pratiques SEO', depth: 2 },
    ],
    content: `
      <h2 id="seo-integre">SEO intégré</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le SEO est intégré à chaque étape de la production éditoriale : de la suggestion de mot-clé à la révision finale. Chaque article bénéficie d'une analyse automatisée avant publication.</p>

      <h2 id="scores-editoriaux" class="mt-12">Scores éditoriaux</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Chaque article peut afficher sept scores. Ils ne remplacent pas la relecture humaine : ils servent à prioriser les corrections avant validation.</p>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li><strong class="text-primary">Global</strong> — Synthèse pondérée utilisée comme signal de validation.</li>
        <li><strong class="text-primary">SEO</strong> — Optimisation pour les moteurs de recherche.</li>
        <li><strong class="text-primary">Qualité</strong> — Pertinence, profondeur et valeur ajoutée du contenu.</li>
        <li><strong class="text-primary">Lisibilité</strong> — Clarté et fluidité du texte.</li>
        <li><strong class="text-primary">Originalité</strong> — Signal issu du rapport d'originalité ; il peut être heuristique selon le provider disponible.</li>
        <li><strong class="text-primary">GEO</strong> — Optimisation pour les réponses génératives et les moteurs assistés par IA.</li>
        <li><strong class="text-primary">EEAT</strong> — Expertise, expérience, autorité et confiance.</li>
      </ul>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Ces scores sont visibles dans l'éditeur, les listes d'articles, la validation, la performance et les recommandations. Une donnée absente est affichée avec <code class="text-accent">—</code> plutôt qu'une valeur inventée.</p>

      <h2 id="rapport-seo" class="mt-12">Rapport SEO</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Depuis l'éditeur, le panneau SEO affiche une analyse détaillée pour chaque article : mots-clés détectés, meta description, structure des titres, liens internes, optimisation des images, et checklist de publication.</p>

      <h2 id="optimisations" class="mt-12">Page Optimisations</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">La page Optimisations liste les actions recommandées pour améliorer le référencement de chaque article : mise à jour de contenu, amélioration du titre, ajout de liens internes, optimisation de la meta description. Chaque recommandation peut être traitée directement depuis la liste.</p>

      <h2 id="expert-seo" class="mt-12">Expert SEO</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">L'expert SEO est un agent IA spécialisé dans l'analyse et l'optimisation du référencement. Il examine chaque article et produit des recommandations exploitables. Vous pouvez l'invoquer manuellement depuis l'éditeur pour une analyse ciblée.</p>

      <h2 id="workflow-seo" class="mt-12">Workflow SEO</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le workflow SEO est une séquence automatisée qui applique plusieurs passes d'optimisation : analyse initiale, suggestions d'amélioration, vérification de conformité, et rapport final. Il peut être intégré au pipeline de production.</p>

      <h2 id="bonnes-pratiques-seo" class="mt-12">Bonnes pratiques SEO</h2>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li>Rédigez une meta description unique et pertinente pour chaque article.</li>
        <li>Utilisez une hiérarchie de titres logique (H1, H2, H3).</li>
        <li>Ajoutez des liens internes vers d'autres articles du même projet.</li>
        <li>Optimisez les images avec des attributs alt descriptifs.</li>
        <li>Vérifiez les scores SEO avant chaque publication.</li>
      </ul>
    `,
  },
  {
    id: 'pipeline',
    label: 'Pipeline automatique',
    icon: RefreshCw,
    sections: [
      { id: 'a-quoi-sert-le-pipeline', label: 'À quoi sert le pipeline', depth: 2 },
      { id: 'configuration', label: 'Configuration', depth: 2 },
      { id: 'fonctionnement', label: 'Fonctionnement', depth: 2 },
      { id: 'modes-disponibles', label: 'Modes disponibles', depth: 2 },
      { id: 'planification', label: 'Planification', depth: 2 },
      { id: 'garde-fous', label: 'Garde-fous et validation humaine', depth: 2 },
      { id: 'erreurs-frequentes', label: 'Erreurs fréquentes', depth: 2 },
      { id: 'bonnes-pratiques-pipeline', label: 'Bonnes pratiques', depth: 2 },
    ],
    content: `
      <h2 id="a-quoi-sert-le-pipeline">À quoi sert le pipeline</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le pipeline automatique prépare des contenus selon une planification définie. Il accélère la production sans publier automatiquement. C'est un outil conçu pour les équipes qui ont besoin d'un flux régulier d'articles sans intervention manuelle à chaque étape.</p>

      <h2 id="configuration" class="mt-12">Configuration</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Dans Paramètres / Pipeline, vous pouvez activer ou désactiver le pipeline, choisir les jours actifs de la semaine, définir l'heure de lancement quotidienne, et configurer le nombre d'articles à générer par semaine.</p>

      <h2 id="fonctionnement" class="mt-12">Fonctionnement</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le pipeline exécute séquentiellement les agents IA : recherche de mots-clés, génération d'idées, rédaction, optimisation SEO et révision éditoriale. Chaque étape produit un résultat qui nourrit la suivante.</p>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Les articles produits sont stockés comme brouillons et doivent être relus et validés avant publication.</p>

      <h2 id="modes-disponibles" class="mt-12">Modes disponibles</h2>

      <h3 id="manuel" class="mt-8">Mode manuel</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Lancez une exécution à la demande depuis la page de configuration. Utile pour tester la configuration ou produire un lot d'articles ponctuel.</p>

      <h3 id="programme" class="mt-8">Mode programmé</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Le pipeline s'exécute automatiquement selon les jours et l'heure définis. Idéal pour maintenir un rythme de publication régulier sans intervention.</p>

      <h2 id="planification" class="mt-12">Planification</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Définissez les jours de la semaine où le pipeline doit s'exécuter et l'heure de déclenchement. Par exemple, du lundi au vendredi à 8h00. Le pipeline respecte cette planification et produit un nombre défini d'articles par semaine.</p>

      <h2 id="garde-fous" class="mt-12">Garde-fous et validation humaine</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le pipeline n'a pas le droit de publier directement. Tous les articles produits sont placés dans le workflow éditorial en tant que brouillons. Un humain doit relire, valider et publier chaque article. Des limites de génération empêchent la surproduction involontaire.</p>

      <h2 id="erreurs-frequentes" class="mt-12">Erreurs fréquentes</h2>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li><strong class="text-primary">Pipeline inactif</strong> — Vérifiez que le pipeline est activé et que les jours de fonctionnement sont définis.</li>
        <li><strong class="text-primary">Aucun provider configuré</strong> — Le pipeline nécessite au moins un provider IA fonctionnel.</li>
        <li><strong class="text-primary">Génération trop ambitieuse</strong> — Commencez avec un faible nombre d'articles par semaine et ajustez progressivement.</li>
      </ul>

      <h2 id="bonnes-pratiques-pipeline" class="mt-12">Bonnes pratiques</h2>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li>Testez le pipeline en mode manuel avant d'activer la planification.</li>
        <li>Surveillez les premiers lots pour vérifier la qualité de la génération.</li>
        <li>Ajustez les prompts des agents si les résultats ne correspondent pas à votre ligne éditoriale.</li>
        <li>Prévoyez du temps de relecture proportionnel au nombre d'articles générés.</li>
      </ul>
    `,
  },
  {
    id: 'providers',
    label: 'Providers IA',
    icon: Cpu,
    sections: [
      { id: 'quest-ce-quun-provider', label: "Qu'est-ce qu'un provider", depth: 2 },
      { id: 'ajouter-un-provider', label: 'Ajouter un provider', depth: 2 },
      { id: 'types-supportes', label: 'Types supportés', depth: 2 },
      { id: 'securite-cles', label: 'Sécurité des clés', depth: 2 },
      { id: 'tester-connexion', label: 'Tester la connexion', depth: 2 },
      { id: 'provider-par-defaut', label: 'Provider par défaut', depth: 2 },
      { id: 'erreurs-frequentes', label: 'Erreurs fréquentes', depth: 2 },
    ],
    content: `
      <h2 id="quest-ce-quun-provider">Qu'est-ce qu'un provider</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Les providers connectent le projet à des services d'IA externes : Google Gemini, OpenAI, OpenRouter, Ollama ou tout service compatible OpenAI. Sans provider configuré, les agents IA ne peuvent pas fonctionner.</p>

      <h2 id="ajouter-un-provider" class="mt-12">Ajouter un provider</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Dans Paramètres / Providers, vous pouvez ajouter un provider par type. Pour chaque provider, choisissez le type, donnez-lui un label pour l'identifier, saisissez la clé API, configurez le modèle et l'URL de base si nécessaire, testez la connexion pour valider les paramètres, et définissez le provider par défaut du projet.</p>

      <h2 id="types-supportes" class="mt-12">Types supportés</h2>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li><strong class="text-primary">Gemini</strong> — Google Gemini (gemini-2.5-flash par défaut).</li>
        <li><strong class="text-primary">OpenAI</strong> — Modèles GPT (gpt-4o-mini par défaut).</li>
        <li><strong class="text-primary">OpenRouter</strong> — Accès à de multiples modèles via une API unifiée.</li>
        <li><strong class="text-primary">Ollama</strong> — Modèles en local (qwen3:14b par défaut).</li>
        <li><strong class="text-primary">Custom</strong> — Tout service compatible avec l'API OpenAI.</li>
      </ul>

      <h3 id="openrouter" class="mt-8">OpenRouter</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">OpenRouter donne accès à une centaine de modèles via une API unique. Vous pouvez changer de modèle sans modifier la configuration du provider.</p>

      <h3 id="ollama" class="mt-8">Ollama</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Ollama permet d'exécuter des modèles en local. Aucune clé API n'est nécessaire. L'URL de base est généralement <code class="text-accent">http://localhost:11434</code>.</p>

      <h2 id="securite-cles" class="mt-12">Sécurité des clés</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Les clés API sont chiffrées avant stockage et ne sont jamais renvoyées en clair au frontend — seulement un indicateur booléen indiquant si une clé est configurée. Détails du chiffrement dans le chapitre <em>Sécurité</em>.</p>

      <h2 id="tester-connexion" class="mt-12">Tester la connexion</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le bouton Tester envoie une requête de validation au provider avec la clé et le modèle configurés. Si la réponse est positive, le provider est marqué comme fonctionnel. En cas d'erreur, le message d'erreur du service s'affiche pour faciliter le diagnostic.</p>

      <h2 id="provider-par-defaut" class="mt-12">Provider par défaut</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le provider par défaut est utilisé par les agents qui n'ont pas d'assignation spécifique. Un seul provider peut être le défaut du projet. Si aucun provider par défaut n'est défini, le système tente d'utiliser la variable d'environnement globale.</p>

      <h2 id="erreurs-frequentes" class="mt-12">Erreurs fréquentes</h2>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li><strong class="text-primary">Clé API invalide</strong> — Vérifiez que la clé est correcte et active sur le service du provider.</li>
        <li><strong class="text-primary">URL de base incorrecte</strong> — Pour Ollama, vérifiez que le service est bien accessible à l'URL configurée.</li>
        <li><strong class="text-primary">Modèle inexistant</strong> — Certains modèles peuvent ne pas être disponibles selon le provider.</li>
        <li><strong class="text-primary">Provider sans clé</strong> — Un provider sans clé ne peut pas être utilisé pour la génération.</li>
      </ul>
    `,
  },
  {
    id: 'agents',
    label: 'Agents IA',
    icon: Bot,
    sections: [
      { id: 'quest-ce-quun-agent', label: "Qu'est-ce qu'un agent", depth: 2 },
      { id: 'categories-agents', label: 'Catégories d\'agents', depth: 2 },
      { id: 'assignation', label: 'Assignation aux providers', depth: 2 },
      { id: 'activation', label: 'Activation et désactivation', depth: 2 },
      { id: 'resolution-fournisseur', label: 'Ordre de résolution du fournisseur', depth: 2 },
      { id: 'bonnes-pratiques', label: 'Bonnes pratiques', depth: 2 },
    ],
    content: `
      <h2 id="quest-ce-quun-agent">Qu'est-ce qu'un agent</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Les agents sont des modules spécialisés qui exécutent une tâche précise dans le flux de production. Chaque agent a un rôle spécifique, un prompt dédié et peut être assigné à un provider IA. Le système compte 62 agents répartis en 4 catégories.</p>

      <h2 id="categories-agents" class="mt-12">Catégories d'agents</h2>

      <h3 id="recherche" class="mt-8">Recherche (14 agents)</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Analyse de mots-clés, tendances, concurrence et sources. Ces agents préparent le terrain éditorial en identifiant les sujets porteurs et les opportunités de contenu.</p>

      <h3 id="strategie" class="mt-8">Stratégie (16 agents)</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Idéation, calibrage, planification et persona. Ces agents transforment les données de recherche en une stratégie de contenu cohérente.</p>

      <h3 id="creation" class="mt-8">Création (15 agents)</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Rédaction, reformulation, FAQ, callouts et images. Ces agents produisent le contenu lui-même à partir des directives stratégiques.</p>

      <h3 id="revision" class="mt-8">Révision (17 agents)</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Relecture, SEO, qualité, EEAT et vérification. Ces agents contrôlent et améliorent le contenu avant publication.</p>

      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Chaque agent affiche un statut : <strong class="text-primary">actif</strong> (utilise un provider IA), <strong class="text-primary">heuristique</strong> (règles internes, sans LLM — aucun provider ne lui est applicable) ou <strong class="text-primary">partiel</strong> (dépend d'un service externe complémentaire, ex. recherche web ou tendances).</p>

      <h2 id="assignation" class="mt-12">Assignation aux providers</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Dans Paramètres / Agents, vous pouvez assigner un provider à chaque agent. Par exemple, utiliser Gemini pour la rédaction et OpenAI pour l'analyse SEO. Chaque agent peut avoir un provider différent selon ses besoins spécifiques.</p>

      <h2 id="activation" class="mt-12">Activation et désactivation</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Les agents peuvent être désactivés individuellement. Un agent désactivé est ignoré par le routage IA et n'est pas exécuté. Cela permet de désactiver temporairement certaines fonctionnalités sans supprimer la configuration.</p>

      <h2 id="resolution-fournisseur" class="mt-12">Ordre de résolution du fournisseur</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Quand un agent est invoqué, le système détermine quel provider utiliser dans cet ordre :</p>
      <ol class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-decimal pl-6">
        <li>Assignation spécifique du projet (si configurée).</li>
        <li>Provider par défaut du projet.</li>
        <li>Variable d'environnement globale.</li>
      </ol>

      <h2 id="bonnes-pratiques" class="mt-12">Bonnes pratiques</h2>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li>Utilisez des providers différents pour les tâches de création et de révision.</li>
        <li>Désactivez les agents non utilisés pour réduire la consommation d'API.</li>
        <li>Testez la génération avec un seul article avant de passer à la production en masse.</li>
        <li>Vérifiez que chaque agent assigné à un provider a bien un provider fonctionnel.</li>
      </ul>
    `,
  },
  {
    id: 'permissions',
    label: 'Accès et permissions',
    icon: ShieldCheck,
    sections: [
      { id: 'roles-projet', label: 'Rôles projet', depth: 2 },
      { id: 'admin-plateforme', label: 'Administrateur plateforme', depth: 2 },
      { id: 'providers-agents-acces', label: 'Providers et agents : qui peut accéder', depth: 2 },
      { id: 'bonnes-pratiques', label: 'Bonnes pratiques', depth: 2 },
    ],
    content: `
      <h2 id="roles-projet">Rôles projet</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Chaque projet définit ses propres rôles pour les membres :</p>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li><strong class="text-primary">Owner</strong> — Peut gérer les providers, agents, membres, paramètres. Peut supprimer le projet. Ne peut ni être réassigné ni retiré.</li>
        <li><strong class="text-primary">Admin</strong> — Peut gérer les providers, agents, membres, paramètres. Ne peut pas supprimer le projet.</li>
        <li><strong class="text-primary">Editor</strong> — Peut créer, modifier, générer, publier des articles, et gérer catégories/callouts/pipeline. Accès limité aux paramètres.</li>
        <li><strong class="text-primary">Designer</strong> — Peut créer et modifier des articles, et gérer la médiathèque.</li>
        <li><strong class="text-primary">Viewer</strong> — Accès en lecture seule.</li>
      </ul>

      <h2 id="admin-plateforme" class="mt-12">Administrateur plateforme</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le drapeau <strong class="text-primary">is_staff</strong> sur un compte utilisateur donne uniquement accès à la gestion du catalogue de plateformes IA partagé (providers disponibles pour tous les projets) — il ne donne <strong class="text-primary">aucun accès</strong> aux projets des autres utilisateurs. Chaque projet reste strictement cloisonné : seuls les membres explicitement ajoutés (owner, admin, editor, designer, viewer) y ont accès. is_staff est attribué automatiquement au tout premier utilisateur créé sur l'instance, puis géré manuellement.</p>

      <h2 id="providers-agents-acces" class="mt-12">Providers et agents : qui peut accéder</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">La configuration des providers et agents d'un projet est réservée au owner et aux admins de ce projet. Les editors, designers et viewers voient un message "Admin access required" s'ils tentent d'accéder à ces pages. Les comptes <code class="text-accent">is_staff</code> voient en plus le catalogue de plateformes IA partagé, mais n'ont pas d'accès automatique aux projets des autres.</p>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Cette restriction garantit que les clés API et la configuration IA restent sous le contrôle des responsables du projet.</p>

      <h2 id="bonnes-pratiques" class="mt-12">Bonnes pratiques</h2>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li>Attribuez le rôle Owner uniquement aux personnes responsables du projet.</li>
        <li>Limitez le nombre d'admins pour garder le contrôle des paramètres sensibles.</li>
        <li>Révisez régulièrement les accès des membres quand l'équipe évolue.</li>
        <li>Le rôle Viewer est utile pour les parties prenantes qui n'ont pas besoin d'éditer.</li>
      </ul>
    `,
  },
  {
    id: 'collaboration',
    label: 'Collaboration',
    icon: Users,
    sections: [
      { id: 'travail-equipe', label: 'Travail en équipe', depth: 2 },
      { id: 'commentaires', label: 'Commentaires', depth: 2 },
      { id: 'kanban', label: 'Suivi du workflow', depth: 2 },
      { id: 'notifications', label: 'Notifications', depth: 2 },
      { id: 'calendrier-editorial', label: 'Calendrier éditorial', depth: 2 },
      { id: 'bonnes-pratiques-co', label: 'Bonnes pratiques', depth: 2 },
    ],
    content: `
      <h2 id="travail-equipe">Travail en équipe</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Ideas Studio est conçu pour le travail en équipe. Plusieurs collaborateurs peuvent travailler simultanément sur le même projet, chacun avec son rôle et ses permissions.</p>

      <h2 id="commentaires" class="mt-12">Commentaires</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Chaque article dispose d'un système de commentaires pour faciliter les échanges entre éditeurs, relecteurs et validateurs. Les commentaires sont horodatés et associés à leur auteur.</p>

      <h2 id="kanban" class="mt-12">Suivi du workflow</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">La page Production offre une vue d'ensemble de l'avancement des articles à travers leurs statuts (idée, en rédaction, brouillon prêt, prêt, programmé, publié…). Un tableau kanban à colonnes personnalisables et glisser-déposer est prévu dans l'API mais n'est pas encore branché à l'interface.</p>

      <h2 id="notifications" class="mt-12">Notifications</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Les notifications informent l'équipe des changements de statut, des commentaires, des résultats de génération et des actions requises. Chaque membre reçoit les notifications pertinentes selon son rôle.</p>

      <h2 id="calendrier-editorial" class="mt-12">Calendrier éditorial</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le calendrier affiche les articles programmés sur une vue mensuelle. Il permet de visualiser la répartition des publications et d'ajuster la planification.</p>

      <h2 id="bonnes-pratiques-co" class="mt-12">Bonnes pratiques</h2>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li>Utilisez les commentaires pour discuter des modifications, pas les canaux externes.</li>
        <li>Mettez à jour le statut des articles dans le kanban pour que l'équipe suive l'avancement.</li>
        <li>Consultez le calendrier pour éviter les publications groupées.</li>
        <li>Définissez des relecteurs attitrés pour chaque article.</li>
      </ul>
    `,
  },
  {
    id: 'api',
    label: 'API et Webhooks',
    icon: Code,
    sections: [
      { id: 'api-publique', label: 'API publique', depth: 2 },
      { id: 'swagger-openapi', label: 'Swagger et OpenAPI', depth: 2 },
      { id: 'endpoints-disponibles', label: 'Endpoints disponibles', depth: 2 },
      { id: 'webhooks-evenements', label: 'Webhooks et événements', depth: 2 },
      { id: 'securite-webhooks', label: 'Sécurité des webhooks', depth: 2 },
      { id: 'exemples-utilisation', label: 'Exemples d\'utilisation', depth: 2 },
    ],
    content: `
      <h2 id="api-publique">API publique</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Les articles publiés sont accessibles via une API REST publique. Cette API ne nécessite pas d'authentification et peut être utilisée par le site public pour afficher les articles.</p>

      <h2 id="swagger-openapi" class="mt-12">Swagger, ReDoc et OpenAPI</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le backend FastAPI expose automatiquement Swagger UI, ReDoc et le schéma OpenAPI JSON. Les liens techniques sont disponibles en haut de cette page et utilisent l'URL backend configurée par <code class="text-accent">VITE_API_URL</code>. Si cette variable n'est pas définie, l'interface suppose le backend local de développement.</p>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Les routes privées nécessitent un token JWT. Les routes publiques sont regroupées sous <code class="text-accent">/api/public</code>, et le tracking utilise des endpoints dédiés qui ne doivent pas exposer de secrets.</p>

      <h2 id="endpoints-disponibles" class="mt-12">Endpoints disponibles</h2>

      <h3 id="articles-publics" class="mt-8">Articles publics</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary"><code class="text-accent">GET /api/public/projects/{id}/articles</code> — Récupère la liste des articles publiés d'un projet.</p>

      <h3 id="detail-article" class="mt-8">Détail d'un article</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary"><code class="text-accent">GET /api/public/projects/{id}/articles/{'{slug}'}</code> — Récupère le détail d'un article par son slug.</p>

      <h2 id="webhooks-evenements" class="mt-12">Webhooks et événements</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Les webhooks sont conçus pour déclencher des appels HTTP vers vos services lors d'événements comme la création ou la publication d'un article, la fin d'une génération, ou l'exécution du pipeline. <strong class="text-primary">Le déclenchement automatique n'est pas encore implémenté</strong> : seul l'appel de test manuel envoie effectivement une requête aujourd'hui. La création, la modification et la suppression d'un webhook fonctionnent via l'API ; il n'y a pas encore de page dédiée dans l'interface.</p>

      <h2 id="securite-webhooks" class="mt-12">Sécurité des webhooks</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Chaque webhook est configuré avec un secret qui signe les requêtes sortantes (header <code class="text-accent">X-IdeasStudio-Signature</code>, HMAC-SHA256). Votre service peut vérifier cette signature pour s'assurer que la requête provient bien du studio. L'URL du webhook doit être en HTTPS ; les IP privées/locales sont refusées.</p>

      <h2 id="exemples-utilisation" class="mt-12">Exemples d'utilisation prévus</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Une fois le déclenchement automatique branché, les webhooks permettront par exemple de notifier Slack ou Discord à la publication d'un article, de déclencher un rebuild de site statique, ou de synchroniser les métadonnées avec un CMS externe.</p>
    `,
  },
  {
    id: 'tracking',
    label: 'Analytics et tracking',
    icon: BarChart2,
    sections: [
      { id: 'systeme-tracking', label: 'Le système de tracking', depth: 2 },
      { id: 'dashboard-performance', label: 'Dashboard Analytics', depth: 2 },
      { id: 'google-search-console', label: 'Google Search Console', depth: 2 },
      { id: 'periodes', label: 'Périodes disponibles', depth: 2 },
      { id: 'diagnostic-donnees', label: 'Diagnostic des données absentes', depth: 2 },
      { id: 'limites', label: 'Limites du tracking', depth: 2 },
    ],
    content: `
      <h2 id="systeme-tracking">Le système de tracking</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le système de tracking collecte et agrège les visites du site public pour fournir des analytics exploitables. Il repose sur le snippet JavaScript installé sur le site (voir <em>Connecter un site</em>), qui envoie les événements au studio.</p>

      <h2 id="dashboard-performance" class="mt-12">Dashboard Analytics</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Une page Analytics unique regroupe les statistiques internes (vues totales, tendance par canal — direct, organique, referral, social —, sources, pays, appareils, score SEO moyen, top articles) et, si un compte Google Analytics 4 est connecté au projet, un second bloc de données GA4 (sessions, durée moyenne, taux de rebond, pages les plus vues). Export des données disponible en JSON ou PDF.</p>

      <h2 id="google-search-console" class="mt-12">Google Search Console</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">L'intégration Google Search Console visualisera les mots-clés organiques et les positions dans les résultats de recherche. <strong class="text-primary">Statut actuel : non disponible</strong> — la configuration OAuth Google n'est pas encore implémentée, les endpoints renvoient systématiquement un statut "non connecté".</p>

      <h2 id="periodes" class="mt-12">Périodes disponibles</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Le dashboard accepte un nombre de jours au choix, une période prédéfinie (jour, semaine, mois, trimestre, semestre, année) ou une plage de dates personnalisée. Par défaut, les 30 derniers jours sont affichés.</p>

      <h2 id="diagnostic-donnees" class="mt-12">Diagnostic des données absentes</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Si le dashboard n'affiche pas de données :</p>
      <ol class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-decimal pl-6">
        <li>Vérifiez que le domaine du projet est correctement renseigné dans Paramètres / Général.</li>
        <li>Vérifiez que le snippet est installé sur le site public.</li>
        <li>Visitez une page de votre site pour générer un événement de test.</li>
        <li>Rafraîchissez le dashboard avec la période appropriée.</li>
        <li>Si le message "Snippet connecté, aucune donnée" persiste, le site n'a pas reçu de visite dans la période sélectionnée.</li>
      </ol>

      <h2 id="limites" class="mt-12">Limites du tracking</h2>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li>Le tracking ne fonctionne que si le snippet est correctement installé.</li>
        <li>Les bloqueurs de publicité peuvent empêcher le snippet de s'exécuter.</li>
        <li>Les données de navigation ne sont pas disponibles en temps réel (latence de quelques minutes).</li>
      </ul>
    `,
  },
  {
    id: 'security',
    label: 'Sécurité',
    icon: Lock,
    sections: [
      { id: 'cles-api', label: 'Clés API', depth: 2 },
      { id: 'authentification', label: 'Authentification', depth: 2 },
      { id: 'chiffrement', label: 'Chiffrement des données', depth: 2 },
      { id: 'bonnes-pratiques', label: 'Bonnes pratiques', depth: 2 },
      { id: 'a-retenir', label: 'À retenir', depth: 2 },
    ],
    content: `
      <h2 id="cles-api">Clés API</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Les clés API sont chiffrées avec l'algorithme AES (Fernet) avant stockage en base de données. Le frontend ne reçoit jamais la clé en clair. Les clés ne doivent jamais être commitées dans Git, partagées par email, ou exposées dans une documentation publique.</p>

      <h2 id="authentification" class="mt-12">Authentification</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">L'authentification utilise des tokens JWT (JSON Web Tokens) avec une expiration configurable. Le token est stocké dans le localStorage du navigateur et envoyé via l'en-tête Authorization pour chaque requête API.</p>

      <h3 id="expiration-token" class="mt-8">Expiration des tokens</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Le token expire après une durée configurable. Une fois expiré, l'utilisateur doit se reconnecter. Cette durée peut être ajustée dans la configuration du serveur.</p>

      <h3 id="protection-csrf" class="mt-8">Protection CSRF</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Les requêtes API sensibles sont protégées contre les attaques CSRF. Le token JWT sert également de mécanisme anti-CSRF.</p>

      <h2 id="chiffrement" class="mt-12">Chiffrement des données</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">En plus des clés API, certaines données sensibles peuvent être chiffrées au repos. Le chiffrement utilise la bibliothèque cryptography avec l'algorithme Fernet, qui implémente AES 128 en mode CBC.</p>

      <h2 id="bonnes-pratiques" class="mt-12">Bonnes pratiques</h2>
      <ul class="mt-3 space-y-2 text-[15px] leading-relaxed text-secondary list-disc pl-6">
        <li>Utilisez des mots de passe forts pour chaque compte.</li>
        <li>Révoquez immédiatement une clé API si elle a été exposée.</li>
        <li>Limitez la gestion des providers et agents aux owners et admins du projet.</li>
        <li>Utilisez les variables d'environnement de l'hébergeur pour les clés globales.</li>
        <li>Activez HTTPS sur votre site public pour sécuriser les données de tracking.</li>
      </ul>

      <h2 id="a-retenir" class="mt-12">À retenir</h2>
      <p class="mt-3 text-[15px] leading-relaxed text-secondary">Ideas Studio applique le principe du moindre privilège : chaque utilisateur et chaque service n'a accès qu'aux ressources nécessaires à son fonctionnement. Les clés API ne sont jamais exposées au frontend et le chiffrement protège les données sensibles au repos.</p>
    `,
  },
  {
    id: 'faq',
    label: 'FAQ',
    icon: HelpCircle,
    sections: [
      { id: 'generale', label: 'Générale', depth: 2 },
      { id: 'technique', label: 'Technique', depth: 2 },
      { id: 'utilisation', label: 'Utilisation', depth: 2 },
    ],
    content: `
      <h2 id="generale">Générale</h2>

      <h3 id="quels-sont-les-pre-requis" class="mt-8">Quels sont les prérequis techniques ?</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Un site public, une clé API d'un service d'IA et un compte Ideas Studio. Aucune compétence technique avancée n'est nécessaire pour l'installation de base.</p>

      <h2 id="technique" class="mt-12">Technique</h2>

      <h3 id="snippet-donnees" class="mt-8">Que voit-on si le snippet ne reçoit aucune donnée ?</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Les dashboards restent visibles avec des métriques à zéro. La page affiche "Snippet non configuré" ou "Snippet connecté, aucune donnée reçue pour cette période" selon l'état du domaine.</p>

      <h3 id="pipeline-publication-auto" class="mt-8">Le pipeline publie-t-il automatiquement ?</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Non. Le pipeline prépare des brouillons et les place dans le workflow éditorial. La publication reste une action humaine avec relecture et validation obligatoires.</p>

      <h3 id="comment-tester-gemini" class="mt-8">Comment tester Gemini ?</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Créez une clé API sur <a href="https://aistudio.google.com/apikey" class="text-accent hover:underline" target="_blank" rel="noopener noreferrer">Google AI Studio</a>, ajoutez un provider Gemini dans Paramètres / Providers, collez la clé, et cliquez sur Tester. Si la connexion est réussie, le provider est prêt pour la génération.</p>

      <h3 id="acces-providers-agents" class="mt-8">Qui peut gérer les providers et agents ?</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Le owner du projet et les admins de ce projet. Les editors, designers et viewers n'ont pas accès à ces pages de configuration. Les comptes <code class="text-accent">is_staff</code> voient en plus le catalogue de plateformes IA partagé, mais n'ont pas d'accès automatique aux projets des autres utilisateurs.</p>

      <h3 id="diagnostic-donnees" class="mt-8">Comment diagnostiquer des données absentes dans les dashboards ?</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Vérifiez que le domaine est renseigné (Paramètres / Général), que le snippet est installé, et qu'il y a eu des visites dans la période sélectionnée. Utilisez le bouton Rafraîchir pour recharger les données.</p>

      <h2 id="utilisation" class="mt-12">Utilisation</h2>

      <h3 id="preparer-site" class="mt-8">Comment préparer mon site pour la connexion ?</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Votre site public doit pouvoir inclure une balise <code class="text-accent">&lt;script&gt;</code> dans le <code class="text-accent">&lt;head&gt;</code>. Le snippet fonctionne sur tout site HTML, quel que soit le framework ou le CMS utilisé. Aucune dépendance supplémentaire n'est requise.</p>

      <h3 id="plusieurs-sites" class="mt-8">Puis-je connecter plusieurs sites ?</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Oui, chaque projet a son propre domaine et son propre snippet. Vous pouvez créer autant de projets que nécessaire.</p>

      <h3 id="migration" class="mt-8">Puis-je migrer mon projet vers un autre serveur ?</h3>
      <p class="mt-2 text-[15px] leading-relaxed text-secondary">Oui, exportez les données de votre projet et importez-les sur le nouveau serveur. Le snippet devra être mis à jour si l'URL du studio change.</p>
    `,
  },
]

function extractOutline(sections: { id: string; label: string; depth: number }[]) {
  return sections
}

function normalizeMarkdownText(value: string) {
  return value.replace(/\s+/g, ' ').trim()
}

function inlineMarkdown(node: ChildNode): string {
  if (node.nodeType === Node.TEXT_NODE) return node.textContent ?? ''
  if (!(node instanceof HTMLElement)) return ''

  const text = Array.from(node.childNodes).map(inlineMarkdown).join('')
  const normalized = normalizeMarkdownText(text)

  if (node.tagName === 'STRONG') return normalized ? `**${normalized}**` : ''
  if (node.tagName === 'CODE') return normalized ? `\`${normalized}\`` : ''
  if (node.tagName === 'A') {
    const href = node.getAttribute('href')
    return href && normalized ? `[${normalized}](${href})` : normalized
  }
  return text
}

function blockMarkdown(element: Element): string {
  if (!(element instanceof HTMLElement)) return ''
  const text = normalizeMarkdownText(Array.from(element.childNodes).map(inlineMarkdown).join(''))

  if (!text && !['UL', 'OL'].includes(element.tagName)) return ''
  if (element.tagName === 'H2') return `## ${text}`
  if (element.tagName === 'H3') return `### ${text}`
  if (element.tagName === 'P') return text
  if (element.tagName === 'UL') {
    return Array.from(element.children)
      .filter((child) => child.tagName === 'LI')
      .map((child) => `- ${normalizeMarkdownText(Array.from(child.childNodes).map(inlineMarkdown).join(''))}`)
      .join('\n')
  }
  if (element.tagName === 'OL') {
    return Array.from(element.children)
      .filter((child) => child.tagName === 'LI')
      .map((child, index) => `${index + 1}. ${normalizeMarkdownText(Array.from(child.childNodes).map(inlineMarkdown).join(''))}`)
      .join('\n')
  }
  return text
}

function chapterContentToMarkdown(html: string): string {
  const doc = new DOMParser().parseFromString(`<main>${html}</main>`, 'text/html')
  return Array.from(doc.body.firstElementChild?.children ?? [])
    .map(blockMarkdown)
    .filter(Boolean)
    .join('\n\n')
}

function buildDocumentationMarkdown() {
  const exportedAt = new Date().toLocaleString('fr-FR')
  return [
    '# Documentation Ideas Studio',
    '',
    `Export complet généré le ${exportedAt}.`,
    '',
    '## Sommaire',
    '',
    ...CHAPTERS.map((chapter, index) => `${index + 1}. ${chapter.label}`),
    '',
    ...CHAPTERS.flatMap((chapter) => [
      `# ${chapter.label}`,
      '',
      chapterContentToMarkdown(chapter.content),
      '',
    ]),
  ].join('\n')
}

function downloadMarkdown(filename: string, markdown: string) {
  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

interface PaletteItem {
  chapterId: string
  chapterLabel: string
  icon: IconType
  id: string
  label: string
  isChapterRoot?: boolean
}

export default function DocumentationPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [activeChapterId, setActiveChapterId] = useState(CHAPTERS[0]?.id ?? '')
  const [activeSectionId, setActiveSectionId] = useState<string | null>(null)
  const [pendingScrollId, setPendingScrollId] = useState<string | null>(null)
  const [scrollProgress, setScrollProgress] = useState(0)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [paletteQuery, setPaletteQuery] = useState('')
  const [paletteIndex, setPaletteIndex] = useState(0)
  const contentRef = useRef<HTMLDivElement>(null)
  const paletteInputRef = useRef<HTMLInputElement>(null)

  const activeChapter = CHAPTERS.find((c) => c.id === activeChapterId) ?? CHAPTERS[0]
  const activeChapterIndex = CHAPTERS.findIndex((c) => c.id === activeChapterId)
  const prevChapter = activeChapterIndex > 0 ? CHAPTERS[activeChapterIndex - 1] : null
  const nextChapter = activeChapterIndex >= 0 && activeChapterIndex < CHAPTERS.length - 1 ? CHAPTERS[activeChapterIndex + 1] : null

  const outline = activeChapter ? extractOutline(activeChapter.sections) : []
  const swaggerUrl = `${documentationApiUrl}/docs`
  const redocUrl = `${documentationApiUrl}/redoc`
  const openApiUrl = `${documentationApiUrl}/openapi.json`

  function openPalette() {
    setPaletteQuery('')
    setPaletteIndex(0)
    setPaletteOpen(true)
  }

  // Global ⌘K / Ctrl+K shortcut to open the search palette.
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen((v) => {
          if (v) return false
          setPaletteQuery('')
          setPaletteIndex(0)
          return true
        })
      }
      if (e.key === 'Escape') setPaletteOpen(false)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Focus the palette input once it mounts (imperative DOM action, no state update).
  useEffect(() => {
    if (paletteOpen) requestAnimationFrame(() => paletteInputRef.current?.focus())
  }, [paletteOpen])

  // Thin reading-progress bar tied to page scroll.
  useEffect(() => {
    function onScroll() {
      const h = document.documentElement
      const scrollable = h.scrollHeight - h.clientHeight
      setScrollProgress(scrollable > 0 ? (h.scrollTop / scrollable) * 100 : 0)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // Highlight the section currently in view in the right-hand outline: the
  // active heading is the last one whose top has scrolled past the sticky
  // header, defaulting to the first heading of the chapter.
  useEffect(() => {
    const container = contentRef.current
    if (!container) return
    const headings = Array.from(container.querySelectorAll('h2[id], h3[id]')) as HTMLElement[]
    if (headings.length === 0) return

    function updateActiveSection() {
      const offset = 96
      let currentId = headings[0]?.id ?? null
      for (const heading of headings) {
        if (heading.getBoundingClientRect().top - offset <= 0) {
          currentId = heading.id
        } else {
          break
        }
      }
      setActiveSectionId(currentId)
    }

    updateActiveSection()
    window.addEventListener('scroll', updateActiveSection, { passive: true })
    return () => window.removeEventListener('scroll', updateActiveSection)
  }, [activeChapterId])

  // Scroll to a specific heading once its chapter has rendered.
  useEffect(() => {
    if (!pendingScrollId) return
    const targetId = pendingScrollId
    const raf = requestAnimationFrame(() => {
      document.getElementById(targetId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      setPendingScrollId(null)
    })
    return () => cancelAnimationFrame(raf)
  }, [activeChapterId, pendingScrollId])

  function goToChapter(id: string) {
    setActiveChapterId(id)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const searchIndex = useMemo<PaletteItem[]>(
    () =>
      CHAPTERS.flatMap((ch) =>
        ch.sections.map((s) => ({
          chapterId: ch.id,
          chapterLabel: ch.label,
          icon: ch.icon,
          id: s.id,
          label: s.label,
        })),
      ),
    [],
  )

  const paletteResults = useMemo<PaletteItem[]>(() => {
    const q = paletteQuery.trim().toLowerCase()
    if (!q) {
      return CHAPTERS.map((ch) => ({
        chapterId: ch.id,
        chapterLabel: ch.label,
        icon: ch.icon,
        id: ch.sections[0]?.id ?? '',
        label: ch.label,
        isChapterRoot: true,
      }))
    }
    return searchIndex
      .filter((item) => item.label.toLowerCase().includes(q) || item.chapterLabel.toLowerCase().includes(q))
      .slice(0, 20)
  }, [paletteQuery, searchIndex])

  function selectPaletteItem(item: PaletteItem) {
    setPaletteOpen(false)
    setActiveChapterId(item.chapterId)
    setPendingScrollId(item.id)
  }

  function handlePaletteKeyDown(e: ReactKeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setPaletteIndex((i) => Math.min(i + 1, paletteResults.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setPaletteIndex((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const item = paletteResults[paletteIndex]
      if (item) selectPaletteItem(item)
    }
  }

  function handleDownloadMarkdown() {
    downloadMarkdown('ideas-studio-documentation-complete.md', buildDocumentationMarkdown())
  }

  return (
    <div className="min-h-screen bg-bg text-primary">
      {/* Reading progress */}
      <div className="fixed left-0 top-0 z-50 h-[2.5px] bg-accent transition-[width] duration-150" style={{ width: `${scrollProgress}%` }} />

      {/* Topbar */}
      <header className="sticky top-0 z-30 border-b border-border bg-surface/95 backdrop-blur supports-[backdrop-filter]:bg-surface/80">
          <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-5">
          <Link to="/" className="flex items-center gap-2 text-[15px] font-semibold tracking-tight text-primary">
            <img src="/icon.svg" alt="" className="h-7 w-7 rounded-[8px]" />
            Ideas Studio
          </Link>

          <nav className="hidden items-center gap-6 text-[15px] text-secondary md:flex">
            {NAV_ITEMS.map((item) => (
              <a key={item.label} href={item.href} className="hover:text-primary transition-colors">
                {item.label}
              </a>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <Link to="/login" className="hidden sm:inline-flex rounded-[8px] px-3 py-1.5 text-[14px] font-medium text-secondary hover:bg-surface-soft hover:text-primary transition-colors">
              Connexion
            </Link>
            <Link to="/projects" className="inline-flex items-center gap-1.5 rounded-[8px] bg-accent px-3 py-1.5 text-[14px] font-medium text-white hover:opacity-90 transition-opacity">
              Ouvrir le studio
              <ArrowRight size={13} />
            </Link>
            <button
              className="flex md:hidden h-8 w-8 items-center justify-center rounded-[8px] text-secondary hover:bg-surface-soft"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>
        {mobileMenuOpen && (
          <div className="border-t border-border bg-surface px-5 py-3 md:hidden">
            <nav className="flex flex-col gap-2">
              {NAV_ITEMS.map((item) => (
                <a key={item.label} href={item.href} className="text-[15px] text-secondary hover:text-primary py-1">
                  {item.label}
                </a>
              ))}
              <Link to="/login" className="text-[15px] text-accent font-medium py-1">Connexion</Link>
            </nav>
          </div>
        )}
      </header>

      <div className="mx-auto grid max-w-7xl gap-0 px-5 py-0 lg:grid-cols-[260px_minmax(0,1fr)_200px]">
        {/* Left sidebar - chapters */}
        <aside className="hidden lg:block border-r border-border min-h-[calc(100vh-56px)]">
          <div className="sticky top-14 py-6 pr-4">
            <button
              type="button"
              onClick={openPalette}
              className="mb-4 flex w-full items-center gap-2 rounded-[8px] border border-border bg-surface px-3 py-2 text-left text-[14px] text-tertiary hover:border-border-strong hover:text-secondary transition-colors"
            >
              <Search size={14} className="shrink-0" />
              Rechercher dans la doc…
              <kbd className="ml-auto shrink-0 rounded-[4px] border border-border bg-surface-soft px-1.5 py-0.5 text-[11px] font-medium text-tertiary">⌘K</kbd>
            </button>
            <nav className="flex flex-col gap-0.5">
              {CHAPTERS.map((ch) => {
                const ChapterIcon = ch.icon
                return (
                  <button
                    key={ch.id}
                    onClick={() => goToChapter(ch.id)}
                    className={`flex w-full items-center gap-2.5 text-left rounded-[8px] px-3 py-2 text-[14px] transition-colors ${
                      activeChapterId === ch.id
                        ? 'bg-accent/10 font-medium text-accent'
                        : 'text-secondary hover:bg-surface-soft hover:text-primary'
                    }`}
                  >
                    <ChapterIcon size={15} className={activeChapterId === ch.id ? 'text-accent' : 'text-tertiary'} />
                    {ch.label}
                  </button>
                )
              })}
            </nav>
          </div>
        </aside>

        {/* Main content - active chapter only */}
        <main className="min-w-0 px-6 lg:px-10 py-10 max-w-3xl">
          <Card className="mb-10">
            <p className="text-[12px] font-semibold uppercase tracking-wider text-accent">Documentation</p>
            <h1 className="mt-2 text-[32px] font-semibold leading-tight text-primary">Documentation Ideas Studio</h1>
            <p className="mt-3 text-[15px] leading-relaxed text-secondary">
              Comprendre, configurer et utiliser le studio éditorial SEO/GEO assisté par IA.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <Link to="/projects" className="inline-flex h-9 items-center gap-1.5 rounded-[8px] bg-accent px-3.5 text-[14px] font-semibold text-white hover:opacity-90">
                Ouvrir le studio
                <ArrowRight size={14} />
              </Link>
              <button
                type="button"
                onClick={handleDownloadMarkdown}
                className="inline-flex h-9 items-center gap-1.5 rounded-[8px] bg-[#1d1d1f] px-3.5 text-[14px] font-semibold text-white hover:bg-[#2d2d30]"
              >
                <Download size={14} />
                Télécharger Markdown complet
              </button>
              <a href={swaggerUrl} target="_blank" rel="noopener noreferrer" className="inline-flex h-9 items-center rounded-[8px] border border-border px-3.5 text-[14px] font-medium text-primary hover:bg-surface-soft">
                Ouvrir Swagger API
              </a>
              <a href={redocUrl} target="_blank" rel="noopener noreferrer" className="inline-flex h-9 items-center rounded-[8px] border border-border px-3.5 text-[14px] font-medium text-primary hover:bg-surface-soft">
                ReDoc
              </a>
              <a href={openApiUrl} target="_blank" rel="noopener noreferrer" className="inline-flex h-9 items-center rounded-[8px] border border-border px-3.5 text-[14px] font-medium text-primary hover:bg-surface-soft">
                OpenAPI JSON
              </a>
            </div>
            {!configuredApiUrl && (
              <p className="mt-3 text-[12px] leading-relaxed text-tertiary">
                Aucun <code className="text-accent">VITE_API_URL</code> n'est configuré : les liens API utilisent le backend local de développement.
              </p>
            )}
          </Card>
          <div ref={contentRef} className="doc-content" dangerouslySetInnerHTML={{ __html: activeChapter.content }} />

          <div className="mt-14 grid grid-cols-1 gap-3 border-t border-border pt-8 sm:grid-cols-2">
            {prevChapter ? (
              <button
                type="button"
                onClick={() => goToChapter(prevChapter.id)}
                className="group flex items-center gap-3 rounded-[10px] border border-border px-4 py-3 text-left hover:border-border-strong hover:bg-surface-soft transition-colors"
              >
                <ChevronLeft size={16} className="shrink-0 text-tertiary group-hover:text-primary transition-colors" />
                <span className="min-w-0">
                  <span className="block text-[11px] font-medium uppercase tracking-wider text-tertiary">Précédent</span>
                  <span className="block truncate text-[14px] font-medium text-primary">{prevChapter.label}</span>
                </span>
              </button>
            ) : (
              <span />
            )}
            {nextChapter && (
              <button
                type="button"
                onClick={() => goToChapter(nextChapter.id)}
                className="group flex items-center justify-end gap-3 rounded-[10px] border border-border px-4 py-3 text-right hover:border-border-strong hover:bg-surface-soft transition-colors sm:col-start-2"
              >
                <span className="min-w-0">
                  <span className="block text-[11px] font-medium uppercase tracking-wider text-tertiary">Suivant</span>
                  <span className="block truncate text-[14px] font-medium text-primary">{nextChapter.label}</span>
                </span>
                <ChevronRight size={16} className="shrink-0 text-tertiary group-hover:text-primary transition-colors" />
              </button>
            )}
          </div>
        </main>

        {/* Right sidebar - outline of active chapter only */}
        <aside className="hidden xl:block border-l border-border min-h-[calc(100vh-56px)]">
          <div className="sticky top-14 py-6 pl-4">
            <p className="mb-3 text-[12px] font-semibold uppercase tracking-wider text-tertiary">Sur cette page</p>
            <nav className="flex flex-col gap-0.5">
              {outline.map((item) => {
                const isActive = activeSectionId === item.id
                return (
                  <a
                    key={item.id}
                    href={`#${item.id}`}
                    className={`border-l-2 py-1.5 text-[14px] transition-colors duration-200 ${
                      item.depth === 3 ? 'pl-6' : 'pl-4'
                    } ${
                      isActive
                        ? 'border-accent font-medium text-accent'
                        : `border-border hover:border-border-strong hover:text-primary ${item.depth === 3 ? 'text-tertiary' : 'text-secondary'}`
                    }`}
                  >
                    {item.label}
                  </a>
                )
              })}
            </nav>
          </div>
        </aside>
      </div>

      {/* Footer */}
      <footer className="border-t border-border bg-surface">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-5 py-6 text-[14px] text-tertiary">
          <span>&copy; {new Date().getFullYear()} Ideas Studio</span>
          <div className="flex items-center gap-6">
            <Link to="/documentation" className="hover:text-primary transition-colors">Documentation</Link>
            <Link to="/login" className="hover:text-primary transition-colors">Connexion</Link>
            <Link to="/projects" className="hover:text-primary transition-colors">Studio</Link>
          </div>
        </div>
      </footer>

      {/* ⌘K search palette */}
      {paletteOpen && (
        <div
          className="fixed inset-0 z-[100] flex items-start justify-center bg-black/40 px-4 pt-[12vh] backdrop-blur-sm"
          onClick={() => setPaletteOpen(false)}
        >
          <div
            className="w-full max-w-xl overflow-hidden rounded-[14px] border border-border bg-surface shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 border-b border-border px-4 py-3">
              <Search size={16} className="shrink-0 text-tertiary" />
              <input
                ref={paletteInputRef}
                value={paletteQuery}
                onChange={(e) => { setPaletteQuery(e.target.value); setPaletteIndex(0) }}
                onKeyDown={handlePaletteKeyDown}
                placeholder="Rechercher une page, un chapitre…"
                className="w-full bg-transparent text-[15px] text-primary outline-none placeholder:text-tertiary"
              />
              <kbd className="shrink-0 rounded-[4px] border border-border px-1.5 py-0.5 text-[11px] text-tertiary">Esc</kbd>
            </div>
            <div className="max-h-[60vh] overflow-y-auto p-2">
              {paletteResults.length === 0 && (
                <p className="px-3 py-6 text-center text-[14px] text-tertiary">Aucun résultat pour « {paletteQuery} »</p>
              )}
              {paletteResults.map((item, index) => {
                const ItemIcon = item.icon
                return (
                  <button
                    key={`${item.chapterId}-${item.id}`}
                    type="button"
                    onClick={() => selectPaletteItem(item)}
                    onMouseEnter={() => setPaletteIndex(index)}
                    className={`flex w-full items-center gap-3 rounded-[8px] px-3 py-2.5 text-left transition-colors ${
                      index === paletteIndex ? 'bg-accent/10' : 'hover:bg-surface-soft'
                    }`}
                  >
                    <ItemIcon size={15} className={index === paletteIndex ? 'text-accent' : 'text-tertiary'} />
                    <span className="min-w-0 flex-1">
                      <span className={`block truncate text-[14px] ${index === paletteIndex ? 'font-medium text-accent' : 'text-primary'}`}>
                        {item.label}
                      </span>
                      {!item.isChapterRoot && (
                        <span className="block truncate text-[12px] text-tertiary">{item.chapterLabel}</span>
                      )}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
