import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  Check,
  ClipboardList,
  FileText,
  Gauge,
  LifeBuoy,
  Lock,
  Mail,
  MessageSquare,
  Search,
  ShieldCheck,
  Sparkles,
  Users,
} from '@/components/ui/hugeIcons'
import { publicCopy } from '@/lib/publicI18n'

const t = publicCopy.en
const supportEmail = 'support@ideasstudio.ai'

function PublicNav() {
  return (
    <header className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4">
      <Link to="/" className="flex items-center gap-2 text-[15px] font-semibold text-[#101114]">
        <img src="/icon.svg" alt="" className="h-7 w-7 rounded-[8px]" />
        Ideas Studio
      </Link>
      <nav className="hidden items-center gap-6 text-[13px] font-medium text-[#5f6368] md:flex">
        <Link to="/features" className="hover:text-[#101114]">{t.nav.features}</Link>
        <Link to="/documentation" className="hover:text-[#101114]">{t.nav.documentation}</Link>
        <Link to="/support" className="hover:text-[#101114]">{t.nav.support}</Link>
      </nav>
      <div className="flex items-center gap-2">
        <Link to="/login" className="hidden rounded-[8px] px-3 py-2 text-[13px] font-medium text-[#33363d] hover:bg-[#eef0f4] sm:inline-flex">
          {t.nav.signIn}
        </Link>
        <Link to="/register" className="inline-flex h-9 items-center gap-1.5 rounded-[8px] bg-[#2563ff] px-3.5 text-[13px] font-semibold text-white hover:bg-[#1f54d8]">
          {t.nav.start}
          <ArrowRight size={14} />
        </Link>
      </div>
    </header>
  )
}

function PublicFooter() {
  return (
    <footer className="border-t border-[#e5e7eb] bg-white">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 md:grid-cols-[1.2fr_2fr]">
        <div>
          <div className="flex items-center gap-2 text-[15px] font-semibold text-[#101114]">
            <img src="/icon.svg" alt="" className="h-7 w-7 rounded-[8px]" />
            Ideas Studio
          </div>
          <p className="mt-3 max-w-sm text-[13px] leading-6 text-[#6b7280]">
            AI editorial operations for teams that need strategy, production, SEO quality and performance in one reliable product.
          </p>
        </div>
        <div className="grid gap-6 text-[13px] sm:grid-cols-3">
          <div className="grid gap-2">
            <p className="font-semibold text-[#101114]">Product</p>
            <Link to="/features" className="text-[#6b7280] hover:text-[#101114]">Features</Link>
            <Link to="/documentation" className="text-[#6b7280] hover:text-[#101114]">Documentation</Link>
          </div>
          <div className="grid gap-2">
            <p className="font-semibold text-[#101114]">Company</p>
            <Link to="/support" className="text-[#6b7280] hover:text-[#101114]">Support</Link>
            <Link to="/contact" className="text-[#6b7280] hover:text-[#101114]">Contact</Link>
            <a href={`mailto:${supportEmail}`} className="text-[#6b7280] hover:text-[#101114]">Email</a>
          </div>
          <div className="grid gap-2">
            <p className="font-semibold text-[#101114]">Legal</p>
            <Link to="/privacy" className="text-[#6b7280] hover:text-[#101114]">Privacy</Link>
            <Link to="/terms" className="text-[#6b7280] hover:text-[#101114]">Terms</Link>
            <Link to="/security" className="text-[#6b7280] hover:text-[#101114]">Security</Link>
          </div>
        </div>
      </div>
    </footer>
  )
}

