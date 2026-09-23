import type { DependencyKind, ElementDescriptors, FlagAsExternalOptions, MicromatchPatternNullable, BackwardCompatibleEntitySelector, FileDescriptors, FileSelector, FileSelectorNormalized, DependencySelectorNormalized, BackwardCompatibleDependencyInfoSelector, BackwardCompatibleDependencySelector, DependencyInfoSelectorNormalized, EntitySelectorNormalized } from "@boundaries/elements";
import type { ESLint, Linter, Rule } from "eslint";
export declare const PLUGIN_NAME: "boundaries";
export declare const PLUGIN_ENV_VARS_PREFIX: "ESLINT_PLUGIN_BOUNDARIES";
export declare const REPO_URL: "https://github.com/javierbrea/eslint-plugin-boundaries";
export declare const WEBSITE_URL: "https://www.jsboundaries.dev";
export declare const PLUGIN_ISSUES_URL: "https://github.com/javierbrea/eslint-plugin-boundaries/issues";
export declare const DEPENDENCY_NODE_REQUIRE: "require";
export declare const DEPENDENCY_NODE_IMPORT: "import";
export declare const DEPENDENCY_NODE_DYNAMIC_IMPORT: "dynamic-import";
export declare const DEPENDENCY_NODE_EXPORT: "export";
/** @deprecated Use DEPENDENCIES instead */
export declare const ELEMENT_TYPES: "element-types";
export declare const DEPENDENCIES: "dependencies";
export declare const ENTRY_POINT: "entry-point";
export declare const EXTERNAL: "external";
export declare const NO_IGNORED_DEPENDENCIES: "no-ignored-dependencies";
/** @deprecated Use NO_IGNORED_DEPENDENCIES instead */
export declare const NO_IGNORED: "no-ignored";
export declare const NO_PRIVATE: "no-private";
export declare const NO_UNKNOWN_FILES: "no-unknown-files";
export declare const NO_UNKNOWN_DEPENDENCIES: "no-unknown-dependencies";
/** @deprecated Use NO_UNKNOWN_DEPENDENCIES instead */
export declare const NO_UNKNOWN: "no-unknown";
/**
 * Map of all rule short names, without the plugin prefix.
 */
export declare const RULE_SHORT_NAMES_MAP: {
    /** @deprecated Use DEPENDENCIES instead */
    readonly ELEMENT_TYPES: "element-types";
    readonly DEPENDENCIES: "dependencies";
    readonly ENTRY_POINT: "entry-point";
    readonly EXTERNAL: "external";
    readonly NO_IGNORED_DEPENDENCIES: "no-ignored-dependencies";
    /** @deprecated Use NO_IGNORED_DEPENDENCIES instead */
    readonly NO_IGNORED: "no-ignored";
    readonly NO_PRIVATE: "no-private";
    readonly NO_UNKNOWN_FILES: "no-unknown-files";
    readonly NO_UNKNOWN_DEPENDENCIES: "no-unknown-dependencies";
    /** @deprecated Use NO_UNKNOWN_DEPENDENCIES instead */
    readonly NO_UNKNOWN: "no-unknown";
};
/**
 * Map of all rule names, including the default plugin prefix.
 */
export declare const RULE_NAMES_MAP: {
    /** @deprecated Use DEPENDENCIES instead */
    readonly ELEMENT_TYPES: "boundaries/element-types";
    readonly DEPENDENCIES: "boundaries/dependencies";
    readonly ENTRY_POINT: "boundaries/entry-point";
    readonly EXTERNAL: "boundaries/external";
    readonly NO_IGNORED_DEPENDENCIES: "boundaries/no-ignored-dependencies";
    /** @deprecated Use NO_IGNORED_DEPENDENCIES instead */
    readonly NO_IGNORED: "boundaries/no-ignored";
    readonly NO_PRIVATE: "boundaries/no-private";
    readonly NO_UNKNOWN_FILES: "boundaries/no-unknown-files";
    readonly NO_UNKNOWN_DEPENDENCIES: "boundaries/no-unknown-dependencies";
    /** @deprecated Use NO_UNKNOWN_DEPENDENCIES instead */
    readonly NO_UNKNOWN: "boundaries/no-unknown";
};
/**
 * List of all rule names
 */
