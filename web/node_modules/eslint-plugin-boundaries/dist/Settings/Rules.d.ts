import type { MicromatchPatternNullable } from "@boundaries/elements";
import type { RuleOptionsPolicies, RuleOptionsWithPolicies, RuleMainKey, RuleShortName, RuleEffect, RuleName } from "../Shared/Settings.types";
type JsonSchemaPrimitive = string | number | boolean | null;
type JsonSchemaValue = JsonSchemaPrimitive | JsonSchemaObject | JsonSchemaValue[];
type JsonSchemaObject = {
    [key: string]: JsonSchemaValue;
};
/**
 * Builds JSON schema for legacy policy selectors.
 *
 * @param matcherOptions - Extra matcher options accepted in legacy tuple syntax.
 * @returns JSON schema definition for legacy policy values.
 */
export declare function legacyPoliciesSchema(matcherOptions?: JsonSchemaObject): {
    anyOf: ({
        type: string;
        items?: undefined;
    } | {
        type: string;
        items: JsonSchemaObject[];
    } | {
        type: string;
        items: {
            anyOf: ({
                type: string;
                items?: undefined;
            } | {
                type: string;
                items: JsonSchemaObject[];
            })[];
        };
    })[];
};
/**
 * Builds JSON schema for rule options of dependency-based rules.
 *
 * @param options - Schema customization options for rule main key and extras.
 * @returns ESLint-compatible schema array for rule options.
 */
export declare function rulesOptionsSchema({ rulesMainKey: mainKey, targetMatcherOptions, extraOptionsSchema, isLegacy, }?: {
    rulesMainKey?: RuleMainKey;
    targetMatcherOptions?: JsonSchemaObject;
    extraOptionsSchema?: Record<string, JsonSchemaObject>;
    isLegacy?: boolean;
}): JsonSchemaObject[];
/**
 * Type guard to check if a value is a valid RuleEffect.
 * @param value - The value to check.
 * @returns True if the value is a valid RuleEffect, false otherwise.
 */
export declare function isRuleEffect(value: unknown): value is RuleEffect;
/**
 * Type guard to check if a value is a valid RuleEffect.
 * @deprecated Use `isRuleEffect` instead.
 * @param value - The value to check.
 * @returns True if the value is a valid RuleEffect, false otherwise.
 */
export declare const isRulePolicy: typeof isRuleEffect;
/**
 * Type guard to check if a value is a valid rule name including the default plugin prefix.
 * @param value - The value to check.
 * @returns True if the value is a valid rule name with the default plugin prefix, false otherwise.
 */
export declare function isRuleName(value: unknown): value is RuleName;
/**
 * Type guard to check if a value is a valid rule short name.
 * @param value - The value to check.
 * @returns True if the value is a valid rule short name, false otherwise.
 */
export declare function isRuleShortName(value: unknown): value is RuleShortName;
/**
 * Detects if legacy template syntax is used in selectors.
 * @param selector - The selector to check (can be a single selector or an array of selectors).
 * @returns True if legacy template syntax was detected, false otherwise.
 */
export declare function detectLegacyTemplateSyntax(micromatchPattern: MicromatchPatternNullable | Record<string, MicromatchPatternNullable>): boolean;
/**
 * Returns the canonical main selector key used by schema and option checks.
 *
 * @param key - Optional rule main key (`from`, `to`, or `target`).
 * @returns The same key with default fallback to `from`.
 */
export declare function rulesMainKey(key?: RuleMainKey): RuleMainKey;
type RuleWarningIndexes = {
    rulesWithLegacyStringSelector: number[];
    rulesWithLegacyTupleSelector: number[];
    rulesWithLegacyFlatElementSelector: number[];
    rulesWithUnclassifiedLegacySelector: number[];
    rulesWithUnwrappedPolicyTarget: number[];
    rulesWithLegacyTemplate: number[];
    rulesWithDeprecatedImportKind: number[];
    rulesWithDeprecatedV7SelectorProps: number[];
    rulesWithDeprecatedDependencyModule: number[];
    rulesWithDeprecatedInternalPath: number[];
};
/**
 * Collects indices of rules using deprecated selector/template/importKind syntax.
 *
 * @param rules - Rule list to inspect.
 * @param ruleName - Rule name used to scope `allow`/`disallow` scanning.
 * @returns Rule indices grouped by deprecated syntax type.
 */
export declare function collectRuleWarningIndexes(rules: RuleOptionsPolicies[], ruleName: RuleName): RuleWarningIndexes;
/**
 * Warns once when deprecated selector/template syntax is detected in policies, and when the
 * deprecated `rules` option alias is used instead of `policies`.
 *
 * @param options - Rule options containing `policies` (or the deprecated `rules` alias) entries.
 * @param ruleName - Rule name displayed in warning messages.
 */
export declare function validateAndWarnRuleOptions(options: RuleOptionsWithPolicies | undefined, ruleName: RuleName, legacyWarnings: boolean): void;
/**
 * Warns about the deprecation of a rule and encourages migration to the "dependencies" rule.
 * @param ruleName The name of the deprecated rule.
 */
export declare function warnMigrationToDependencies(ruleName: RuleName): void;
export {};
