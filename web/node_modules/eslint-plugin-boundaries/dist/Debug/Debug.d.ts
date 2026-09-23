import type { DependencyDescription, Matcher, EntityDescription, DependencySingleSelectorMatchResult } from "@boundaries/elements";
import type { SettingsNormalized } from "../Shared";
/**
 * Prints a warning message using warning color.
 * @param title - Warning title shown before message.
 * @param message - Warning message.
 */
export declare function warn(title: string, message?: string): void;
/**
 * Prints a warning only once for each unique message.
 *
 * @param title - Warning title shown before message.
 * @param message - Warning message candidate.
 * @returns `true` when warning was emitted, `false` when skipped.
 */
export declare function warnOnce(title: string, message?: string): boolean;
/**
 * Emits debug output for file or dependency descriptions when enabled.
 *
 * @param description - Element or dependency description to debug.
 * @param settings - Normalized plugin settings including debug filters.
 * @param matcher - Matcher used to evaluate debug filters.
 */
export declare function debugDescription(description: EntityDescription | DependencyDescription, settings: SettingsNormalized, matcher: Matcher): void;
/**
 * Prints debug information for a rule result when debug mode is enabled
 *
 * @param dependencyMatchResult - The result of matching a dependency against rules, including match status and captured values.
 * @param ruleIndex - The index of the rule that was matched, if any.
 * @param dependency - The original dependency description that was evaluated against the rules.
 * @param settings - Normalized plugin settings including debug filters.
 * @param matcher - Matcher used to evaluate debug filters.
 */
export declare function printDependenciesRuleResult(dependencyMatchResult: DependencySingleSelectorMatchResult | null, ruleIndex: number | null, dependency: DependencyDescription, settings: SettingsNormalized, matcher: Matcher): void;