export declare const RULE_NAMES: readonly ("boundaries/element-types" | "boundaries/dependencies" | "boundaries/entry-point" | "boundaries/external" | "boundaries/no-ignored-dependencies" | "boundaries/no-ignored" | "boundaries/no-private" | "boundaries/no-unknown-files" | "boundaries/no-unknown-dependencies" | "boundaries/no-unknown")[];
/**
 * Type representing all valid rule names, including the default plugin prefix.
 */
export type RuleName = (typeof RULE_NAMES)[number];
/**
 * List of all rule names, including the default plugin prefix.
 */
export type RuleNames = typeof RULE_NAMES;
/**
 * List of all rule short names, without the plugin prefix.
 */
export declare const RULE_SHORT_NAMES: readonly ("element-types" | "dependencies" | "entry-point" | "external" | "no-ignored-dependencies" | "no-ignored" | "no-private" | "no-unknown-files" | "no-unknown-dependencies" | "no-unknown")[];
/**
 * Type representing all valid rule short names, without the plugin prefix.
 */
export type RuleShortName = (typeof RULE_SHORT_NAMES)[number];
/**
 * List of all rule short names, without the plugin prefix.
 */
export type RuleShortNames = typeof RULE_SHORT_NAMES;
/**
 * Different types of dependency nodes supported by the plugin by default.
 * Each type corresponds to a common way of importing or requiring modules in JavaScript/TypeScript.
 */
export declare const DEPENDENCY_NODE_KEYS_MAP: {
    /**
     * CommonJS require statements, e.g., `const module = require('module')`.
     */
    readonly REQUIRE: "require";
    /**
     * ES6 import statements, e.g., `import module from 'module'`.
     */
    readonly IMPORT: "import";
    /**
     * Dynamic import statements, e.g., `import('module')`.
     */
    readonly DYNAMIC_IMPORT: "dynamic-import";
    /**
     * Export statements, e.g., `export { module } from 'source'`.
     */
    readonly EXPORT: "export";
};
/**
 * Keys of the different types of dependency nodes supported by the plugin by default.
 */
export type DependencyNodeKey = (typeof DEPENDENCY_NODE_KEYS_MAP)[keyof typeof DEPENDENCY_NODE_KEYS_MAP];
/**
 * Additional custom dependency node selector to consider when analyzing dependencies.
 * Each entry defines a selector and its kind (either 'type' or 'value').
 * This allows for extending the default dependency nodes with project-specific patterns.
 */
