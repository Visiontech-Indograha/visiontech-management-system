import type { RuleName } from "../Shared";
/**
 * Returns the `no-unknown-dependencies` rule, which prevents dependencies to targets
 * that are not recognized by any element or file descriptor.
 *
 * The `require` option controls which classification axes the target must be known
 * on for the dependency to be considered valid:
 * - `"any"` (default): known on at least one axis (element or file) is enough.
 *   Reported only when the target is unknown on both axes.
 * - `"element"`: the element axis must be known, regardless of the file axis.
 *   Reported when the target element is unknown.
 * - `"file"`: the file axis must be known, regardless of the element axis.
 *   Reported when the target file is unknown.
 * - `"all"`: both axes must be known. Reported when either axis is unknown.
 *
 * @param ruleName - Rule name to build the rule for. Defaults to the canonical name.
 *   When the deprecated `no-unknown` name is used, a one-time rename warning is emitted.
 * @returns ESLint rule definition.
 */
export default function getNoUnknownDependenciesRule(ruleName?: RuleName): import("eslint").Rule.RuleModule;
