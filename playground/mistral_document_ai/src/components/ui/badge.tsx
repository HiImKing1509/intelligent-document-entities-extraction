import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export type BadgeProps = HTMLAttributes<HTMLDivElement> & {
  variant?: "default" | "secondary" | "outline";
};

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border border-transparent px-2.5 py-0.5 text-xs font-medium",
        variant === "default" && "bg-primary/20 text-primary-foreground",
        variant === "secondary" && "bg-secondary/60 text-secondary-foreground",
        variant === "outline" && "border-border text-neutral-300",
        className
      )}
      {...props}
    />
  );
}