export type DependencyNodeSelector = {
    /** A selector string to identify the dependency node in the AST */
    selector: string;
    /** The kind of import, either 'type' or 'value' */
    kind: DependencyKind;
    /** Name to assign to the dependency node. Useful to identify the kind of node selector in rules */
    name?: string;
};
export declare const SETTINGS: {
    readonly ELEMENTS: "boundaries/elements";
    /** @deprecated Use ELEMENTS_SINGLE_MATCH instead */
    readonly ELEMENTS_SINGLE_TYPE: "boundaries/elements-single-type";
    readonly ELEMENTS_SINGLE_MATCH: "boundaries/elements-single-match";
    readonly FILES_SINGLE_MATCH: "boundaries/files-single-match";
    readonly IGNORE: "boundaries/ignore";
    readonly INCLUDE: "boundaries/include";
    readonly ROOT_PATH: "boundaries/root-path";
    readonly DEPENDENCY_NODES: "boundaries/dependency-nodes";
    readonly ADDITIONAL_DEPENDENCY_NODES: "boundaries/additional-dependency-nodes";
    readonly LEGACY_TEMPLATES: "boundaries/legacy-templates";
    readonly CACHE: "boundaries/cache";
    readonly LEGACY_WARNINGS: "boundaries/legacy-warnings";
    readonly FLAG_AS_EXTERNAL: "boundaries/flag-as-external";
    readonly DEBUG_SETTING: "boundaries/debug";
    readonly DEBUG: "ESLINT_PLUGIN_BOUNDARIES_DEBUG";
    readonly ENV_ROOT_PATH: "ESLINT_PLUGIN_BOUNDARIES_ROOT_PATH";
    /** @deprecated Use RULE_DEPENDENCIES instead */
    readonly RULE_ELEMENT_TYPES: "boundaries/element-types";
    readonly RULE_DEPENDENCIES: "boundaries/dependencies";
    readonly RULE_ENTRY_POINT: "boundaries/entry-point";
    readonly RULE_EXTERNAL: "boundaries/external";
    readonly RULE_NO_IGNORED_DEPENDENCIES: "boundaries/no-ignored-dependencies";
    /** @deprecated Use RULE_NO_IGNORED_DEPENDENCIES instead */
    readonly RULE_NO_IGNORED: "boundaries/no-ignored";
    readonly RULE_NO_PRIVATE: "boundaries/no-private";
    readonly RULE_NO_UNKNOWN_FILES: "boundaries/no-unknown-files";
    readonly RULE_NO_UNKNOWN_DEPENDENCIES: "boundaries/no-unknown-dependencies";
    /** @deprecated Use RULE_NO_UNKNOWN_DEPENDENCIES instead */
    readonly RULE_NO_UNKNOWN: "boundaries/no-unknown";
    readonly TYPES: "boundaries/types";
    readonly ALIAS: "boundaries/alias";
    readonly FILES: "boundaries/files";
    readonly VALID_MODES: readonly ["folder", "file", "full"];
    readonly VALID_DEPENDENCY_NODE_KINDS: readonly ["value", "type", "typeof"];
    readonly DEFAULT_DEPENDENCY_NODES: {
        readonly require: readonly [{
            readonly selector: "CallExpression[callee.name=require] > Literal";
            readonly kind: "value";
            readonly name: "require";
        }];
        readonly import: readonly [{
            readonly selector: "ImportDeclaration:not([importKind=type]) > Literal";
            readonly kind: "value";
            readonly name: "import";
        }, {
            readonly selector: "ImportDeclaration[importKind=type] > Literal";
            readonly kind: "type";
            readonly name: "import";
        }];
        readonly "dynamic-import": readonly [{
            readonly selector: "ImportExpression > Literal";
            readonly kind: "value";
            readonly name: "dynamic-import";
        }];
        readonly export: readonly [{
            readonly selector: "ExportAllDeclaration:not([exportKind=type]) > Literal";
            readonly kind: "value";
            readonly name: "export";
        }, {
            readonly selector: "ExportAllDeclaration[exportKind=type] > Literal";
            readonly kind: "type";
            readonly name: "export";
        }, {
            readonly selector: "ExportNamedDeclaration:not([exportKind=type]) > Literal";
            readonly kind: "value";
            readonly name: "export";
        }, {
            readonly selector: "ExportNamedDeclaration[exportKind=type] > Literal";
            readonly kind: "type";
            readonly name: "export";
        }];
    };
};
/**
 * Map of the valid keys for the plugin settings.
 */
export declare const SETTINGS_KEYS_MAP: {
    readonly ELEMENTS: "boundaries/elements";
    /** @deprecated Use ELEMENTS_SINGLE_MATCH instead */
    readonly ELEMENTS_SINGLE_TYPE: "boundaries/elements-single-type";
    readonly ELEMENTS_SINGLE_MATCH: "boundaries/elements-single-match";
    readonly FILES_SINGLE_MATCH: "boundaries/files-single-match";
    readonly FILES: "boundaries/files";
    readonly IGNORE: "boundaries/ignore";
    readonly INCLUDE: "boundaries/include";
    readonly ROOT_PATH: "boundaries/root-path";
    readonly DEPENDENCY_NODES: "boundaries/dependency-nodes";
    readonly ADDITIONAL_DEPENDENCY_NODES: "boundaries/additional-dependency-nodes";
    readonly LEGACY_TEMPLATES: "boundaries/legacy-templates";
    /** @deprecated Use 'ELEMENTS' instead */
    readonly TYPES: "boundaries/types";
    /** @deprecated Use import/resolver settings instead */
    readonly ALIAS: "boundaries/alias";
    readonly CACHE: "boundaries/cache";
    readonly LEGACY_WARNINGS: "boundaries/legacy-warnings";
    readonly FLAG_AS_EXTERNAL: "boundaries/flag-as-external";
    readonly DEBUG: "boundaries/debug";
};
/**
 * Default value for the legacy templates setting.
 */
export declare const LEGACY_TEMPLATES_DEFAULT: true;
/**
 * Default value for the legacy-warnings setting.
 */
export declare const LEGACY_WARNINGS_DEFAULT: true;
/**
 * Default value for the elements single type/match setting.
 */
export declare const ELEMENTS_SINGLE_TYPE_DEFAULT: true;
/**
 * Default value for the files single match setting.
 */
export declare const FILES_SINGLE_MATCH_DEFAULT: false;
/**
 * Default value for the cache setting.
 */
