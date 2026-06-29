import { forwardRef } from 'react'
import type { HugeiconsProps, IconSvgElement } from '@hugeicons/react'
import { HugeiconsIcon } from '@hugeicons/react'
import {
  Activity01Icon,
  Add01Icon,
  AlertCircleIcon,
  AlertTriangle as HugeAlertTriangle,
  ArchiveIcon,
  ArrowDownRight01Icon,
  ArrowLeft01Icon,
  ArrowRight01Icon,
  ArrowUp01Icon,
  ArrowUpRight01Icon,
  BarChartIcon,
  BellIcon,
  BookOpenIcon,
  BotIcon,
  BulbIcon,
  Calendar03Icon,
  CalendarClockIcon,
  CameraIcon,
  Cancel01Icon,
  CancelCircleIcon,
  CheckCheckIcon,
  CheckIcon,
  CheckmarkCircle01Icon,
  ChevronDownIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronUpIcon,
  CircleMinusIcon,
  ClipboardListIcon,
  Clock01Icon,
  Clock03Icon,
  CodeIcon,
  CodeSquareIcon,
  Copy01Icon,
  CpuIcon,
  CrownIcon,
  CursorPointer01Icon,
  Delete02Icon,
  DollarIcon,
  Download01Icon,
  EuroIcon,
  ExternalLinkIcon,
  EyeIcon,
  EyeOffIcon,
  File01Icon,
  FileEditIcon,
  FileImportIcon,
  FolderOpenIcon,
  GaugeIcon,
  Globe02Icon,
  Heading1Icon,
  Heading2Icon,
  Heading03Icon,
  Heading4Icon,
  HelpCircleIcon,
  HistoryIcon,
  Image01Icon,
  InformationCircleIcon,
  Key01Icon,
  LeftToRightListBulletIcon,
  LeftToRightListNumberIcon,
  LifebuoyIcon,
  LibraryIcon,
  Link01Icon,
  Link02Icon,
  Loading03Icon,
  LockIcon,
  Logout01Icon,
  MagicWand01Icon,
  Mail01Icon,
  MailAtSign01Icon,
  MailSend01Icon,
  Menu01Icon,
  Message01Icon,
  MessageCircle as HugeMessageCircle,
  MinusSignIcon,
  Monitor as HugeMonitor,
  Palette as HugePalette,
  PanelLeftCloseIcon,
  PanelLeftOpenIcon,
  PencilEdit01Icon,
  PencilEdit02Icon,
  PencilIcon,
  Pilcrow as HugePilcrow,
  PlayIcon,
  PowerIcon,
  QuoteDownIcon,
  Redo02Icon,
  RefreshCw as HugeRefreshCw,
  RotateCcw as HugeRotateCcw,
  RotateCw as HugeRotateCw,
  SaveIcon,
  Search01Icon,
  Setting06Icon,
  Shield01Icon,
  ShieldCheck as HugeShieldCheck,
  SmartPhone01Icon,
  SparklesIcon,
  StarIcon,
  StickyNoteIcon,
  Table02Icon,
  Tablet01Icon,
  TagsIcon,
  TerminalIcon,
  TestTube02Icon,
  TestTubeIcon,
  TextBoldIcon,
  TextItalicIcon,
  TextUnderlineIcon,
  TrendingUp as HugeTrendingUp,
  TypeCursorIcon,
  Undo02Icon,
  Unlink02Icon,
  Upload01Icon,
  UserAdd01Icon,
  UserGroupIcon,
  UserIcon,
  Wifi01Icon,
  WifiDisconnected01Icon,
  ZapIcon,
} from '@hugeicons/core-free-icons'

export type HugeIconComponentProps = Omit<HugeiconsProps, 'icon' | 'altIcon' | 'showAlt'>
export type HugeIconComponent = ReturnType<typeof createHugeIcon>

