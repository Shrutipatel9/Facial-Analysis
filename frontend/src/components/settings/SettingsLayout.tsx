"use client"

import { KeyRound, Receipt, UserRound } from "lucide-react"
import { useState } from "react"

import { AccountInfoSection } from "./AccountInfoSection"
import { BillingSection } from "./BillingSection"
import { PasswordSection } from "./PasswordSection"
import {
  workspaceAsideClassName,
  workspaceAsideHeader,
  workspaceNavItemClassName,
  workspacePanelScrollClassName,
  workspaceShellClassName,
  workspaceUnifiedPanelClassName,
} from "@/components/layout/workspaceChrome"

type SettingsSection = "account" | "password" | "billing"

const NAV_ITEMS: { section: SettingsSection; label: string; icon: typeof UserRound }[] = [
  { section: "account", label: "Account Info", icon: UserRound },
  { section: "password", label: "Password", icon: KeyRound },
  { section: "billing", label: "Billing", icon: Receipt },
]

/**
 * Settings: same unified padded container as Report / AI Visuals.
 */
export function SettingsLayout() {
  const [activeSection, setActiveSection] = useState<SettingsSection>("account")

  return (
    <section className={workspaceShellClassName()}>
      <div className={workspaceUnifiedPanelClassName()}>
        <aside className={workspaceAsideClassName()}>
          {workspaceAsideHeader("Settings")}
          <nav className="flex flex-col gap-1 pb-4" aria-label="Settings sections">
            {NAV_ITEMS.map((item) => {
              const isActive = item.section === activeSection
              const Icon = item.icon
              return (
                <button
                  key={item.section}
                  type="button"
                  onClick={() => setActiveSection(item.section)}
                  className={workspaceNavItemClassName(isActive)}
                  aria-current={isActive ? "true" : undefined}
                >
                  <Icon className="size-4 shrink-0" aria-hidden />
                  <span className="truncate">{item.label}</span>
                </button>
              )
            })}
          </nav>
        </aside>

        <div className={workspacePanelScrollClassName()}>
          <div className="mx-auto w-full max-w-xl">
            {activeSection === "account" ? <AccountInfoSection /> : null}
            {activeSection === "password" ? <PasswordSection /> : null}
            {activeSection === "billing" ? <BillingSection /> : null}
          </div>
        </div>
      </div>
    </section>
  )
}