export declare const CACHE_DEFAULT: true;
/**
 * Default value for the check-config setting.
 */
export declare const CHECK_CONFIG_DEFAULT: false;
/**
 * Valid keys for the plugin settings.
 */
export type SettingsKey = (typeof SETTINGS_KEYS_MAP)[keyof typeof SETTINGS_KEYS_MAP];
/**
 * List of glob patterns to include when analyzing dependencies.
 * If specified, only files matching these patterns will be included in the plugin analysis.
 */
export type IncludeSetting = string | string[];
/**
 * List of glob patterns to ignore when analyzing dependencies.
 * Files matching these patterns will be excluded from the plugin analysis.
 */
export type IgnoreSetting = string | string[];
/**
 * Root path of the project. This is used to resolve relative paths in element patterns.
 * Can also be set via the ESLINT_PLUGIN_BOUNDARIES_ROOT_PATH environment variable.
 */
export type RootPathSetting = string;
/**
 * Alias settings to define path aliases for module resolution.
 * Each key is an alias and its value is the corresponding path.
 * @deprecated Use "import/resolver" settings instead
 */
export type AliasSetting = Record<string, string>;
export type DebugFilterSetting = {
    /** File or entity selectors used to filter file debug messages */
    files?: FileSelector | BackwardCompatibleEntitySelector;
    /** Dependency selectors used to filter dependency debug messages */
    dependencies?: BackwardCompatibleEntitySelector;
};
export type DebugSetting = {
    /** Enables debug output when true */
    enabled?: boolean;
    /** Enables specific debug messages */
    messages?: {
        /** Whether to enable debug messages for files */
        files?: boolean;
        /** Whether to enable debug messages for dependencies */
        dependencies?: boolean;
        /** Whether to enable debug messages for rule violations */
        violations?: boolean;
    };
    /** Optional filters for file and dependency debug messages */
    filter?: DebugFilterSetting;
};
/**
 * Normalized debug setting.
 */
export type DebugSettingNormalized = {
    /** Whether debug mode is enabled */
    enabled: boolean;
    /** Settings to enable/disable specific debug messages */
    messages: {
        /** Whether to enable debug messages for files */
        files: boolean;
        /** Whether to enable debug messages for dependencies */
        dependencies: boolean;
        /** Whether to enable debug messages for rule violations */
        violations: boolean;
    };
    /** Debug filters **/
    filter: {
        /** File or entity selectors used to filter file debug messages */
        files?: FileSelectorNormalized | EntitySelectorNormalized;
        /** Dependency selectors used to filter dependency debug messages */
        dependencies?: DependencySelectorNormalized;
    };
};
/**
 * Settings for the eslint-plugin-boundaries plugin.
 */
