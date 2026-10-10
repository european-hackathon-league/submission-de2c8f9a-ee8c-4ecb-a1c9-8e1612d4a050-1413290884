"use client";

import { useState } from "react";
import { HugeiconsIcon } from "@hugeicons/react";
import { AiChat02Icon, SentIcon, SidebarRightIcon } from "@hugeicons/core-free-icons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// ponytail: UI shell only; wire to an /api/chat route once the explain agent is ported.
export function ChatPanel() {
  const [open, setOpen] = useState(true);
  return (
    <aside
      data-open={open}
      className="sticky top-0 hidden h-svh shrink-0 flex-col py-2 pr-2 text-sidebar-foreground transition-[width] duration-200 data-[open=false]:w-12 data-[open=true]:w-80 lg:flex"
    >
      <div className="flex h-12 items-center gap-2 px-2">
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label={open ? "Collapse chat" : "Expand chat"}
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          <HugeiconsIcon icon={open ? SidebarRightIcon : AiChat02Icon} strokeWidth={2} />
        </Button>
        {open && <span className="text-sm font-medium">Ask about this view</span>}
      </div>
      {open && (
        <>
          <div className="flex flex-1 items-center justify-center p-4 text-center text-sm text-muted-foreground">
            Chat with the analysis is coming soon. It will answer with citations to the feedback
            shown here.
          </div>
          <form className="flex gap-2 p-2" onSubmit={(e) => e.preventDefault()}>
            <Input placeholder="Ask a question…" disabled aria-label="Chat message" />
            <Button size="icon" disabled aria-label="Send">
              <HugeiconsIcon icon={SentIcon} strokeWidth={2} />
            </Button>
          </form>
        </>
      )}
    </aside>
  );
}