function DashboardVisual() {
  return (
    <div className="mx-auto w-full max-w-5xl rounded-[8px] border border-[#dfe3ea] bg-white p-3 shadow-[0_24px_80px_rgba(17,24,39,0.16)]">
      <div className="flex items-center justify-between border-b border-[#edf0f4] pb-3">
        <div className="flex items-center gap-2">
          <img src="/icon.svg" alt="" className="h-7 w-7 rounded-[8px]" />
          <span className="text-[13px] font-semibold text-[#111827]">Editorial Command Center</span>
        </div>
        <div className="hidden items-center gap-2 text-[11px] text-[#6b7280] sm:flex">
          <span className="rounded-[8px] bg-[#ecfdf5] px-2 py-1 text-[#047857]">Live SEO</span>
          <span className="rounded-[8px] bg-[#eff6ff] px-2 py-1 text-[#1d4ed8]">Gemini ready</span>
        </div>
      </div>
      <div className="grid gap-3 pt-3 lg:grid-cols-[210px_1fr_230px]">
        <aside className="hidden rounded-[8px] bg-[#f6f7f9] p-3 lg:block">
          {['Dashboard', 'Articles', 'Ideas', 'Production', 'Traffic'].map((item, index) => (
            <div key={item} className={`mb-1 flex items-center gap-2 rounded-[8px] px-2 py-2 text-[12px] ${index === 3 ? 'bg-white text-[#2563ff]' : 'text-[#6b7280]'}`}>
              <span className="h-2 w-2 rounded-full bg-current" />
              {item}
            </div>
          ))}
        </aside>
        <main className="grid gap-3">
          <div className="grid gap-3 sm:grid-cols-3">
            {[
              ['Ideas approved', '48', '+18%'],
              ['Articles in production', '17', '+6%'],
              ['SEO score', '91', '+11%'],
            ].map(([label, value, delta]) => (
              <div key={label} className="rounded-[8px] border border-[#e8ebf0] p-3">
                <p className="text-[11px] text-[#6b7280]">{label}</p>
                <div className="mt-2 flex items-end justify-between">
                  <span className="text-[24px] font-semibold text-[#111827]">{value}</span>
                  <span className="text-[11px] font-semibold text-[#047857]">{delta}</span>
                </div>
              </div>
            ))}
          </div>
          <div className="rounded-[8px] border border-[#e8ebf0] p-3">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-[12px] font-semibold text-[#111827]">Production workflow</p>
              <span className="text-[11px] text-[#6b7280]">Updated now</span>
            </div>
            <div className="grid gap-2 sm:grid-cols-3">
              {['Outline', 'Writing', 'SEO review'].map((stage, index) => (
                <div key={stage} className="min-h-24 rounded-[8px] bg-[#f6f7f9] p-2">
                  <p className="mb-2 text-[11px] font-semibold text-[#5f6368]">{stage}</p>
                  <div className="rounded-[8px] bg-white p-2 text-[12px] text-[#111827] shadow-[0_1px_0_rgba(17,24,39,0.04)]">
                    {['AI brief validated', 'Draft in progress', 'Meta tags ready'][index]}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </main>
        <aside className="grid gap-3">
          <div className="rounded-[8px] border border-[#e8ebf0] p-3">
            <p className="text-[12px] font-semibold text-[#111827]">Traffic sources</p>
            {[
              ['Organic', '62%'],
              ['Direct', '21%'],
              ['Referral', '17%'],
            ].map(([label, value]) => (
              <div key={label} className="mt-3">
                <div className="mb-1 flex justify-between text-[11px] text-[#6b7280]"><span>{label}</span><span>{value}</span></div>
                <div className="h-1.5 rounded-full bg-[#eef0f4]"><div className="h-full rounded-full bg-[#2563ff]" style={{ width: value }} /></div>
              </div>
            ))}
          </div>
          <div className="rounded-[8px] border border-[#e8ebf0] p-3">
            <p className="text-[12px] font-semibold text-[#111827]">Quality gates</p>
            <div className="mt-3 grid gap-2 text-[12px] text-[#374151]">
              <span className="flex items-center gap-2"><Check size={14} className="text-[#047857]" /> No placeholder content</span>
              <span className="flex items-center gap-2"><Check size={14} className="text-[#047857]" /> SEO review attached</span>
              <span className="flex items-center gap-2"><Check size={14} className="text-[#047857]" /> Ready for publish</span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}

function FeatureCard({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <div className="rounded-[8px] border border-[#e5e7eb] bg-white p-5">
      <span className="mb-4 flex h-9 w-9 items-center justify-center rounded-[8px] bg-[#f1f5ff] text-[#2563ff]">{icon}</span>
      <h3 className="text-[16px] font-semibold text-[#111827]">{title}</h3>
      <p className="mt-2 text-[13px] leading-6 text-[#6b7280]">{children}</p>
    </div>
  )
}

export function LandingPage() {
  return (
    <div className="min-h-screen bg-[#f7f8fb] text-[#111827]">
      <PublicNav />
      <main>
        <section className="relative overflow-hidden border-y border-[#e5e7eb] bg-[#f7f8fb] px-4 pt-16">
          <div className="mx-auto flex min-h-[680px] max-w-6xl flex-col items-center">
            <p className="rounded-full border border-[#dfe3ea] bg-white px-3 py-1 text-center text-[12px] font-semibold text-[#2563ff]">{t.hero.eyebrow}</p>
            <h1 className="mt-5 max-w-4xl text-center text-[44px] font-semibold leading-[1.04] text-[#101114] sm:text-[64px]">
              {t.hero.title}
            </h1>
            <p className="mt-5 max-w-2xl text-center text-[16px] leading-7 text-[#5f6368]">{t.hero.subtitle}</p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Link to="/register" className="inline-flex h-11 items-center gap-2 rounded-[8px] bg-[#2563ff] px-5 text-[14px] font-semibold text-white hover:bg-[#1f54d8]">
                {t.hero.primary}
                <ArrowRight size={16} />
              </Link>
            </div>
            <div className="mt-12 w-full translate-y-10">
              <DashboardVisual />
            </div>
          </div>
        </section>

        <section className="mx-auto grid max-w-6xl gap-4 px-4 py-24 md:grid-cols-3">
          <FeatureCard icon={<Sparkles size={18} />} title="AI planning that starts from strategy">
            Generate ideas from project context, audience, categories and real editorial constraints.
          </FeatureCard>
          <FeatureCard icon={<ClipboardList size={18} />} title="Production built for delivery">
            Move validated ideas into a production board with statuses, custom columns and clear ownership.
          </FeatureCard>
          <FeatureCard icon={<Gauge size={18} />} title="SEO and traffic in the loop">
            Review quality, detect weak content and connect performance signals back to the roadmap.
          </FeatureCard>
        </section>

        <section className="border-y border-[#e5e7eb] bg-white px-4 py-20">
          <div className="mx-auto grid max-w-6xl gap-10 lg:grid-cols-[0.9fr_1.1fr]">
            <div>
              <p className="text-[13px] font-semibold text-[#2563ff]">Connected workflow</p>
              <h2 className="mt-3 text-[34px] font-semibold leading-tight text-[#111827]">No isolated AI toys. One editorial system.</h2>
              <p className="mt-4 text-[15px] leading-7 text-[#6b7280]">
                Ideas Studio is structured around the real path from opportunity to published article: idea discovery, drafting, review, production, publishing and monitoring.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                ['Provider settings', 'Configure Gemini and other providers inside the CMS without exposing keys in the frontend.'],
                ['Team roles', 'Invite collaborators and keep access scoped to each project.'],
                ['Public tracking', 'Follow views, sources, devices and countries when tracking is configured.'],
                ['Quality controls', 'Detect placeholder content, SEO gaps and missing publishing metadata.'],
              ].map(([title, body]) => (
                <div key={title} className="rounded-[8px] bg-[#f7f8fb] p-4">
                  <p className="text-[14px] font-semibold text-[#111827]">{title}</p>
                  <p className="mt-2 text-[13px] leading-6 text-[#6b7280]">{body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
      <PublicFooter />
    </div>
  )
}

export function FeaturesPage() {
  return (
    <PublicShell title="Features" subtitle="Everything needed to operate an AI-assisted editorial workflow without losing control of quality.">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <FeatureCard icon={<Sparkles size={18} />} title="Idea generation">Generate and prioritize article ideas with opportunity scores and briefs.</FeatureCard>
        <FeatureCard icon={<FileText size={18} />} title="Article workspace">Write, edit, preview, version and prepare articles for publication.</FeatureCard>
        <FeatureCard icon={<ClipboardList size={18} />} title="Production board">Track editorial status with real articles and configurable workflow columns.</FeatureCard>
        <FeatureCard icon={<Search size={18} />} title="SEO review">Analyze drafts, metadata, quality issues and actionable optimization opportunities.</FeatureCard>
        <FeatureCard icon={<BarChart3 size={18} />} title="Performance">Monitor views, top pages, devices, countries and source channels.</FeatureCard>
        <FeatureCard icon={<Users size={18} />} title="Collaboration">Manage members, invitations, roles and project-level access.</FeatureCard>
      </div>
    </PublicShell>
  )
}

export function PricingPage() {
  const plans: Array<{ name: string; price: string; intro: string; items: string[] }> = [
    {
      name: 'Starter',
      price: '$29',
      intro: 'For one project moving from manual content planning to AI-assisted production.',
      items: ['1 project', 'AI idea generation', 'Production board', 'SEO review'],
    },
    {
      name: 'Studio',
      price: '$79',
      intro: 'For teams running multiple editorial workflows with performance feedback.',
      items: ['5 projects', 'Team invitations', 'Traffic dashboards', 'Provider settings'],
    },
    {
      name: 'Scale',
      price: 'Custom',
      intro: 'For agencies and operators that need stricter governance and deployment support.',
      items: ['Unlimited projects', 'Advanced support', 'Security review', 'Deployment guidance'],
    },
  ]
  return (
    <PublicShell title="Pricing" subtitle="Simple plans for editorial teams. Prices are placeholders until billing is connected.">
      <div className="grid gap-4 lg:grid-cols-3">
        {plans.map(({ name, price, intro, items }) => (
          <div key={name} className="rounded-[8px] border border-[#e5e7eb] bg-white p-6">
            <p className="text-[15px] font-semibold text-[#111827]">{name}</p>
            <p className="mt-4 text-[34px] font-semibold text-[#111827]">{price}</p>
            <p className="mt-3 min-h-16 text-[13px] leading-6 text-[#6b7280]">{intro}</p>
            <div className="mt-6 grid gap-2 text-[13px] text-[#374151]">
              {items.map((item) => (
                <span key={item} className="flex items-center gap-2"><Check size={14} className="text-[#047857]" /> {item}</span>
              ))}
            </div>
            <Link to="/register" className="mt-6 inline-flex h-10 w-full items-center justify-center rounded-[8px] bg-[#2563ff] text-[13px] font-semibold text-white hover:bg-[#1f54d8]">
              Start free
            </Link>
          </div>
        ))}
      </div>
    </PublicShell>
  )
}

export function SupportPage() {
  return (
    <PublicShell title="Support" subtitle="Get help with setup, Gemini configuration, tracking, deployment and editorial workflows.">
      <div className="grid gap-4 md:grid-cols-3">
        <FeatureCard icon={<BookOpen size={18} />} title="Documentation">Read setup, workflow and deployment notes in the product documentation.</FeatureCard>
        <FeatureCard icon={<LifeBuoy size={18} />} title="Product help">Send a precise issue summary and the project context to support.</FeatureCard>
        <FeatureCard icon={<ShieldCheck size={18} />} title="Security">Report sensitive deployment, key or access issues directly by email.</FeatureCard>
      </div>
      <div className="mt-8 rounded-[8px] border border-[#dfe3ea] bg-white p-5">
        <p className="text-[15px] font-semibold text-[#111827]">Need help now?</p>
        <p className="mt-2 text-[13px] leading-6 text-[#6b7280]">Use email until the hosted support inbox is connected.</p>
        <a href={`mailto:${supportEmail}?subject=Ideas%20Studio%20support`} className="mt-4 inline-flex h-10 items-center gap-2 rounded-[8px] bg-[#2563ff] px-4 text-[13px] font-semibold text-white hover:bg-[#1f54d8]">
          <Mail size={15} />
          Email support
        </a>
      </div>
    </PublicShell>
  )
}

export function ContactPage() {
  return (
    <PublicShell title="Contact" subtitle="Talk to the Ideas Studio team about product access, deployment or implementation.">
      <div className="grid gap-4 md:grid-cols-2">
        <FeatureCard icon={<Mail size={18} />} title="Email">Write to support@ideasstudio.ai for product and deployment questions.</FeatureCard>
        <FeatureCard icon={<MessageSquare size={18} />} title="Implementation">Share your CMS, hosting target, AI provider and launch deadline.</FeatureCard>
      </div>
      <a href={`mailto:${supportEmail}?subject=Ideas%20Studio%20contact`} className="mt-8 inline-flex h-10 items-center gap-2 rounded-[8px] bg-[#2563ff] px-4 text-[13px] font-semibold text-white hover:bg-[#1f54d8]">
        <Mail size={15} />
        Contact us
      </a>
    </PublicShell>
  )
}

export function LegalPage({ kind }: { kind: 'privacy' | 'terms' | 'security' }) {
  const content = {
    privacy: ['Privacy', 'Ideas Studio stores account, project and editorial workflow data required to operate the product. API keys must stay server-side and are never intentionally exposed to the frontend.'],
    terms: ['Terms', 'Ideas Studio is provided as editorial workflow software. Users remain responsible for content accuracy, publishing decisions and compliance with their own legal obligations.'],
    security: ['Security', 'Secrets must be configured through environment variables or protected provider settings. Do not commit API keys, expose them in documentation or send them to browser clients.'],
  }[kind]

  return (
    <PublicShell title={content[0]} subtitle="Plain-language product policy draft for launch readiness.">
      <div className="rounded-[8px] border border-[#e5e7eb] bg-white p-6">
        <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-[8px] bg-[#f1f5ff] text-[#2563ff]">
          {kind === 'security' ? <Lock size={18} /> : <ShieldCheck size={18} />}
        </div>
        <p className="text-[14px] leading-7 text-[#4b5563]">{content[1]}</p>
      </div>
    </PublicShell>
  )
}

function PublicShell({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[#f7f8fb] text-[#111827]">
      <PublicNav />
      <main className="mx-auto max-w-6xl px-4 py-16">
        <div className="mb-10 max-w-3xl">
          <h1 className="text-[42px] font-semibold leading-tight text-[#101114]">{title}</h1>
          <p className="mt-4 text-[16px] leading-7 text-[#6b7280]">{subtitle}</p>
        </div>
        {children}
      </main>
      <PublicFooter />
    </div>
  )
}