export type Settings = {
    /**
     * Element descriptors to define the different elements (or layers) in your project.
     * Each element descriptor includes a type, a pattern to match files, and optional settings like mode and capture groups.
     */
    [SETTINGS_KEYS_MAP.ELEMENTS]?: ElementDescriptors;
    /**
     * @deprecated Use `boundaries/elements-single-match` instead. Kept as a backward-compatible alias;
     * `boundaries/elements-single-match` takes precedence when both are set.
     */
    [SETTINGS_KEYS_MAP.ELEMENTS_SINGLE_TYPE]?: boolean;
    /**
     * When `true` (default), each element is assigned only the first matching element descriptor's type.
     * When `false`, elements accumulate all matching descriptor types.
     */
    [SETTINGS_KEYS_MAP.ELEMENTS_SINGLE_MATCH]?: boolean;
    /**
     * When `true`, each file is assigned only the first matching file descriptor's category, and matching stops.
     * When `false` (default), files accumulate all matching descriptor categories.
     */
    [SETTINGS_KEYS_MAP.FILES_SINGLE_MATCH]?: boolean;
    /**
     * File descriptors to define specific file patterns and their associated metadata.
     * Each file descriptor includes a category and a pattern to match files, along with optional settings.
     */
    [SETTINGS_KEYS_MAP.FILES]?: FileDescriptors;
    /**
     * List of glob patterns to ignore when analyzing dependencies.
     * Files matching these patterns will be excluded from the plugin analysis.
     */
    [SETTINGS_KEYS_MAP.IGNORE]?: IgnoreSetting;
    /**
     * List of glob patterns to include when analyzing dependencies.
     * If specified, only files matching these patterns will be included in the plugin analysis.
     */
    [SETTINGS_KEYS_MAP.INCLUDE]?: IncludeSetting;
    /**
     * Root path of the project. This is used to resolve relative paths in element patterns.
     * Can also be set via the ESLINT_PLUGIN_BOUNDARIES_ROOT_PATH environment variable.
     */
    [SETTINGS_KEYS_MAP.ROOT_PATH]?: RootPathSetting;
    /**
     * Specifies which dependency nodes (import types) to consider when analyzing dependencies.
     * Each key corresponds to a type of dependency node (e.g., import, require, dynamic-import, export) and maps to an array of selectors defining how to identify those nodes in the AST.
     * If not specified, only 'import' nodes will be considered by default.
     */
    [SETTINGS_KEYS_MAP.DEPENDENCY_NODES]?: DependencyNodeKey[];
    /**
     * Additional custom dependency node selectors to consider when analyzing dependencies.
     * Each entry defines a selector and its kind (either 'type' or 'value').
     * This allows for extending the default dependency nodes with project-specific patterns.
     */
    [SETTINGS_KEYS_MAP.ADDITIONAL_DEPENDENCY_NODES]?: DependencyNodeSelector[];
    /**
     * Whether to enable legacy template syntax support (default: `true`, but it will be `false` in future major releases).
     * This enables:
     * - Using `${variable}` syntax in templates for backward compatibility
     * - Passing captured values from elements to template data at first object level. This might override existing keys in the elements data objects.
     */
    [SETTINGS_KEYS_MAP.LEGACY_TEMPLATES]?: boolean;
    /** @deprecated Use "boundaries/elements" setting instead */
    [SETTINGS_KEYS_MAP.TYPES]?: ElementDescriptors;
    /** @deprecated Use "import/resolver" setting instead */
    [SETTINGS_KEYS_MAP.ALIAS]?: AliasSetting;
    /** Whether to enable caching for the plugin analysis */
    [SETTINGS_KEYS_MAP.CACHE]?: boolean;
    /** When `false`, skips all legacy-pattern detection and suppresses deprecation warnings. Temporary option; will be removed when legacy support is dropped. */
    [SETTINGS_KEYS_MAP.LEGACY_WARNINGS]?: boolean;
    /** Configuration for categorizing dependencies as external or local */
    [SETTINGS_KEYS_MAP.FLAG_AS_EXTERNAL]?: FlagAsExternalOptions;
    /** Debug configuration for tracing files and dependencies */
    [SETTINGS_KEYS_MAP.DEBUG]?: DebugSetting;
};
/**
 * Normalized settings for the eslint-plugin-boundaries plugin.
 * All settings have default values applied.
 */
export type SettingsNormalized = {
    /** Element descriptors */
    elementDescriptors: ElementDescriptors;
    /** Whether each element should be assigned only the first matching descriptor's type */
    elementsSingleMatch: boolean;
    /** File descriptors */
    fileDescriptors: FileDescriptors;
    /** Whether each file should be assigned only the first matching descriptor's category */
    filesSingleMatch: boolean;
    /** List of glob patterns to ignore when analyzing dependencies */
    ignorePaths: string[] | undefined;
    /** List of glob patterns to include when analyzing dependencies */
    includePaths: string[] | undefined;
    /** Root path of the project */
    rootPath: string;
    /** Dependency nodes to consider when analyzing dependencies */
    dependencyNodes: DependencyNodeSelector[];
    /** Whether legacy template syntax support is enabled */
    legacyTemplates: boolean;
    /** Whether caching is enabled */
    cache: boolean;
    /** Whether legacy-pattern detection and deprecation warnings are enabled */
    legacyWarnings: boolean;
    /** Configuration for categorizing dependencies as external or local */
    flagAsExternal: FlagAsExternalOptions;
    /** Debug configuration */
    debug: DebugSettingNormalized;
};
/**
 * Eslint boundaries plugin rules.
 * By default, rule names are prefixed with "boundaries/", but it can be customized via the `PluginName` generic parameter.
 *
 * @template PluginName - The name of the plugin, defaults to "boundaries". It defines the prefix for the rule names.
 */
