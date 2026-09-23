import type { RuleName } from "../Shared";
/**
 * Returns the `no-ignored-dependencies` rule, which prevents recognized elements from
 * importing ignored files.
 *
 * @param ruleName - Rule name to build the rule for. Defaults to the canonical name.
 *   When the deprecated `no-ignored` name is used, a one-time rename warning is emitted.
 * @returns ESLint rule definition.
 */
export default function getNoIgnoredDependenciesRule(ruleName?: RuleName): import("eslint").Rule.RuleModule;
