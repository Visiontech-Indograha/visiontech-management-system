import type { ComponentProps } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../atoms/Tabs";

/**
 * Molekul Tabs untuk Organism (docs/33 §2):
 * TabsBlock > TabsBlockList > TabsBlockTrigger / TabsBlockContent
 */
export function TabsBlock(props: ComponentProps<typeof Tabs>) {
  return <Tabs {...props} />;
}

export function TabsBlockList(props: ComponentProps<typeof TabsList>) {
  return <TabsList {...props} />;
}

export function TabsBlockTrigger(props: ComponentProps<typeof TabsTrigger>) {
  return <TabsTrigger {...props} />;
}

export function TabsBlockContent(props: ComponentProps<typeof TabsContent>) {
  return <TabsContent {...props} />;
}
