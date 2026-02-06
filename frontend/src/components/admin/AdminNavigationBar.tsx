/**
 * AdminNavigationBar Component
 * Sprint 51: Admin Dashboard Navigation Improvement
 * Sprint 79 Feature 79.7: Added Graph Operations link
 * Sprint 112: Added MCP Marketplace link
 *
 * Navigation bar for admin subpages, displayed at the top of the admin dashboard.
 * Provides quick access to Graph Analytics, Costs, LLM Config, Health, Training, and MCP pages.
 */

import { Link, useLocation } from 'react-router-dom';
import {
  Share2,
  DollarSign,
  Cpu,
  Activity,
  GraduationCap,
  FileText,
  ListChecks,
  Wrench,
  Database,
  Layers,
  Award,
  Package,
  ShieldCheck,
  FileCheck,
  Store,
  Settings,
} from 'lucide-react';
import type { ReactNode } from 'react';

/**
 * Navigation item configuration
 */
interface NavItem {
  href: string;
  label: string;
  icon: ReactNode;
  testId: string;
}

/**
 * Navigation items for admin subpages
 */
const navItems: NavItem[] = [
  {
    href: '/admin/graph',
    label: 'Graph',
    icon: <Share2 className="w-4 h-4" />,
    testId: 'admin-nav-graph',
  },
  {
    href: '/admin/graph-operations',
    label: 'Graph Ops',
    icon: <Layers className="w-4 h-4" />,
    testId: 'admin-nav-graph-ops',
  },
  {
    href: '/admin/entities',
    label: 'Entities',
    icon: <Database className="w-4 h-4" />,
    testId: 'admin-nav-entities',
  },
  {
    href: '/admin/costs',
    label: 'Costs',
    icon: <DollarSign className="w-4 h-4" />,
    testId: 'admin-nav-costs',
  },
  {
    href: '/admin/llm-config',
    label: 'LLM',
    icon: <Cpu className="w-4 h-4" />,
    testId: 'admin-nav-llm',
  },
  {
    href: '/admin/health',
    label: 'Health',
    icon: <Activity className="w-4 h-4" />,
    testId: 'admin-nav-health',
  },
  {
    href: '/admin/domain-training',
    label: 'Training',
    icon: <GraduationCap className="w-4 h-4" />,
    testId: 'admin-nav-training',
  },
  {
    href: '/admin/deployment-profile',
    label: 'Profile',
    icon: <Settings className="w-4 h-4" />,
    testId: 'admin-nav-deployment-profile',
  },
  {
    href: '/admin/indexing',
    label: 'Indexing',
    icon: <FileText className="w-4 h-4" />,
    testId: 'admin-nav-indexing',
  },
  {
    href: '/admin/jobs',
    label: 'Jobs',
    icon: <ListChecks className="w-4 h-4" />,
    testId: 'admin-nav-jobs',
  },
  {
    href: '/admin/tools',
    label: 'Tools',
    icon: <Wrench className="w-4 h-4" />,
    testId: 'admin-nav-tools',
  },
  {
    href: '/admin/mcp-marketplace',
    label: 'MCP Store',
    icon: <Store className="w-4 h-4" />,
    testId: 'admin-nav-mcp-marketplace',
  },
  {
    href: '/admin/memory',
    label: 'Memory',
    icon: <Database className="w-4 h-4" />,
    testId: 'admin-nav-memory',
  },
  {
    href: '/admin/explainability',
    label: 'Explainability',
    icon: <FileText className="w-4 h-4" />,
    testId: 'admin-nav-explainability',
  },
  {
    href: '/admin/certification',
    label: 'Certification',
    icon: <Award className="w-4 h-4" />,
    testId: 'admin-nav-certification',
  },
  {
    href: '/admin/skills/registry',
    label: 'Skills',
    icon: <Package className="w-4 h-4" />,
    testId: 'admin-nav-skills',
  },
  {
    href: '/admin/gdpr',
    label: 'GDPR',
    icon: <ShieldCheck className="w-4 h-4" />,
    testId: 'admin-nav-gdpr',
  },
  {
    href: '/admin/audit',
    label: 'Audit',
    icon: <FileCheck className="w-4 h-4" />,
    testId: 'admin-nav-audit',
  },
];

/**
 * Single navigation link component
 */
interface NavLinkItemProps {
  item: NavItem;
  isActive: boolean;
}

function NavLinkItem({ item, isActive }: NavLinkItemProps) {
  const baseClasses =
    'flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors';
  const activeClasses = 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300';
  const inactiveClasses =
    'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-200';

  return (
    <Link
      to={item.href}
      className={`${baseClasses} ${isActive ? activeClasses : inactiveClasses}`}
      data-testid={item.testId}
      aria-current={isActive ? 'page' : undefined}
    >
      {item.icon}
      <span>{item.label}</span>
    </Link>
  );
}

/**
 * AdminNavigationBar - Top navigation for admin subpages
 *
 * Displays a horizontal navigation bar with links to all admin subpages.
 * Highlights the current page and provides responsive design for mobile/desktop.
 */
export function AdminNavigationBar() {
  const location = useLocation();

  return (
    <nav
      className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm p-2"
      data-testid="admin-navigation-bar"
      aria-label="Admin navigation"
    >
      <div className="flex flex-wrap gap-2">
        {navItems.map((item) => (
          <NavLinkItem
            key={item.href}
            item={item}
            isActive={location.pathname === item.href}
          />
        ))}
      </div>
    </nav>
  );
}

export default AdminNavigationBar;
