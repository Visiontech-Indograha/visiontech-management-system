import type { Rule } from "eslint";
import type { RuleOptions, RuleMetaDefinition } from "../../Shared";
import type { DependencyRuleRunner, DependencyRuleOptions } from "./DependencyRule.types";
/**
 * Creates a rule module that evaluates dependency nodes using shared matcher logic.
 *
 * @param ruleMeta - Metadata used to build ESLint rule `meta` information.
 * @param rule - Rule runner invoked for each described dependency.
 * @param ruleOptions - Optional behavior flags for validation and rule shape.
 * @returns ESLint rule module ready to be exported by concrete rules.
 */
export declare function dependencyRule<Options extends RuleOptions>(ruleMeta: RuleMetaDefinition, rule: DependencyRuleRunner<Options>, ruleOptions?: DependencyRuleOptions): Rule.RuleModule;
