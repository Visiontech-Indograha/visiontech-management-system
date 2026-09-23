import type { ElementDescriptors, DependencySelectorNormalized } from "@boundaries/elements";
import type { Rule } from "eslint";
import type { DependencyNodeKey, DependencyNodeSelector, SettingsNormalized, SettingsKey } from "../Shared/Settings.types";
/**
 * Type guard to check if a value is a valid key for the plugin settings.
 * @param value - The value to check.
 * @returns True if the value is a valid settings key, false otherwise.
 */
export declare function isSettingsKey(value: unknown): value is SettingsKey;
/**
 * Type guard to check if a value is a valid DependencyNodeKey.
 * @param value The value to check.
 * @returns True if the value is a valid DependencyNodeKey, false otherwise.
 */
export declare function isDependencyNodeKey(value: unknown): value is DependencyNodeKey;
/**
 * Type guard for legacy element descriptors declared as plain strings.
 *
 * @param type - Value to check.
 * @returns `true` when the value is a legacy string descriptor.
 */
export declare function isLegacyElementDescriptorType(type: unknown): type is string;
/**
 * Converts legacy string element descriptors into object descriptors.
 *
 * @param typesFromSettings - Raw `boundaries/elements` setting value.
 * @returns Normalized element descriptors compatible with current matcher API.
 */
export declare function transformLegacyTypes(typesFromSettings?: string[] | ElementDescriptors): ElementDescriptors;
/**
 * Validates one custom dependency-node selector object.
 *
 * @param selector - Candidate additional dependency node selector.
 * @returns `true` when selector has a valid shape.
 */
export declare function isValidDependencyNodeSelector(selector: unknown): selector is DependencyNodeSelector;
/**
 * Emits deprecation warning for legacy `types` setting.
 *
 * @param types - Legacy types setting value when present.
 * @param legacyWarnings - When `false`, skips detection and warning entirely.
 * @returns `true` when a legacy pattern was present.
 */
export declare function deprecateTypes(types: unknown, legacyWarnings: boolean): boolean;
/**
 * Emits deprecation warning for legacy `alias` setting.
 *
 * @param alias - Legacy alias setting value when present.
 * @param legacyWarnings - When `false`, skips detection and warning entirely.
 * @returns `true` when a legacy pattern was present.
 */
export declare function deprecateAlias(alias: unknown, legacyWarnings: boolean): boolean;
/**
 * Validates debug filter selectors for files or dependencies.
 *
 * @param value - Raw filter value.
 * @param filterName - Filter key used in warning messages.
 * @returns Filter array when valid, otherwise `undefined`.
 */
export declare function validateDebugFilterSelectors(value: unknown, filterName: "files" | "dependencies"): import("@boundaries/elements").FileSelectorNormalized | import("@boundaries/elements").EntitySelectorNormalized | undefined;
/**
 * Validates debug `files` filter selector list.
 *
 * @param value - Raw `debug.filter.files` setting value.
 * @returns Valid files filter selectors.
 */
export declare function validateDebugFilesFilter(value: unknown): import("@boundaries/elements").FileSelectorNormalized | import("@boundaries/elements").EntitySelectorNormalized | undefined;
/**
 * Validates debug `dependencies` filter selector list.
 *
 * @param value - Raw `debug.filter.dependencies` setting value.
 * @returns Valid dependency filter selectors.
 */
export declare function validateDebugDependenciesFilter(value: unknown): DependencySelectorNormalized | undefined;
/**
 * Returns normalized and cached settings from ESLint rule context.
 *
 * @param context - ESLint rule context.
 * @returns Normalized settings object used by rules.
 */
export declare function getSettings(context: Rule.RuleContext): SettingsNormalized;
