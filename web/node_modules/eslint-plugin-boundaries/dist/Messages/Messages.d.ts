import type { DependencyDescription, DependencySingleSelectorMatchResult, ElementDescription, ElementParent } from "@boundaries/elements";
/**
 * Describes elements using the selected relevant properties.
 * @param elementDescription - Element to describe.
 * @param properties - List of element properties to include in the description.
 * @param options - Additional options for message formatting.
 * @param options.singleElement - If `true`, uses singular "element" label instead of "elements of".
 * @returns Formatted message describing the element based on the selected properties.
 */
export declare function elementDescriptionMessage(elementDescription: ElementDescription | ElementParent, properties: string[], { singleElement, includeNullValues, }?: {
    singleElement?: boolean;
    includeNullValues?: boolean;
}): string;
/**
 * Builds the default message for dependencies rule violations from the matching selector data.
 * @param matchResult - Result of matching the dependency against the rule's selector, containing the relevant selector data for the from/to elements and the dependency metadata.
 * @param ruleIndex - Index of the matching rule.
 * @param dependency - Described dependency that triggered the violation, used to extract element and dependency metadata for message construction.
 * @returns Formatted error message describing the violation based on the matching selector data.
 */
export declare function dependenciesRuleMatchedMessage(matchResult: DependencySingleSelectorMatchResult | null, ruleIndex: number, dependency: DependencyDescription): string;
/**
 * Builds the default message for dependencies rule violations from the matching selector data.
 * @param matchResult - Result of matching the dependency against the rule's selector, containing the relevant selector data for the from/to elements and the dependency metadata.
 * @param ruleIndex - Index of the matching rule.
 * @param dependency - Described dependency that triggered the violation, used to extract element and dependency metadata for message construction.
 * @returns Formatted error message describing the violation based on the matching selector data.
 */
export declare function dependenciesRuleDefaultErrorMessage(matchResult: DependencySingleSelectorMatchResult | null, ruleIndex: number | null, dependency: DependencyDescription): string;
