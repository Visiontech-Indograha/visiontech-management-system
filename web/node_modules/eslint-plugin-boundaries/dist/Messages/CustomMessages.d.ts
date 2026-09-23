import type { ElementParent, DependencyDescription, ElementDescription, DependencySingleSelectorMatchResult, ModuleDescription } from "@boundaries/elements";
/**
 * Replaces all occurrences of a placeholder key in a template string.
 *
 * Placeholders use the `${key}` syntax and optionally support namespacing
 * (for example `${from.type}` or `${dependency.parent.category}`).
 *
 * @param template - Message template where placeholders are replaced.
 * @param key - Placeholder key to replace (without `${}` delimiters).
 * @param value - Value injected in place of the placeholder.
 * @param namespace - Optional namespace prepended to the key before replacing.
 * @returns Template string with the requested placeholder replaced.
 */
export declare function replaceObjectValueInLegacyTemplate(template: string, key: string, value: string, namespace?: string | null): string;
/**
 * Creates the replacement context consumed by legacy `${...}` placeholders.
 *
 * The resulting object normalizes available element information and dependency
 * metadata so templates can use keys consistently regardless of source.
 *
 * @param element - Element or parent element that provides captured values.
 * @param importKind - Dependency kind (`value`, `type`, etc.).
 * @param dependencyInfo - Extra dependency metadata for full elements.
 * @returns Normalized key/value map used during placeholder replacement.
 */
export declare function elementPropertiesToReplaceInLegacyTemplate({ element, module: moduleName, dependency, }: {
    element: ElementDescription;
    module?: ModuleDescription;
    dependency?: DependencyDescription["dependency"];
}): {
    type: string;
    internalPath: string;
    source: string;
    module: string;
    importKind: string;
};
export declare function parentPropertiesToReplaceInLegacyTemplate({ parent, dependency, }: {
    parent: ElementParent;
    dependency?: DependencyDescription["dependency"];
}): {
    type: string;
    internalPath: string;
    source: string;
    module: string;
    importKind: string;
};
/**
 * Builds the final custom error message for a dependency violation.
 *
 * This function first resolves legacy `${...}` placeholders (`file`, `from`,
 * `dependency`, `target`, and parent variants) and then evaluates optional
 * Handlebars expressions with the same dependency context.
 *
 * @param template - User-defined message template from rule configuration.
 * @param dependency - Runtime dependency information used by placeholders.
 * @returns Rendered, user-facing error message.
 */
export declare function customErrorMessage(template: string, dependency: DependencyDescription, ruleIndex?: number | null, matchResult?: DependencySingleSelectorMatchResult | null): string;