function createHugeIcon(icon: IconSvgElement) {
  return forwardRef<SVGSVGElement, HugeIconComponentProps>(function HugeIconAdapter(
    { size = 16, strokeWidth = 1.8, color = 'currentColor', ...props },
    ref,
  ) {
    return (
      <HugeiconsIcon
        ref={ref}
        icon={icon}
        size={size}
        strokeWidth={strokeWidth}
        color={color}
        {...props}
      />
    )
  })
}

export const Activity = createHugeIcon(Activity01Icon)
export const AlertCircle = createHugeIcon(AlertCircleIcon)
export const AlertTriangle = createHugeIcon(HugeAlertTriangle)
export const Archive = createHugeIcon(ArchiveIcon)
export const ArrowDownRight = createHugeIcon(ArrowDownRight01Icon)
export const ArrowLeft = createHugeIcon(ArrowLeft01Icon)
export const ArrowRight = createHugeIcon(ArrowRight01Icon)
export const ArrowUp = createHugeIcon(ArrowUp01Icon)
export const ArrowUpRight = createHugeIcon(ArrowUpRight01Icon)
export const AtSign = createHugeIcon(MailAtSign01Icon)
export const BarChart2 = createHugeIcon(BarChartIcon)
export const BarChart3 = createHugeIcon(BarChartIcon)
export const Bell = createHugeIcon(BellIcon)
export const Bold = createHugeIcon(TextBoldIcon)
export const BookOpen = createHugeIcon(BookOpenIcon)
export const Bot = createHugeIcon(BotIcon)
export const Calendar = createHugeIcon(Calendar03Icon)
export const CalendarClock = createHugeIcon(CalendarClockIcon)
export const CalendarDays = createHugeIcon(Calendar03Icon)
export const Camera = createHugeIcon(CameraIcon)
export const Check = createHugeIcon(CheckIcon)
export const CheckCheck = createHugeIcon(CheckCheckIcon)
export const CheckCircle = createHugeIcon(CheckmarkCircle01Icon)
export const ChevronDown = createHugeIcon(ChevronDownIcon)
export const ChevronLeft = createHugeIcon(ChevronLeftIcon)
export const ChevronRight = createHugeIcon(ChevronRightIcon)
export const ChevronUp = createHugeIcon(ChevronUpIcon)
export const ClipboardList = createHugeIcon(ClipboardListIcon)
export const Clock = createHugeIcon(Clock01Icon)
export const Clock3 = createHugeIcon(Clock03Icon)
export const Code = createHugeIcon(CodeIcon)
export const Code2 = createHugeIcon(CodeSquareIcon)
export const Copy = createHugeIcon(Copy01Icon)
export const Cpu = createHugeIcon(CpuIcon)
export const Crown = createHugeIcon(CrownIcon)
export const DollarSign = createHugeIcon(DollarIcon)
export const Download = createHugeIcon(Download01Icon)
export const Edit2 = createHugeIcon(PencilEdit01Icon)
export const Edit3 = createHugeIcon(PencilEdit02Icon)
export const Euro = createHugeIcon(EuroIcon)
export const ExternalLink = createHugeIcon(ExternalLinkIcon)
export const Eye = createHugeIcon(EyeIcon)
export const EyeOff = createHugeIcon(EyeOffIcon)
export const FilePenLine = createHugeIcon(FileEditIcon)
export const FileText = createHugeIcon(File01Icon)
export const FolderOpen = createHugeIcon(FolderOpenIcon)
export const Gauge = createHugeIcon(GaugeIcon)
export const Globe = createHugeIcon(Globe02Icon)
export const Heading1 = createHugeIcon(Heading1Icon)
export const Heading2 = createHugeIcon(Heading2Icon)
export const Heading3 = createHugeIcon(Heading03Icon)
export const Heading4 = createHugeIcon(Heading4Icon)
export const HelpCircle = createHugeIcon(HelpCircleIcon)
export const History = createHugeIcon(HistoryIcon)
export const Image = createHugeIcon(Image01Icon)
export const Import = createHugeIcon(FileImportIcon)
export const Info = createHugeIcon(InformationCircleIcon)
export const Italic = createHugeIcon(TextItalicIcon)
export const Key = createHugeIcon(Key01Icon)
export const Library = createHugeIcon(LibraryIcon)
export const LifeBuoy = createHugeIcon(LifebuoyIcon)
export const Lightbulb = createHugeIcon(BulbIcon)
export const Link = createHugeIcon(Link01Icon)
export const Link2 = createHugeIcon(Link02Icon)
export const List = createHugeIcon(LeftToRightListBulletIcon)
export const ListOrdered = createHugeIcon(LeftToRightListNumberIcon)
export const Loader2 = createHugeIcon(Loading03Icon)
export const Lock = createHugeIcon(LockIcon)
export const LogOut = createHugeIcon(Logout01Icon)
export const Mail = createHugeIcon(Mail01Icon)
export const Menu = createHugeIcon(Menu01Icon)
export const MessageCircle = createHugeIcon(HugeMessageCircle)
export const MessageSquare = createHugeIcon(Message01Icon)
export const Minus = createHugeIcon(MinusSignIcon)
export const MinusCircle = createHugeIcon(CircleMinusIcon)
export const Monitor = createHugeIcon(HugeMonitor)
export const MousePointer2 = createHugeIcon(CursorPointer01Icon)
export const Palette = createHugeIcon(HugePalette)
export const PanelLeftClose = createHugeIcon(PanelLeftCloseIcon)
export const PanelLeftOpen = createHugeIcon(PanelLeftOpenIcon)
export const PenLine = createHugeIcon(PencilEdit01Icon)
export const Pencil = createHugeIcon(PencilIcon)
export const PencilLine = createHugeIcon(PencilEdit02Icon)
export const Pilcrow = createHugeIcon(HugePilcrow)
export const Play = createHugeIcon(PlayIcon)
export const Plus = createHugeIcon(Add01Icon)
export const Power = createHugeIcon(PowerIcon)
export const Quote = createHugeIcon(QuoteDownIcon)
export const Redo2 = createHugeIcon(Redo02Icon)
export const RefreshCw = createHugeIcon(HugeRefreshCw)
export const RotateCcw = createHugeIcon(HugeRotateCcw)
export const RotateCw = createHugeIcon(HugeRotateCw)
export const Save = createHugeIcon(SaveIcon)
export const Search = createHugeIcon(Search01Icon)
export const Send = createHugeIcon(MailSend01Icon)
export const Settings = createHugeIcon(Setting06Icon)
export const Shield = createHugeIcon(Shield01Icon)
export const ShieldCheck = createHugeIcon(HugeShieldCheck)
export const Smartphone = createHugeIcon(SmartPhone01Icon)
export const Sparkles = createHugeIcon(SparklesIcon)
export const Star = createHugeIcon(StarIcon)
export const StickyNote = createHugeIcon(StickyNoteIcon)
export const Table2 = createHugeIcon(Table02Icon)
export const Tablet = createHugeIcon(Tablet01Icon)
export const Tags = createHugeIcon(TagsIcon)
export const Terminal = createHugeIcon(TerminalIcon)
export const TestTube = createHugeIcon(TestTubeIcon)
export const TestTube2 = createHugeIcon(TestTube02Icon)
export const Trash2 = createHugeIcon(Delete02Icon)
export const TrendingUp = createHugeIcon(HugeTrendingUp)
export const Type = createHugeIcon(TypeCursorIcon)
export const Underline = createHugeIcon(TextUnderlineIcon)
export const Undo2 = createHugeIcon(Undo02Icon)
export const Unlink2 = createHugeIcon(Unlink02Icon)
export const Upload = createHugeIcon(Upload01Icon)
export const User = createHugeIcon(UserIcon)
export const UserPlus = createHugeIcon(UserAdd01Icon)
export const Users = createHugeIcon(UserGroupIcon)
export const Wand2 = createHugeIcon(MagicWand01Icon)
export const Wifi = createHugeIcon(Wifi01Icon)
export const WifiOff = createHugeIcon(WifiDisconnected01Icon)
export const X = createHugeIcon(Cancel01Icon)
export const XCircle = createHugeIcon(CancelCircleIcon)
export const Zap = createHugeIcon(ZapIcon)
