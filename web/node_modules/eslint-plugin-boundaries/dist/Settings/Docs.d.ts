import type { Rule } from "eslint";
import type { RuleName } from "../Shared/Settings.types";
/**
 * Returns the documentation URL for an ESLint rule.
 * @param ruleName The name of the rule.
 * @param anchor Optional anchor to a specific section in the documentation page.
 * @returns The documentation URL for the ESLint rule.
 */
export declare function docsUrl(path: string, anchor?: string): string;
/**
 * Returns the documentation path for a given rule name.
 * @param ruleName The name of the rule.
 * @returns The documentation path for the given rule name.
 */
export declare function getRuleDocsPath(ruleName: RuleName): string;
/**
 * Returns the documentation URL for an ESLint rule.
 * @param ruleName The name of the rule.
 * @param anchor Optional anchor to a specific section in the documentation page.
 * @returns The documentation URL for the ESLint rule.
 */
export declare function ruleDocsUrl(ruleName: RuleName, anchor?: string): string;
/**
 * Returns a "more info" message with the documentation URL for a given path.
 * @param path The path to the documentation page.
 * @param anchor Optional anchor to a specific section in the documentation page.
 * @returns A message containing the documentation URL.
 */
export declare function moreInfoLink(path: string, anchor?: string): string;
/**
 * Returns a migration guide link for a specific version upgrade.
 * @param versionFrom - The version being upgraded from.
 * @param versionTo - The version being upgraded to.
 * @param anchor - Optional anchor to a specific section in the migration guide.
 * @returns A message containing the migration guide URL for the specified version upgrade.
 */
export declare function migrationGuideLink(versionFrom: string, versionTo: string, anchor?: string): string;
/**
 * Returns a migration guide link for upgrading from version 5 to version 6.
 * @param anchor - Optional anchor to a specific section in the migration guide.
 * @returns A message containing the migration guide URL for upgrading from version 5 to version 6.
 */
export declare function migrationToV6GuideLink(anchor?: string): string;
/**
 * Returns a migration guide link for upgrading from version 1 to version 2.
 * @param anchor - Optional anchor to a specific section in the migration guide.
 * @returns A message containing the migration guide URL for upgrading from version 1 to version 2.
 */
export declare function migrationToV2GuideLink(anchor?: string): string;
/**
 * Returns a migration guide link for upgrading from version 6 to version 7.
 * @param anchor - Optional anchor to a specific section in the migration guide.
 * @returns A message containing the migration guide URL for upgrading from version 6 to version 7.
 */
export declare function migrationToV7GuideLink(anchor?: string): string;
/**
 * Returns a settings information link for the plugin settings documentation.
 * @param anchor - Optional anchor to a specific section in the settings documentation.
 * @returns A message containing the settings information URL for the plugin settings documentation.
 */
export declare function moreInfoSettingsLink(anchor?: string): string;
/**
 * Returns a "more info" message linking to the element descriptors documentation page.
 * @param anchor - Optional anchor to a specific section in the documentation page.
 * @returns A message containing the elements documentation URL.
 */
export declare function moreInfoElementsLink(anchor?: string): string;
/**
 * Returns a "more info" message linking to the legacy settings documentation page.
 * @param anchor - Optional anchor to a specific section in the documentation page.
 * @returns A message containing the legacy settings documentation URL.
 */
export declare function moreInfoLegacySettingsLink(anchor?: string): string;
/**
 * Returns a "more info" message linking to the entity selectors documentation page.
 * @param anchor - Optional anchor to a specific section in the documentation page.
 * @returns A message containing the entity selectors documentation URL.
 */
export declare function moreInfoSelectorsLink(anchor?: string): string;
/**
 * Builds the ESLint `meta.deprecated` info object for a rule replaced by another rule name
 * (e.g. a rename), so editors/tools can surface the deprecation without relying on the
 * runtime `warnOnce` message.
 * @param replacedByRuleName - The rule name that replaces the deprecated one.
 * @returns The `deprecated` metadata object consumed by ESLint's rule `meta`.
 */
export declare function deprecatedRuleInfo(replacedByRuleName: RuleName): Rule.RuleMetaData["deprecated"];