export type Rules<PluginName extends string = typeof PLUGIN_NAME> = {
    [K in `${PluginName}/${typeof ELEMENT_TYPES | typeof DEPENDENCIES | typeof ENTRY_POINT | typeof EXTERNAL | typeof NO_IGNORED_DEPENDENCIES | typeof NO_IGNORED | typeof NO_PRIVATE | typeof NO_UNKNOWN_FILES | typeof NO_UNKNOWN_DEPENDENCIES | typeof NO_UNKNOWN}`]?: K extends `${PluginName}/${typeof ELEMENT_TYPES}` ? Linter.RuleEntry<DependenciesRuleOptions[]> : K extends `${PluginName}/${typeof DEPENDENCIES}` ? Linter.RuleEntry<DependenciesRuleOptions[]> : K extends `${PluginName}/${typeof ENTRY_POINT}` ? Linter.RuleEntry<EntryPointRuleOptions[]> : K extends `${PluginName}/${typeof EXTERNAL}` ? Linter.RuleEntry<ExternalRuleOptions[]> : K extends `${PluginName}/${typeof NO_PRIVATE}` ? Linter.RuleEntry<NoPrivateOptions[]> : K extends `${PluginName}/${typeof NO_UNKNOWN_DEPENDENCIES | typeof NO_UNKNOWN}` ? Linter.RuleEntry<NoUnknownDependenciesOptions[]> : Linter.RuleEntry<never>;
};
export type FlagAsExternalBooleanOptionKey = "unresolvableAlias" | "inNodeModules" | "outsideRootPath";
/**
 * ESLint configuration with optional settings and rules specific to the boundaries plugin.
 */
export interface Config<PluginName extends string = typeof PLUGIN_NAME> extends Linter.Config {
    /**
     * Optional settings specific to the boundaries plugin.
     */
    settings?: Settings;
    /**
     * Optional rules specific to the boundaries plugin.
     */
    rules?: Rules<PluginName>;
}
/**
 * ESLint plugin interface for the boundaries plugin, including metadata, rules, and configurations.
 */
export interface PluginBoundaries extends ESLint.Plugin {
    meta: {
        name: string;
        version: string;
    };
    rules: Record<RuleShortName, Rule.RuleModule>;
    configs: {
        recommended: Config;
        strict: Config;
        "strict-legacy": Config;
    };
}
export type RuleMetaDefinition = {
    type?: Rule.RuleMetaData["type"];
    /** The description of the rule */
    description: string;
    /** The name of the rule */
    ruleName: RuleName;
    /** The schema of the rule options */
    schema?: Rule.RuleMetaData["schema"];
    /** Deprecation metadata surfaced by ESLint when the rule is deprecated */
    deprecated?: Rule.RuleMetaData["deprecated"];
};
export declare const RULE_EFFECT_ALLOW: "allow";
export declare const RULE_EFFECT_DISALLOW: "disallow";
/**
 * Map containing the available rule effects.
 */
export declare const RULE_EFFECTS_MAP: {
    readonly ALLOW: "allow";
    readonly DISALLOW: "disallow";
};
/**
 * Effect of a policy, either allowing or disallowing certain dependencies.
 */
export type RuleEffect = (typeof RULE_EFFECTS_MAP)[keyof typeof RULE_EFFECTS_MAP];
/** @deprecated Use `RULE_EFFECT_ALLOW` instead. */
export declare const RULE_POLICY_ALLOW: "allow";
/** @deprecated Use `RULE_EFFECT_DISALLOW` instead. */
export declare const RULE_POLICY_DISALLOW: "disallow";
/**
 * Map containing the available rule policies.
 * @deprecated Use `RULE_EFFECTS_MAP` instead.
 */
export declare const RULE_POLICIES_MAP: {
    readonly ALLOW: "allow";
    readonly DISALLOW: "disallow";
};
/**
 * Policy for rules, either allowing or disallowing certain dependencies.
 * @deprecated Use `RuleEffect` instead.
 */
export type RulePolicy = RuleEffect;
/**
 * Base options for some rules, including default effect and custom message.
 */
export type RuleBaseOptions = {
    /** Default effect for all the policies (allow or disallow) */
    default?: RuleEffect;
    /** Custom message for all rule violations. It can be overridden at the policy level. */
    message?: string;
};
/**
 * Policy that defines allowed or disallowed dependencies between different element types.
 */
