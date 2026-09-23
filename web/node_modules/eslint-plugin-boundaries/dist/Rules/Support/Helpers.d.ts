import type { Rule } from "eslint";
import type { RuleMetaDefinition } from "../../Shared";
/**
 * Returns the meta object for an ESLint rule.
 * @param options The rule metadata definition.
 * @param options.description The description of the rule.
 * @param options.schema The JSON schema for rule options validation.
 * @param options.ruleName The name of the rule.
 * @param options.type The type of the rule (problem, suggestion, or layout).
 * @returns The meta object for the ESLint rule.
 */
export declare function meta({ description, schema, ruleName, type, deprecated, }: RuleMetaDefinition): Pick<Rule.RuleModule, "meta">;
