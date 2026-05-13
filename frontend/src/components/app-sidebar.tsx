"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import {
  LayoutDashboard,
  GitBranch,
  Scale,
  ClipboardList,
  AlertTriangle,
  CalendarDays,
  BookOpen,
  FileText,
  Puzzle,
  Package,
  Users,
  Rocket,
  ChevronDown,
  Settings,
  LogOut,
} from "lucide-react"
import { getSupabaseBrowserClient } from "@/lib/supabase-browser"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarSeparator,
} from "@/components/ui/sidebar"

const navItems = [
  { title: "Overview", icon: LayoutDashboard, href: "/dashboard" },
  { title: "Product Tree", icon: GitBranch, href: "/dashboard/product-tree" },
  { title: "Budgets", icon: Scale, href: "/dashboard/budgets" },
  { title: "Requirements", icon: ClipboardList, href: "/dashboard/requirements" },
  { title: "Risks", icon: AlertTriangle, href: "/dashboard/risks" },
  { title: "Schedule", icon: CalendarDays, href: "/dashboard/schedule" },
  { title: "ECSS", icon: BookOpen, href: "/dashboard/ecss" },
  { title: "Reports", icon: FileText, href: "/dashboard/reports" },
  { title: "Integrations", icon: Puzzle, href: "/dashboard/integrations" },
  { title: "Warehouse", icon: Package, href: "/dashboard/warehouse" },
  { title: "Team", icon: Users, href: "/dashboard/team" },
  { title: "Settings", icon: Settings, href: "/dashboard/settings" },
]

export function AppSidebar() {
  const pathname = usePathname()
  const router = useRouter()

  function isActive(href: string) {
    if (href === "/dashboard") {
      return pathname === "/dashboard"
    }
    return pathname.startsWith(href)
  }

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="p-4">
        <Link href="/dashboard" className="flex items-center gap-3 group-data-[collapsible=icon]:justify-center">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Rocket className="h-4 w-4" />
          </div>
          <div className="flex flex-col group-data-[collapsible=icon]:hidden">
            <span className="text-sm font-bold tracking-wide">B.E.P.I.</span>
            <span className="text-[10px] font-medium uppercase tracking-widest text-sidebar-foreground/60">
              Budget Engineering Project Integration
            </span>
          </div>
        </Link>
      </SidebarHeader>

      <SidebarSeparator />

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton
                    isActive={isActive(item.href)}
                    tooltip={item.title}
                    render={<Link href={item.href} />}
                  >
                    <item.icon />
                    <span>{item.title}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarSeparator />
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              tooltip="Sign Out"
              onClick={async () => {
                const supabase = getSupabaseBrowserClient();
                await supabase.auth.signOut();
                router.push("/login");
              }}
            >
              <LogOut />
              <span>Sign Out</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
        <SidebarSeparator />
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              size="lg"
              className="group-data-[collapsible=icon]:justify-center"
            >
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-sidebar-accent text-sidebar-accent-foreground text-xs font-bold">
                M
              </div>
              <div className="flex flex-1 items-center justify-between group-data-[collapsible=icon]:hidden">
                <div className="flex flex-col">
                  <span className="text-xs font-medium">Current Mission</span>
                  <span className="text-[11px] text-sidebar-foreground/60">Demo LEO Mission</span>
                </div>
                <ChevronDown className="h-3.5 w-3.5 text-sidebar-foreground/60" />
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  )
}