export type DependenciesPolicy = {
    dependency?: BackwardCompatibleDependencyInfoSelector;
    /** Selectors of the source elements that the policy applies to (the elements importing) */
    from?: BackwardCompatibleEntitySelector;
    /** Selectors of the target elements that are disallowed to be imported */
    to?: BackwardCompatibleEntitySelector;
    /** Selectors of the elements that are disallowed to be imported */
    disallow?: BackwardCompatibleDependencySelector | BackwardCompatibleEntitySelector;
    /** Selectors of the elements that are allowed to be imported */
    allow?: BackwardCompatibleDependencySelector | BackwardCompatibleEntitySelector;
    /** Kind of import that the policy applies to (e.g., "type", "value") */
    importKind?: DependencyKind;
    /** Custom message for policy violations */
    message?: string;
};
/**
 * Policy that defines allowed or disallowed dependencies between different element types.
 * @deprecated Use `DependenciesPolicy` instead.
 */
export type DependenciesRule = DependenciesPolicy;
export type DependenciesPolicyNormalized = {
    dependency?: DependencyInfoSelectorNormalized;
    from?: EntitySelectorNormalized;
    to?: EntitySelectorNormalized;
    disallow?: DependencySelectorNormalized | EntitySelectorNormalized;
    allow?: DependencySelectorNormalized | EntitySelectorNormalized;
    importKind?: DependencyKind;
    message?: string;
};
/** @deprecated Use `DependenciesPolicyNormalized` instead. */
export type DependenciesRuleNormalized = DependenciesPolicyNormalized;
/**
 * Options for the dependencies rule, including default effect and specific policies.
 */
export type DependenciesRuleOptions = Omit<RuleBaseOptions, "policies" | "rules"> & {
    /** Specific policies for defining boundaries between elements */
    policies?: DependenciesPolicy[];
    /** Specific policies for defining boundaries between elements. @deprecated Use `policies` instead. */
    rules?: DependenciesPolicy[];
    /** Whether to check dependencies from all origins (including external and core) or only from local elements (default: `false`, only local). */
    checkAllOrigins?: boolean;
    /** Whether to check local dependencies with unknown elements (not matching any element descriptor) or to ignore them. (default: `false`, ignore them) */
    checkUnknownLocals?: boolean;
    /** Whether to check internal dependencies (dependencies within files in the same element) (default: `false`, ignore them) */
    checkInternals?: boolean;
};
/**
 * Policy that defines entry points for specific element types, controlling which files can be imported.
 */
export type EntryPointPolicy = {
    /** Selectors of the elements that the policy applies to (the elements being imported) */
    target: BackwardCompatibleEntitySelector;
    /** Micromatch patterns of the files that are disallowed to import from other elements. Relative to the element path */
    disallow?: string[];
    /** Micromatch patterns of the files that are allowed to import from other elements. Relative to the element path */
    allow?: string[];
    /** Kind of import that the policy applies to (e.g., "type", "value") */
    importKind?: DependencyKind;
    /** Custom message for policy violations */
    message?: string;
};
/** @deprecated Use `EntryPointPolicy` instead. */
export type EntryPointRule = EntryPointPolicy;
/**
 * Options for the entry-point rule, including default effect and specific policies.
 */
export type EntryPointRuleOptions = Omit<RuleBaseOptions, "policies" | "rules"> & {
    /** Specific policies for defining entry points between elements */
    policies?: EntryPointPolicy[];
    /** Specific policies for defining entry points between elements. @deprecated Use `policies` instead. */
    rules?: EntryPointPolicy[];
};
/**
 * Options for selecting external libraries, including path patterns and optional specifiers.
 * If specifiers are provided, they will be used to match specific imports from the external library.
 */
export type ExternalLibrarySelectorOptions = {
    /**
     * Micromatch pattern(s) to match only one or more specific subpaths of the external library.
     */
    path?: MicromatchPatternNullable;
    /** Micromatch pattern(s) to match only specific imports/exports */
    specifiers?: string[];
};
/**
 * External library selector with options, represented as a tuple where the first element is the import path of the external library, and the second element is an object containing options for selecting only specific paths or specifiers from that library.
 */
export type ExternalLibrarySelectorWithOptions = [
    string,
    ExternalLibrarySelectorOptions
];
/**
 * External library selector, which can be a simple string (the import path) or an external library selector with options.
 */
export type ExternalLibrarySelector = string | ExternalLibrarySelectorWithOptions;
/**
 * External library selectors, which can be a single external library selector or an array of external library selectors.
 * @deprecated Use ExternalLibrariesSelector instead.
 */
export type ExternalLibrarySelectors = ExternalLibrariesSelector;
/**
 * External libraries selector, which can be a single external library selector or an array of external library selectors.
 */
