import type { DependencyDescription, Matcher, DependencySingleSelectorMatchResult } from "@boundaries/elements";
import type { Rule } from "eslint";
import type { EslintLiteralNode } from "../Elements";
import type { RuleOptionsWithPolicies, DependenciesPolicy, SettingsNormalized, RuleName } from "../Shared";
export type EvaluatePoliciesResult = {
    allowed: true;
} | {
    allowed: false;
    /** Index into `rules[]` of the rule that produced the result, or null if no rule matched. */
    ruleIndex: number | null;
    /** The match result from the selector that triggered the outcome, or null when no rule matched. */
    matchResult: DependencySingleSelectorMatchResult | null;
};
/**
 * Evaluates the configured rules against a dependency description using a simplified path
 * that delegates all matching entirely to the elements package.
 *
 * For each rule, the outer `from`/`to`/`dependency` fields are merged with each entry in
 * `allow`/`disallow` to build the final {@link DependencySelectorNormalized}. Rules follow
 * **last-write-wins** semantics: the last rule that produces a match determines the outcome.
 * Within a single rule, `disallow`/`deny` takes precedence over `allow` — `allow` is not
 * evaluated when `disallow` already matched.
 */
export declare function evaluatePolicies(rules: DependenciesPolicy[], dep: DependencyDescription, matcher: Matcher, settings: SettingsNormalized): EvaluatePoliciesResult;
/**
 * Resolves the custom error message for a violation, preferring the policy-specific message
 * over the global options message.
 */
export declare function resolveCustomMessage(ruleIndex: number | null, ruleOptions: RuleOptionsWithPolicies): string | undefined;
type BuildErrorMessageParams = {
    matchResult: DependencySingleSelectorMatchResult | null;
    ruleIndex: number | null;
    customMessage: string | undefined;
    dependency: DependencyDescription;
};
/**
 * Builds the error message for a dependency violation.
 */
export declare function buildErrorMessage({ matchResult, ruleIndex, customMessage, dependency, }: BuildErrorMessageParams): string;
/**
 * Evaluates configured rules for a dependency and reports ESLint violations.
 *
 * @param params - Rule evaluation context and dependency information.
 */
export declare function evaluatePoliciesAndReport({ rules, dependency, settings, context, node, options, }: {
    rules: DependenciesPolicy[];
    settings: SettingsNormalized;
    context: Rule.RuleContext;
    node: EslintLiteralNode;
    options?: RuleOptionsWithPolicies;
    dependency: DependencyDescription;
}): void;
/**
 * Returns an ESLint rule definition for the dependencies rule, which checks dependencies between elements based on configured rules.
 * @param customRuleName - Optional custom name for the rule.
 * @returns ESLint rule definition.
 */
export default function getDependencyRule(ruleName?: RuleName): Rule.RuleModule;
export {};