export type ExternalLibrariesSelector = ExternalLibrarySelector | ExternalLibrarySelector[];
/**
 * Policy that defines allowed or disallowed external library imports for specific element types.
 */
export type ExternalPolicy = {
    /** Selectors of the source elements that the policy applies to (the elements importing) */
    from: BackwardCompatibleEntitySelector;
    /** Selectors of the external libraries that are disallowed to be imported */
    disallow?: ExternalLibrariesSelector;
    /** Selectors of the external libraries that are allowed to be imported */
    allow?: ExternalLibrariesSelector;
    /** Kind of import that the policy applies to (e.g., "type", "value") */
    importKind?: DependencyKind;
    /** Custom message for policy violations */
    message?: string;
};
/** @deprecated Use `ExternalPolicy` instead. */
export type ExternalRule = ExternalPolicy;
/**
 * Options for the external rule, including default effect and specific policies.
 */
export type ExternalRuleOptions = Omit<RuleBaseOptions, "policies" | "rules"> & {
    /** Specific policies for defining allowed or disallowed external library imports */
    policies?: ExternalPolicy[];
    /** Specific policies for defining allowed or disallowed external library imports. @deprecated Use `policies` instead. */
    rules?: ExternalPolicy[];
};
/**
 * Options for the no-private rule, which restricts imports of private elements.
 * Private elements are those that are children of another elements in the folder structure.
 * This rules enables that private elements can't be used by anyone except its parent (or any other descendant of the parent when `allowUncles` option is enabled)
 */
export type NoPrivateOptions = {
    /** Whether to allow imports from "uncle" elements (elements sharing the same ancestor) */
    allowUncles?: boolean;
    /** Custom message for rule violations */
    message?: string;
};
export declare const NO_UNKNOWN_DEPENDENCIES_REQUIRE_ALL: "all";
export declare const NO_UNKNOWN_DEPENDENCIES_REQUIRE_ELEMENT: "element";
export declare const NO_UNKNOWN_DEPENDENCIES_REQUIRE_FILE: "file";
export declare const NO_UNKNOWN_DEPENDENCIES_REQUIRE_ANY: "any";
/**
 * Map containing the available values for the no-unknown-dependencies rule's
 * `require` option.
 */
export declare const NO_UNKNOWN_DEPENDENCIES_REQUIRE_MAP: {
    readonly ALL: "all";
    readonly ELEMENT: "element";
    readonly FILE: "file";
    readonly ANY: "any";
};
/**
 * Which classification axes a dependency target must be "known" on for the
 * no-unknown-dependencies rule to consider it valid.
 * - `"any"` (default): known on at least one axis (element or file) is enough.
 *   Reported only when the target is unknown on both axes.
 * - `"element"`: the element axis must be known, regardless of the file axis.
 *   Reported when the target element is unknown.
 * - `"file"`: the file axis must be known, regardless of the element axis.
 *   Reported when the target file is unknown.
 * - `"all"`: both axes must be known. Reported when either axis is unknown.
 */
export type NoUnknownDependenciesRequire = (typeof NO_UNKNOWN_DEPENDENCIES_REQUIRE_MAP)[keyof typeof NO_UNKNOWN_DEPENDENCIES_REQUIRE_MAP];
/**
 * Options for the no-unknown-dependencies rule, which prevents dependencies to
 * targets that are not recognized by any element or file descriptor.
 *
 * The `require` option controls which classification axes the target must be
 * known on to be valid. With the default (`require: "any"`), known on at least
 * one axis is enough, so the rule reports only when the target is unknown on
 * both axes.
 */
export type NoUnknownDependenciesOptions = {
    /** Which classification axes the target must be known on to be valid. (default: `"any"`) */
    require?: NoUnknownDependenciesRequire;
};
export type RuleOptionsWithPolicies = ExternalRuleOptions | EntryPointRuleOptions | DependenciesRuleOptions;
export type RuleOptions = RuleOptionsWithPolicies | NoPrivateOptions | NoUnknownDependenciesOptions;
export type RuleOptionsPolicies = ExternalPolicy | EntryPointPolicy | DependenciesPolicy;
export declare const FROM: "from";
export type RuleMainKey = typeof FROM | "to" | "target";
export type ValidateRulesOptions = {
    mainKey?: RuleMainKey;
    onlyMainKey?: boolean;
};
