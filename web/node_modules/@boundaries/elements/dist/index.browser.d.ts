/**
 * Type representing a micromatch pattern, which can be a string or an array of strings.
 */
type MicromatchPattern = string | string[];
/**
 * Type representing a micromatch pattern supporting null values
 */
type MicromatchPatternNullable = string | null | (string | null)[];
/**
 * Type representing values that can be matched against micromatch patterns.
 */
type MicromatchMatchableValue = string | string[] | null | undefined | boolean;

/**
 * Configuration options for categorizing entities as external or local.
 */
type FlagAsExternalOptions = {
    /** When true, non-relative entities whose path cannot be resolved are categorized as external (default: true) */
    unresolvableAlias?: boolean;
    /** When true, non-relative paths that include node_modules are categorized as external (default: true) */
    inNodeModules?: boolean;
    /** When true, entities whose resolved path is outside the configured root path are categorized as external (default: false) */
    outsideRootPath?: boolean;
    /** List of patterns (using micromatch syntax) that, when matching the source of the entity, categorize it as external (default: []) */
    customSourcePatterns?: MicromatchPattern;
};
/** Configuration options for the Config class */
type ConfigOptions = {
    /** An array of path patterns to include when resolving entities. Defaults to all files if not specified */
    includePaths?: MicromatchPattern;
    /** An array of path patterns to ignore when resolving entities */
    ignorePaths?: MicromatchPattern;
    /**
     * Whether to enable legacy template support (default: true)
     * When enabled, it supports using "${...}" syntax in templates.
     **/
    legacyTemplates?: boolean;
    /** Whether to enable caching */
    cache?: boolean;
    /** Configuration for categorizing entities as external or local */
    flagAsExternal?: FlagAsExternalOptions;
    /** Root path of the project, used for determining if entities are outside the project */
    rootPath?: string;
};
type FlagAsExternalOptionsNormalized = {
    /** When true, non-relative dependencies whose path cannot be resolved are categorized as external */
    unresolvableAlias: boolean;
    /** When true, non-relative paths that include node_modules are categorized as external */
    inNodeModules: boolean;
    /** When true, entities whose resolved path is outside the configured root path are categorized as external */
    outsideRootPath: boolean;
    /** List of patterns (using micromatch syntax) that, when matching the source of the entity, categorize it as external */
    customSourcePatterns: string[];
};
type ConfigOptionsNormalized = Omit<ConfigOptions, "legacyTemplates" | "cache" | "flagAsExternal"> & {
    /** Whether to enable legacy template support */
    legacyTemplates: boolean;
    /** Cache configuration options */
    cache: boolean;
    /** Configuration for categorizing entities as external or local */
    flagAsExternal: FlagAsExternalOptionsNormalized;
    /** Root path of the project, already normalized, and finishing with a slash, used for determining if entities are outside the project */
    rootPath: string | undefined;
};
/** Options for descriptors */
type DescriptorOptionsNormalized = Pick<ConfigOptionsNormalized, "includePaths" | "ignorePaths" | "cache" | "flagAsExternal" | "rootPath">;
/** Options for element matchers */
type MatchersOptionsNormalized = Pick<ConfigOptionsNormalized, "legacyTemplates">;

/**
 * Captured values from an element or file path
 */
type CapturedValues = Record<string, string>;
/**
 * Base element properties related to captured values
 */
type BaseDescription = {
    /** Absolute path of the item. It might be null when a dependency path can't be resolved */
    path: string | null;
    /** Captured values from the item, or null if the item descriptor has no capture or the item is ignored or unknown */
    captured: CapturedValues | null;
    /** Indicates if the item is ignored by settings. If true, it will be excluded from processing any other properties. */
    isIgnored: boolean;
    /** Indicates if the item is unknown, which means that it cannot be resolved to any descriptor */
    isUnknown: boolean;
};
/**
 * Description of an ignored item
 */
type BaseIgnoredDescription = BaseDescription & {
    /** Ignored items have not captured values */
    captured: null;
    /** Indicates if the item is ignored */
    isIgnored: true;
    /** Indicates that the item is unknown */
    isUnknown: true;
};
/**
 * Description of a known item, which has a path and captured values
 */
type BaseKnownDescription = BaseDescription & {
    /** Known items always have a path */
    path: string;
    /** Indicates if the item is ignored */
    isIgnored: false;
    /** Indicates that the item is known */
    isUnknown: false;
};
/**
 * Description of an unknown item, which has no captured values and is not ignored
 */
type BaseUnknownDescription = BaseDescription & {
    /** Unknown items have not captured values */
    captured: null;
    /** Indicates that the item is not ignored */
    isIgnored: false;
    /** Indicates that the item is unknown */
    isUnknown: true;
};

/**
 * Base element properties related to captured values
 */
type ElementDescription = BaseDescription & {
    /** All types of the element. Contains multiple types unless elementsSingleMatch is enabled. */
    types: string[] | null;
    /**
     * Category of the element
     * @deprecated This property is deprecated and will be removed in future versions.
     */
    category: string | null;
    /**
     * Full filePath of the file related to the element, or null in case it has not related file
     * @deprecated This property has been temporarily added for backward compatibility with legacy mode "file", where the element description included file properties. It will be removed in future versions.
     */
    filePath: string | null;
    /**
     * Internal path of the file relative to the element it belongs to, or null in case it has not related file.
     */
    fileInternalPath: string | null;
    /** Parent elements */
    parents: ElementParent[];
};
/**
 * Parent elements
 */
type ElementParent = {
    /** All types of the parent element. Contains multiple types unless elementsSingleMatch is enabled. */
    types: string[] | null;
    /**
     * Category of the parent element
     * @deprecated This property is deprecated and will be removed in future versions.
     */
    category: string | null;
    /** Path of the parent element */
    path: string | null;
    /** Captured values from the parent element's descriptor pattern */
    captured: CapturedValues | null;
};
/**
 * Description of an ignored element
 */
type IgnoredElementDescription = ElementDescription & BaseIgnoredDescription & {
    /** Path of an ignored element is null, because it can't be resolved to any descriptor */
    path: null;
    /** Types of the element */
    types: null;
    /** Category of the element */
    category: null;
    /** File internal path of an ignored element is null, because it can't be resolved to any descriptor */
    fileInternalPath: null;
    /** Parent elements. For ignored elements, parents are an empty array because the element can't be resolved to any descriptor, so we have no information about its parents. */
    parents: [];
};
/**
 * Description of an unknown local element
 */
type UnknownElementDescription = ElementDescription & BaseUnknownDescription & {
    /** Path of an unknown element is null, because it can't be resolved to any descriptor */
    path: null;
    /** File internal path of an unknown element is null, because it can't be resolved to any descriptor */
    fileInternalPath: null;
    /** Types of the element. For unknown elements, the types is null because it can't be determined without a matching descriptor. */
    types: null;
    /** Category of the element. For unknown elements, the category is null because it can't be determined without a matching descriptor. */
    category: null;
    /** Parent elements. For unknown elements, parents are an empty array because the element can't be resolved to any descriptor, so we have no information about its parents. */
    parents: [];
};
type KnownElementDescription = ElementDescription & BaseKnownDescription & {
    /** Known elements always have path and categories */
    path: string;
    /** File internal path of a known element */
    fileInternalPath: string;
    /**
     * All types of the element
     **/
    types: string[] | null;
    /** filePath is always string for known elements*/
    filePath: string;
    /** Parent elements. For known elements, parents is an array of parent descriptions, which may be empty if the element has no parents. */
    parents: ElementParent[];
};

/**
 * Determines if the given value is a base element description.
 * @param value The value to check.
 * @returns True if the value is a base element description, false otherwise.
 */
declare function isElementDescription(value: unknown): value is ElementDescription;
/**
 * Determines if the given element is unknown, because its type could not be determined.
 * @param value The value to check.
 * @returns True if the element is an unknown element, false otherwise.
 */
declare function isUnknownElementDescription(value: unknown): value is UnknownElementDescription;
/**
 * Determines if the given element is known, because its type was determined.
 * @param value The value to check.
 * @returns True if the element is a known element, false otherwise.
 */
declare function isKnownElementDescription(value: unknown): value is KnownElementDescription;
/**
 * Determines if the given element is ignored.
 * @param value The value to check.
 * @returns True if the element is an ignored element, false otherwise.
 */
declare function isIgnoredElementDescription(value: unknown): value is IgnoredElementDescription;

/**
 * Index + matcher pair for the `atIndex` operator.
 * `matches` is distinct from `equalsTo` to keep the whole-array equality operator unambiguous.
 */
type ArrayQueryAtIndex<TMatcher> = {
    /** Index into the array. Negative values count from the end (-1 = last element). */
    index: number;
    /**
     * Matcher applied to the element found at `index`.
     * A single value or an array of values — array means OR (matches if any item matches).
     */
    matches: TMatcher | TMatcher[];
};
/**
 * Query object for matching against an array-valued property.
 * `TMatcher` matches a single array element:
 *  - micromatch pattern (string) for string arrays (types, categories)
 *  - ParentElementSingleSelector for the parent ancestor chain (parents)
 *
 * All present operators are combined with AND. An operator that is `undefined`
 * imposes no constraint.
 */
type ArrayQuery<TMatcher> = {
    /** Matches if at least one array element matches at least one of these matchers. */
    anyOf?: TMatcher[];
    /** Matches if, for every matcher, at least one array element matches it. */
    allOf?: TMatcher[];
    /** Matches if no array element matches any of these matchers. */
    noneOf?: TMatcher[];
    /** Ordered exact match: array length equals N and array[i] matches matcher[i]. */
    equalsTo?: TMatcher[];
    /** Matches the single element at the given index. Negative index counts from the end. */
    atIndex?: ArrayQueryAtIndex<TMatcher>;
    /** Matches if the array length is exactly this value. */
    hasLength?: number;
};
/**
 * Template-array operand item used inside `anyOf` / `allOf` / `noneOf` / `equalsTo`.
 * Its `expand` template is resolved against the template data to a raw string array
 * (or single string), whose values are spread in place as additional matchers.
 */
type ArrayQueryExpandItem = {
    /** A single Handlebars expression (e.g. "{{ from.element.types }}") resolving to a string array. */
    expand: string;
};
/** Matcher item for a string array query: a micromatch pattern or an expand item. */
type StringArrayQueryMatcher = string | ArrayQueryExpandItem;
/** Array query over a string array (file `categories`, element `types`). */
type StringArrayQuery = {
    /** anyOf/allOf/noneOf/equalsTo items may be micromatch patterns or `{ expand }` items. */
    anyOf?: StringArrayQueryMatcher[];
    allOf?: StringArrayQueryMatcher[];
    noneOf?: StringArrayQueryMatcher[];
    equalsTo?: StringArrayQueryMatcher[];
    atIndex?: ArrayQueryAtIndex<string>;
    hasLength?: number;
};

/**
 * Data to pass to selector templates when they are rendered before matching.
 */
type TemplateData = Record<string, unknown>;
/**
 * Options for elements and dependencies matchers.
 */
type MatcherOptions = {
    /** Extra data to pass to captured values templates. By default, data from the element and dependency being matched is passed as to/from. */
    extraTemplateData?: TemplateData;
};
/**
 * Options for entity matcher
 */
type EntityMatcherOptions = MatcherOptions & {
    /** Optional source of the entity being matched in case it is a dependency */
    source?: string;
};

/** All operator keys that identify an ArrayQuery object. */
declare const ARRAY_QUERY_KEYS: readonly ["anyOf", "allOf", "noneOf", "equalsTo", "atIndex", "hasLength"];
/**
 * Determines if a value is an ArrayQuery object (vs. a plain micromatch pattern / array).
 * A string or an array is NOT an ArrayQuery; only a plain object carrying at least one
 * operator key is.
 */
declare function isArrayQuery(value: unknown): value is ArrayQuery<unknown>;
/**
 * Narrows a value to StringArrayQuery.
 * Use this instead of isArrayQuery when the value originates from a
 * MicromatchPatternNullable | StringArrayQuery union, so the call site does
 * not need an unsafe cast.
 */
declare function isStringArrayQuery(value: unknown): value is StringArrayQuery;
/** A `{ expand: string }` item inside a string array query operator. */
declare function isExpandItem(value: unknown): value is ArrayQueryExpandItem;
/** Resolves an expand item to its list of string matchers (spread). */
declare function resolveExpandItem(item: ArrayQueryExpandItem, templateData: TemplateData): string[];
/**
 * Returns a plain `ArrayQuery<string>` where any `{ expand }` items in
 * anyOf/allOf/noneOf/equalsTo are resolved to their string values. Other operators pass through.
 */
declare function expandStringArrayQuery(query: StringArrayQuery, templateData: TemplateData): ArrayQuery<string>;

/**
 * Selector for module information.
 */
type ModuleSingleSelector = {
    /** Base source of the module for external/core modules */
    source?: MicromatchPatternNullable;
    /** Origin of the module */
    origin?: MicromatchPatternNullable;
    /** Internal path of the file relative to the base for external/core modules */
    internalPath?: MicromatchPatternNullable;
};
/** Module selector, which can be a single selector or an array of selectors. */
type ModuleSelector = ModuleSingleSelector | ModuleSingleSelector[];
/** Normalized module selector, which can be a single normalized selector or an array of normalized selectors. */
type ModuleSelectorNormalized = ModuleSingleSelector[];

/**
 * Determines if the given selector is a single module selector
 * @param value The value to check.
 * @returns True if the selector is a single module selector, false otherwise.
 */
declare function isModuleSingleSelector(value: unknown): value is ModuleSingleSelector;
/**
 * Determines if the given value is a module selector.
 * @param value The value to check.
 * @returns True if the value is a module selector, false otherwise.
 */
declare function isModuleSelector(value: unknown): value is ModuleSelector;
/**
 * Normalizes a single module selector, ensuring it has the correct structure and default values.
 * @param selector  The selector to normalize.
 * @returns The normalized selector.
 * @throws Error if the selector is not a valid module single selector.
 */
declare function normalizeModuleSingleSelector(selector: ModuleSingleSelector): ModuleSingleSelector;
/**
 * Normalizes a module selector, ensuring it has the correct structure and default values. If the selector is an array, each item will be normalized.
 * @param selector The selector to normalize.
 * @returns The normalized selector.
 * @throws Error if the selector is not a valid origin selector.
 */
declare function normalizeModuleSelector(selector: ModuleSelector): ModuleSelectorNormalized;

/**
 * Matcher class to determine if modules match a given selector.
 */
declare class ModulesMatcher extends BaseElementsMatcher {
    /**
     * Creates a new ModulesMatcher.
     * @param config Configuration options for the matcher.
     * @param micromatch Micromatch instance for matching.
     */
    constructor(config: MatchersOptionsNormalized, micromatch: Micromatch);
    /**
     * Whether the given origin matches the selector.
     * @param origin The origin to check.
     * @param selector The selector to check against.
     * @param templateData The data to use for replace in selector value.
     * @returns Whether the origin matches the selector.
     */
    private _isOriginMatch;
    /**
     * Whether the given module source matches the selector module.
     * @param origin The origin to check.
     * @param selector The selector to check against.
     * @param templateData The data to use for replace in selector value.
     * @returns Whether the module source matches the selector module.
     */
    private _isSourceMatch;
    /**
     * Whether the given module internal path matches the selector module.
     * @param origin The origin to check.
     * @param selector The selector to check against.
     * @param templateData The data to use for replace in selector value.
     * @returns Whether the module internal path matches the selector module.
     */
    private _isInternalPathMatch;
    /**
     * Returns the selector matching result for the given module description, or null if none matches.
     * @param moduleDescription The module description to check.
     * @param selectorsData The selectors to check against.
     * @param extraTemplateData Extra template data to use for matching.
     * @returns The selector matching result for the given module description, or null if none matches.
     */
    private _getSelectorMatching;
    /**
     * Returns the selector matching result for the given module, or null if none matches.
     * @param moduleDescription The module to check.
     * @param selector The selector to check against.
     * @param options Extra options for matching, such as templates data, etc.
     * @returns The selector matching result for the given module, or null if none matches.
     */
    getSelectorMatching(moduleDescription: ModuleDescription, selector: ModuleSelector, { extraTemplateData }?: MatcherOptions): ModuleSingleSelector | null;
    /**
     * Returns whether the given module matches the selector.
     * @param moduleDescription The module to check.
     * @param selector The selector to check against.
     * @param options Extra options for matching, such as templates data, etc.
     * @returns Whether the module matches the selector.
     */
    isModuleMatch(moduleDescription: ModuleDescription, selector: ModuleSelector, options?: MatcherOptions): boolean;
}

/**
 * Serialized cache of micromatch matcher.
 */
type MicromatchSerializedCache = {
    matchingResults: Record<string, boolean>;
    captures: Record<string, string[] | null>;
};

/**
 * Micromatch wrapper class with caching capabilities.
 */
declare class Micromatch {
    /**
     * Cache for micromatch matching results
     */
    private readonly _matchingResultsCache;
    /**
     * Cache for micromatch captures
     */
    private readonly _capturesCache;
    /**
     * Cache for micromatch makeRe results
     */
    private readonly _makeReCache;
    /**
     * Creates an instance of Micromatch class.
     * @param cache Whether to use caching or not.
     */
    constructor(cache: boolean);
    /**
     * Clears all caches.
     */
    clearCache(): void;
    /**
     * Serializes the current cache state.
     * @returns The serialized cache data.
     */
    serializeCache(): MicromatchSerializedCache;
    /**
     * Restores the cache state from serialized data.
     * @param serializedCache The serialized cache data.
     */
    setFromSerialized(serializedCache: MicromatchSerializedCache): void;
    /**
     * Optimized micromatch match with caching.
     * @param value The value to match.
     * @param pattern The pattern to match against.
     * @returns True if the value matches the pattern, false otherwise.
     */
    isMatch(value: string, pattern: string | string[]): boolean;
    /**
     * Optimized micromatch capture with caching.
     * @param pattern The pattern to match against.
     * @param target The target string to test.
     * @returns Captured groups or null if no match.
     */
    capture(pattern: string, target: string): string[] | null;
    /**
     * Optimized micromatch makeRe with caching.
     * @param pattern The pattern to convert to RegExp.
     * @returns The RegExp instance.
     */
    makeRe(pattern: string): RegExp;
}

/**
 * Base matcher class to determine if objects match a given selector.
 */
declare class BaseElementsMatcher {
    /**
     * Option to use legacy templates with ${} syntax.
     */
    protected readonly _legacyTemplates: boolean;
    /**
     * Micromatch instance for matching.
     */
    protected micromatch: Micromatch;
    /**
     * Creates a new BaseElementsMatcher.
     * @param config Configuration options for the matcher.
     * @param globalCache Global cache instance.
     */
    constructor(config: MatchersOptionsNormalized, micromatch: Micromatch);
    /**
     * Converts a template with ${} to Handlebars {{}} templates for backwards compatibility.
     * @param template The template to convert.
     * @returns The converted template.
     */
    private _getBackwardsCompatibleTemplate;
    /**
     * Determines if a template contains Handlebars syntax.
     * @param template The template to check.
     * @returns True if the template contains Handlebars syntax, false otherwise.
     */
    private _isHandlebarsTemplate;
    /**
     * Returns a rendered template using the provided template data.
     * Optimized version with template caching for better performance.
     * @param template The template to render.
     * @param templateData The data to use for replace in the template.
     * @returns The rendered template.
     */
    private _getRenderedTemplate;
    /**
     * Returns rendered templates using the provided template data.
     * @param template The templates to render.
     * @param extraTemplateData The data to use for replace in the templates.
     * @returns The rendered templates.
     */
    protected getRenderedTemplates(template: MicromatchPatternNullable, templateData: TemplateData): MicromatchPatternNullable;
    /**
     * Cleans a micromatch pattern by removing falsy values from arrays.
     * @param pattern The micromatch pattern(s) to clean.
     * @returns The cleaned pattern. If an array is provided, falsy entries are removed and the resulting array may be empty. If null is provided, null is returned unchanged.
     */
    protected cleanMicromatchPattern(pattern: MicromatchPatternNullable): string | string[] | null;
    /**
     * Returns whether the given value matches the micromatch pattern, converting non-string values to strings.
     * Optimized version with caching for better performance.
     * @param value The value to check.
     * @param pattern The micromatch pattern to match against.
     * @returns Whether the value matches the pattern.
     */
    protected isMicromatchMatch(value: string | null | undefined | boolean, pattern: MicromatchPatternNullable): boolean;
    /**
     * Returns whether the given value matches the micromatch pattern after rendering it as a template.
     * @param pattern The micromatch pattern to render and match against.
     * @param templateData The data to use for rendering the pattern as a template.
     * @param value The value to check.
     * @returns Whether the value matches the rendered pattern.
     */
    protected isTemplateMicromatchMatch(pattern: MicromatchPatternNullable, templateData: TemplateData, value: MicromatchMatchableValue): boolean;
    /**
     * Whether the given element key matches the selector key as booleans.
     * @param param0 The parameters object.
     * @returns Whether the object key matches the selector key.
     */
    protected isObjectKeyBooleanMatch<T extends BaseDescription | ModuleDescription, S extends ElementSingleSelector | ModuleSelector>({ 
    /** The object to check. */
    object, 
    /** The selector to check against. */
    selector, 
    /** The key of the object to check. */
    objectKey, 
    /** The key of the selector to check against. */
    selectorKey, }: {
        /** The object to check. */
        object: T;
        /** The selector to check against. */
        selector: S;
        /** The key of the object to check. */
        objectKey: keyof T;
        /** The key of the selector to check against. */
        selectorKey: keyof S;
    }): boolean;
    /**
     * Generic array-query matcher. All present operators are AND-combined.
     * @param array The target array from the description (may be null).
     * @param query The array query object.
     * @param matchElement Predicate matching one array element against one matcher.
     * @returns Whether the array satisfies the query.
     */
    protected isArrayQueryMatch<TElement, TMatcher>(array: readonly TElement[] | null, query: ArrayQuery<TMatcher>, matchElement: (element: TElement, matcher: TMatcher) => boolean): boolean;
    /**
     * Whether the array-query `equalsTo` operator, if present, fails to match the array.
     * @param array The target array from the description.
     * @param query The array query object.
     * @param matchElement Predicate matching one array element against one matcher.
     * @returns Whether the `equalsTo` operator is present and not satisfied by the array.
     */
    private _arrayQueryEqualsToFails;
    /**
     * Whether the array-query `atIndex` operator, if present, fails to match the array.
     * @param array The target array from the description.
     * @param query The array query object.
     * @param matchElement Predicate matching one array element against one matcher.
     * @returns Whether the `atIndex` operator is present and not satisfied by the array.
     */
    private _arrayQueryAtIndexFails;
    /**
     * String array query matcher with `expand` item support.
     * Expands `{ expand }` operand items against the template data, then evaluates
     * with the standard template-micromatch element matcher.
     */
    protected isStringArrayQueryMatch(array: readonly string[] | null, query: StringArrayQuery, templateData: TemplateData): boolean;
    /**
     * Whether the given object key matches the selector key using micromatch.
     * @param param0 The parameters object.
     * @returns Whether the object key matches the selector key.
     */
    protected isObjectKeyMicromatchMatch<T extends BaseDescription | ModuleDescription, S extends ElementSingleSelector | ModuleSelector, K extends keyof T>({ object, selector, objectKey, selectorKey, selectorValue, templateData, }: {
        /** The object to check. */
        object: T & Record<K, MicromatchMatchableValue>;
        /** The selector to check against. */
        selector: S;
        /** The key of the object to check. */
        objectKey: K;
        /** The key of the selector to check against. */
        selectorKey: keyof S;
        /** The value of the selector key to check against. */
        selectorValue?: MicromatchPatternNullable;
        /** Data to pass when the selector value is rendered as a template */
        templateData: TemplateData;
    }): boolean;
}

/**
 * Selector for matching captured values in selectors.
 * It is a record where the keys are the names of the captured values and the values are the patterns to match on those captured values.
 * When provided as an array, each element in the array represents an alternative (OR logic) - the selector matches if any of the array elements matches.
 */
type CapturedValuesSingleSelector = Record<string, MicromatchPatternNullable>;
/**
 * Selector for matching captured values in selectors.
 * It is a record where the keys are the names of the captured values and the values are the patterns to match on those captured values.
 * When provided as an array, each element in the array represents an alternative (OR logic) - the selector matches if any of the array elements matches.
 */
type CapturedValuesSelector = CapturedValuesSingleSelector | CapturedValuesSingleSelector[];
/**
 * Common properties for file and element selectors **/
type BaseSingleSelector = {
    /** Micromatch pattern(s) to match the path of the file */
    path?: MicromatchPatternNullable;
    /** Captured values selector for dynamic matching */
    captured?: CapturedValuesSelector;
    /** Whether the element is ignored */
    isIgnored?: boolean;
    /** Whether the element is unknown */
    isUnknown?: boolean;
};

/**
 * Determines if the given value is a captured values object selector (single object with pattern properties).
 * @param value The value to check.
 * @returns True if the value is a captured values object selector, false otherwise.
 */
declare function isCapturedValuesSingleSelector(value: unknown): value is CapturedValuesSingleSelector;
/**
 * Determines if the given value is a captured values selector.
 * @param value The value to check.
 * @returns True if the value is a captured values selector, false otherwise.
 */
declare function isCapturedValuesSelector(value: unknown): value is CapturedValuesSelector;
/**
 * Determines if the given selector extends a base single selector.
 * @param value The value to check.
 * @returns True if the selector extends a base single selector, false otherwise.
 */
declare function extendsSingleSelector<T extends BaseSingleSelector>(value: unknown): value is T;

/**
 * Selector for matching a parent element
 */
type ParentElementSingleSelector = Pick<BaseSingleSelector, "path" | "captured"> & {
    /** Type of the first parent element */
    type?: MicromatchPatternNullable;
    /** Types of the parent element */
    types?: MicromatchPatternNullable | StringArrayQuery;
    category?: MicromatchPatternNullable;
};
/** Array query over the element ancestor chain. parents[0] is the closest parent. */
type ParentElementArrayQuery = ArrayQuery<ParentElementSingleSelector>;
/**
 * Legacy selectors are used for backward compatibility with previous versions of the plugin. They include additional properties that were used in the old selector format
 */
type LegacyParentElementSingleSelector = ParentElementSingleSelector & {
    /** The path of the parent element to select. */
    elementPath?: MicromatchPatternNullable;
};
type LegacyParentElementSelector = LegacyParentElementSingleSelector | LegacyParentElementSingleSelector[];
type ParentElementSelector = ParentElementSingleSelector | ParentElementSingleSelector[];
type BackwardCompatibleParentElementSingleSelector = ParentElementSingleSelector | LegacyParentElementSingleSelector;
type BackwardCompatibleParentElementSelector = BackwardCompatibleParentElementSingleSelector | BackwardCompatibleParentElementSingleSelector[];
/**
 * Normalized parent element selector, being always an array of single selectors.
 */
type ParentElementSelectorNormalized = ParentElementSingleSelector[];
/**
 * Simple element selector by type, represented as a string matching the element type.
 * @deprecated Use BaseElementSelectorData or DependencyElementSelectorData instead.
 */
type LegacySimpleElementSingleSelectorByType = string;
/**
 * File Element selector with options, including captured values for dynamic matching.
 * It is represented as a tuple where the first element is the element type (string)
 * and the second element is an object containing a selector for captured values.
 * @deprecated Use FileElementSelectorData defining an object with type and/or category and the rest of properties directly instead.
 */
type LegacySimpleElementSingleSelectorByTypeWithOptions = [
    LegacySimpleElementSingleSelectorByType,
    CapturedValuesSelector
];
type LegacySimpleElementSingleSelector = LegacySimpleElementSingleSelectorByType | LegacySimpleElementSingleSelectorByTypeWithOptions;
/**
 * Legacy element simple selector type, which can be a simple string, object with type and/or category, or an element selector with options.
 */
type LegacyElementSimpleSelector = LegacySimpleElementSingleSelector | LegacySimpleElementSingleSelector[];
/**
 * Selector for base elements, including captured values for dynamic matching.
 */
type ElementSingleSelector = BaseSingleSelector & {
    /** Type of the element. Matches the first type only */
    type?: MicromatchPatternNullable;
    /** Types of the element. A micromatch pattern (OR) or an array query object. */
    types?: MicromatchPatternNullable | StringArrayQuery;
    category?: MicromatchPatternNullable;
    /** Internal path of the file relative to the element it belongs to, or null if it has no internal path */
    fileInternalPath?: MicromatchPatternNullable;
    filePath?: MicromatchPatternNullable;
    /** Selector for matching the first parent element */
    parent?: ParentElementSelector | null;
    /**
     * Query over the full parent ancestor chain (`element.parents`).
     * `parents[0]` is the closest parent; the last element is the outermost ancestor.
     * Use the array query operators (anyOf / allOf / noneOf / equalsTo / atIndex / hasLength).
     * Unlike `parent`, this is a pure boolean filter and does not contribute captured values.
     */
    parents?: ParentElementArrayQuery;
};
/**
 * Legacy selectors are used for backward compatibility with previous versions of the plugin. They include additional properties that were used in the old selector format
 */
type LegacyElementSingleObjectSelector = ElementSingleSelector & {
    /** The origin of the element to select. */
    origin?: MicromatchPatternNullable;
    /** The path of the element to select. */
    elementPath?: MicromatchPatternNullable;
    /** The path of the file containing the element to select. */
    internalPath?: MicromatchPatternNullable;
};
/**
 * Legacy selectors are used for backward compatibility with previous versions of the plugin. They include additional properties that were used in the old selector format
 */
type LegacyElementObjectSelector = LegacyElementSingleObjectSelector | LegacyElementSingleObjectSelector[];
/** Normalized single element selector, where the parent selector is always an array of single selectors. */
type ElementSingleSelectorNormalized = ElementSingleSelector & {
    /** Normalized selector for matching the first parent element, being always an array of single selectors. */
    parent?: ParentElementSelectorNormalized | null;
};
/** A simple element selector in any legacy format */
type LegacyElementSingleSelector = LegacyElementSingleObjectSelector | LegacySimpleElementSingleSelector;
/**
 * A legacy element selector, which can be a single legacy element selector or an array of legacy element selectors, in any legacy format
 */
type LegacyElementSelector = LegacyElementSingleSelector | LegacyElementSingleSelector[];
/**
 * Element selector, which can be a single element selector or an array of element selectors.
 */
type ElementSelector = ElementSingleSelector | ElementSingleSelector[];
/**
 * Element selector backward compatibility type, which can be a simple string, object with type and/or category, or an element selector with options.
 * @deprecated Use ElementSingleSelector instead.
 */
type BackwardCompatibleElementSingleSelector = LegacyElementSingleSelector | ElementSingleSelector;
/**
 * Backward compatible element selector type that can be either a legacy element single selector or a new element single selector. This type is used to allow functions that accept element single selectors to also accept legacy element single selectors for backward compatibility.
 */
type BackwardCompatibleElementSelector = BackwardCompatibleElementSingleSelector | BackwardCompatibleElementSingleSelector[];
/** Normalized element selector, being always an array of single selectors, already transformed to the new format if it was using any of the backward compatible formats */
type ElementSelectorNormalized = ElementSingleSelectorNormalized[];

type ElementSingleSelectorMatchResult = Omit<ElementSingleSelectorNormalized, "parent"> & {
    parent?: ParentElementSingleSelector | null;
};

/**
 * Matcher class to determine if elements match a given selector.
 */
declare class ElementsMatcher extends BaseElementsMatcher {
    /**
     * Creates a new ElementsSelectorMatcher.
     * @param config Configuration options for the matcher.
     * @param micromatch Micromatch instance for matching.
     * @param globalCache Global cache instance.
     */
    constructor(config: MatchersOptionsNormalized, micromatch: Micromatch);
    /**
     * Whether the given element first type matches the selector type (singular).
     * @param element The element to check.
     * @param selector The selector to check against.
     * @param templateData The data to use for replace in selector value
     * @returns Whether the element first type matches the selector type.
     */
    private _isSingleTypeMatch;
    /**
     * Whether the given element type matches the selector type.
     * @param element The element to check.
     * @param selector The selector to check against.
     * @param templateData The data to use for replace in selector value
     * @returns Whether the element type matches the selector type.
     */
    private _isTypeMatch;
    /**
     * Whether the given element path matches the selector path.
     * @param element The element to check.
     * @param selector The selector to check against.
     * @param templateData The data to use for replace in selector value
     * @returns Whether the element path matches the selector path.
     */
    private _isPathMatch;
    /**
     * Whether the given element file internal path matches the selector file internal path.
     * @param element The element to check.
     * @param selector The selector to check against.
     * @param templateData The data to use for replace in selector value
     * @returns Whether the element file internal path matches the selector file internal path.
     */
    private _isFileInternalPathMatch;
    /**
     * Checks if a single captured values object matches the element.
     * @param capturedValues The captured values to check.
     * @param capturedSelector The captured values selector object to check against
     * @param templateData The data to use for replace in selector values
     * @returns True if all captured values in the selector match those in the element, false otherwise.
     */
    private _checkCapturedValuesObject;
    /**
     * Determines if the captured values of the element match those in the selector.
     * When the selector is an array, the element matches if it matches any of the array elements (OR logic).
     * @param element The element to check.
     * @param selector The selector to check against
     * @param templateData The data to use for replace in selector values
     * @returns True if the captured values match, false otherwise.
     */
    private _isCapturedValuesMatch;
    /**
     * Determines if the parent captured values match the selector.
     * @param parentSelector The parent selector to match.
     * @param parentCaptured The captured values from first parent.
     * @param templateData The data to use for replace in selector values
     * @returns True if the captured values match, false otherwise.
     */
    private _isParentCapturedValuesMatch;
    /**
     * Whether a specific parent element matches a parent single selector.
     * Does not handle null selectors or the "first parent" lookup.
     * @param parent The parent element to check.
     * @param selector The parent selector to check against.
     * @param templateData The data to use for replace in selector values.
     * @returns Whether the parent matches the selector.
     */
    private _isParentMatch;
    /**
     * Whether the given element first parent matches the selector parent.
     * @param element The element to check.
     * @param selector The selector to check against.
     * @param templateData The data to use for replace in selector values
     * @returns Whether the first parent matches the selector parent.
     */
    private _isSingleParentMatch;
    /**
     * Whether the element's full parent ancestor chain matches the `parents` array query.
     * @param element The element to check.
     * @param selector The normalized element selector.
     * @param templateData The data to use for replace in selector values.
     * @returns Whether the ancestor chain satisfies the query, or true if no `parents` selector is set.
     */
    private _isParentsMatch;
    /**
     * Returns the parent selector that matches the element.
     * When the parent selector is an array, returns the first parent selector that matches (OR logic).
     * @param element The element to check.
     * @param selector The selector to check against.
     * @param templateData The data to use for replace in selector values
     * @returns The matching parent selector, null if the selector parent is null and the element has no parents, or undefined if there is no match.
     */
    private _getParentSelectorMatching;
    /**
     * Determines if the isIgnored property of the element matches that in the selector.
     * @param element The element to check.
     * @param selector The selector to check against.
     * @returns True if the isIgnored properties match, false otherwise.
     */
    private _isIgnoredMatch;
    /**
     * Determines if the isUnknown property of the element matches that in the selector.
     * @param element The element to check.
     * @param selector The selector to check against.
     * @returns True if the isUnknown properties match, false otherwise.
     */
    private _isUnknownMatch;
    /**
     * Determines if the category of the element matches that in the selector.
     * @param element The element to check.
     * @param selector The selector to check against.
     * @param templateData The data to use for replace in selector value
     * @returns True if the categories match, false otherwise.
     */
    private _isCategoryMatch;
    /**
     * Determines if the filePath of the element matches that in the selector.
     * This is a legacy check for backward compatibility with legacy mode "file", where the element selector included filePath. It will be removed in future versions, so it shouldn't be used in new selectors.
     * @param element The element to check.
     * @param selector The selector to check against.
     * @param templateData The data to use for replace in selector value
     * @returns True if the filePaths match, false otherwise.
     */
    private _isFilePathMatch;
    /**
     * Returns the selector matching result for the given local or external element.
     * @param element The local or external element to check.
     * @param selector The selector to check against.
     * @param extraTemplateData Extra template data to use for matching.
     * @returns The selector matching result for the given element, or null if none matches.
     */
    private _getSelectorMatching;
    /**
     * Returns the selector matching result for the given element, or null if none matches.
     * It omits checks in keys applying only to dependency between elements, such as relationship.
     * @param element The element to check.
     * @param selector The selector to check against.
     * @param options Extra options for matching, such as templates data, etc.
     * @returns The selector matching result for the given element, or null if none matches.
     */
    getSelectorMatching(element: ElementDescription, selector: BackwardCompatibleElementSelector, { extraTemplateData }?: MatcherOptions): ElementSingleSelectorMatchResult | null;
    /**
     * Returns whether the given element matches the selector.
     * It omits checks in keys applying only to dependency between elements, such as relationship.
     * @param element The element to check.
     * @param selector The selector to check against.
     * @param options Extra options for matching, such as templates data, etc.
     * @returns Whether the element matches the selector properties applying to elements.
     */
    isElementMatch(element: ElementDescription, selector: BackwardCompatibleElementSelector, options?: MatcherOptions): boolean;
}

/**
 * Determines if the given value is a simple element selector.
 * @param value The value to check.
 * @returns True if the value is a simple element selector, false otherwise.
 */
declare function isLegacySimpleElementSingleSelectorByType(value: unknown): value is LegacySimpleElementSingleSelectorByType;
/**
 * Determines if the given selector is a simple element selector by type with options.
 * @param value The value to check.
 * @returns True if the selector is a simple element selector by type with options, false otherwise.
 */
declare function isLegacySimpleElementSingleSelectorByTypeWithOptions(value: unknown): value is LegacySimpleElementSingleSelectorByTypeWithOptions;
/**
 * Determines if the given selector is a legacy element simple selector, which can be a simple string, object with type and/or category, or an element selector with options.
 * @param value The value to check.
 * @returns True if the selector is a legacy element simple selector, false otherwise.
 */
declare function isLegacySimpleElementSingleSelector(value: unknown): value is LegacyElementSimpleSelector;
/**
 * Determines if the given value uses the legacy string or tuple selector syntax
 * (a type string, a `[type, options?]` tuple, or an array containing either),
 * as opposed to the modern object-based selector syntax.
 * @param value The value to check.
 * @returns True if the value uses legacy string or tuple selector syntax, false otherwise.
 */
declare function isLegacySimpleElementSelector(value: unknown): boolean;
/**
 * Determines if the given selector is a legacy parent element single selector.
 * @param selector The selector to check.
 * @returns True if the selector is a legacy parent element single selector, false otherwise.
 */
declare function isLegacyParentElementSingleSelector(selector: unknown): selector is LegacyParentElementSingleSelector;
/**
 * Determines if the given selector is a legacy element single selector.
 * @param selector The selector to check.
 * @returns True if the selector is a legacy element single selector, false otherwise.
 */
declare function isLegacyElementSingleObjectSelector(selector: unknown): selector is LegacyElementSingleObjectSelector;
/**
 * Determines if the given selector is a legacy element selector.
 * @param selector The selector to check.
 * @returns True if the selector is a legacy element selector, false otherwise.
 */
declare function isLegacyElementSingleSelector(selector: unknown): selector is LegacyElementSelector;
declare function isLegacyElementSelector(selector: unknown): selector is LegacyElementSelector;
/**
 * Determines if the given selector is a single element selector
 * @param value The value to check.
 * @returns True if the selector is a single element selector, false otherwise.
 */
declare function isElementSingleSelector(value: unknown): value is ElementSingleSelector;
/**
 * Determines if the given value is an element selector.
 * @param value The value to check.
 * @returns True if the value is an element selector, false otherwise.
 */
declare function isElementSelector(value: unknown): value is ElementSelector;
declare function isBackwardCompatibleElementSingleSelector(selector: unknown): selector is BackwardCompatibleElementSingleSelector;
declare function isBackwardCompatibleElementSelector(selector: unknown): selector is BackwardCompatibleElementSelector;
declare function normalizeLegacySimpleElementSingleSelector(selector: LegacySimpleElementSingleSelector): ElementSingleSelectorNormalized;
declare function normalizeLegacyParentElementSelectors(selector: BackwardCompatibleParentElementSingleSelector[]): ParentElementSelectorNormalized | null;
declare function normalizeParentElementSelector(selector: BackwardCompatibleParentElementSelector | null): ParentElementSelectorNormalized | null;
declare function normalizeParentInElementSingleSelector(selector: ElementSingleSelector): ElementSingleSelectorNormalized;
declare function normalizeLegacyElementSingleObjectSelector(selector: LegacyElementSingleObjectSelector): ElementSingleSelectorNormalized;
declare function normalizeLegacyElementSingleSelector(selector: LegacyElementSingleSelector): ElementSingleSelectorNormalized;
/**
 * Normalizes a selector into ElementSelectorData format.
 * @param selector The selector to normalize.
 * @returns The normalized selector data.
 */
declare function normalizeSingleElementSelector(selector: BackwardCompatibleElementSingleSelector): ElementSingleSelectorNormalized;
/**
 * Normalizes an ElementSelector into an array of ElementSingleSelector.
 * @param elementSelector The element selector, in any supported format.
 * @returns The normalized array of selector data.
 */
declare function normalizeElementSelector(elementSelector: BackwardCompatibleElementSelector): ElementSelectorNormalized;

/**
 * Selector for files
 */
type FileSingleSelector = BaseSingleSelector & {
    /** Categories of the file. A micromatch pattern (OR) or an array query object. */
    categories?: MicromatchPatternNullable | StringArrayQuery;
};
/**
 * File selector, which can be a single file selector or an array of file selectors.
 */
type FileSelector = FileSingleSelector | FileSingleSelector[];
/** Normalized file selector, being always an array of single selectors */
type FileSelectorNormalized = FileSingleSelector[];

/**
 * Matcher class to determine if files match a given selector.
 */
declare class FilesMatcher extends BaseElementsMatcher {
    /**
     * Creates a new FilesMatcher.
     * @param config Configuration options for the matcher.
     * @param micromatch Micromatch instance for matching.
     */
    constructor(config: MatchersOptionsNormalized, micromatch: Micromatch);
    /**
     * Whether the given file path matches the selector path.
     * @param file The file to check.
     * @param selector The selector to check against.
     * @param templateData The data to use for replace in selector value.
     * @returns Whether the file path matches the selector path.
     */
    private _isPathMatch;
    /**
     * Whether the given file categories match the selector categories.
     * File descriptions expose categories as an array, so it matches when any category matches the selector pattern.
     * @param file The file to check.
     * @param selector The selector to check against.
     * @param templateData The data to use for replace in selector value.
     * @returns Whether the file categories match the selector categories.
     */
    private _isCategoriesMatch;
    /**
     * Checks if a single captured values object matches the file.
     * @param capturedValues The captured values to check.
     * @param capturedSelector The captured values selector object to check against.
     * @param templateData The data to use for replace in selector values.
     * @returns True if all captured values in the selector match those in the file, false otherwise.
     */
    private _checkCapturedValuesObject;
    /**
     * Determines if the captured values of the file match those in the selector.
     * When the selector is an array, the file matches if it matches any of the array elements.
     * @param file The file to check.
     * @param selector The selector to check against.
     * @param templateData The data to use for replace in selector values.
     * @returns True if the captured values match, false otherwise.
     */
    private _isCapturedValuesMatch;
    /**
     * Determines if the isIgnored property of the file matches that in the selector.
     * @param file The file to check.
     * @param selector The selector to check against.
     * @returns True if the isIgnored properties match, false otherwise.
     */
    private _isIgnoredMatch;
    /**
     * Determines if the isUnknown property of the file matches that in the selector.
     * @param file The file to check.
     * @param selector The selector to check against.
     * @returns True if the isUnknown properties match, false otherwise.
     */
    private _isUnknownMatch;
    /**
     * Returns the selector matching result for the given file.
     * @param file The file to check.
     * @param selectorsData The selectors to check against.
     * @param extraTemplateData Extra template data to use for matching.
     * @returns The selector matching result for the given file, or null if none matches.
     */
    private _getSelectorMatching;
    /**
     * Returns the selector matching result for the given file, or null if none matches.
     * @param file The file to check.
     * @param selector The selector to check against.
     * @param options Extra options for matching, such as templates data, etc.
     * @returns The selector matching result for the given file, or null if none matches.
     */
    getSelectorMatching(file: FileDescription, selector: FileSelector, { extraTemplateData }?: MatcherOptions): FileSingleSelector | null;
    /**
     * Returns whether the given file matches the selector.
     * @param file The file to check.
     * @param selector The selector to check against.
     * @param options Extra options for matching, such as templates data, etc.
     * @returns Whether the file matches the selector.
     */
    isFileMatch(file: FileDescription, selector: FileSelector, options?: MatcherOptions): boolean;
}

/**
 * Determines if the given selector is a single file selector
 * @param value The value to check.
 * @returns True if the selector is a single file selector, false otherwise.
 */
declare function isFileSingleSelector(value: unknown): value is FileSingleSelector;
/**
 * Determines if the given value is a file selector.
 * @param value The value to check.
 * @returns True if the value is a file selector, false otherwise.
 */
declare function isFileSelector(value: unknown): value is FileSelector;
/**
 * Normalizes a single file selector, ensuring it has the correct structure and default values.
 * @param selector The selector to normalize.
 * @returns The normalized selector.
 */
declare function normalizeSingleFileSelector(selector: FileSingleSelector): FileSingleSelector;
/**
 * Normalizes a FileSelector into an array of FileSingleSelector.
 * @param fileSelector The file selector, in any supported format.
 * @returns The normalized array of single file selectors.
 */
declare function normalizeFileSelector(fileSelector: FileSelector): FileSelectorNormalized;

/**
 * The result of matching a single entity selector, containing the matching results for each selector property (element, file and origin).
 */
type EntitySingleSelectorMatchResult = {
    /** The single selector matching result for the element. */
    element?: ElementSingleSelector;
    /** The single selector matching result for the file. */
    file?: FileSingleSelector;
    /** The single selector matching result for the module. */
    module?: ModuleSingleSelector;
};
/**
 * Result of matching an entity selector against an entity.
 */
type EntityMatchResult = {
    selector: EntitySingleSelectorMatchResult | null;
    /** Whether the entity matches all the selector properties provided */
    isMatch: boolean;
};

/**
 * Legacy selector for an entity, which can contain element selectors in any legacy format.
 */
type LegacyEntitySingleSelector = {
    /** The element associated with this entity, or undefined to ignore the element in the matching process */
    element?: LegacyElementSelector | ElementSelector;
    /** The file associated with this entity, or undefined to ignore the file in the matching process */
    file?: FileSelector;
    /** The module associated with this entity, or undefined to ignore the module in the matching process */
    module?: ModuleSelector;
} | LegacyElementSelector | ElementSelector;
/** Legacy entity Selector, which can be a single legacy entity selector or an array of legacy entity selectors */
type LegacyEntitySelector = LegacyEntitySingleSelector | LegacyEntitySingleSelector[];
/** Single selector for an entity, which is the main unit under analysis */
type EntitySingleSelector = {
    /** The element associated with this entity, or undefined to ignore the element in the matching process */
    element?: ElementSelector;
    /** The file associated with this entity, or undefined to ignore the file in the matching process */
    file?: FileSelector;
    /** The module associated with this entity, or undefined to ignore the module in the matching process */
    module?: ModuleSelector;
};
/** Selector for an entity, which is the main unit under analysis */
type EntitySelector = EntitySingleSelector | EntitySingleSelector[];
/** Backward compatible single selector for an entity, which can be either a legacy entity single selector or a new entity single selector. This type is used to allow functions that accept entity single selectors to also accept legacy entity single selectors for backward compatibility. */
type BackwardCompatibleEntitySingleSelector = LegacyEntitySingleSelector | EntitySingleSelector;
/** Backward compatible selector for an entity, which can contain either legacy entity selectors or new entity selectors. This type is used to allow functions that accept entity selectors to also accept legacy entity selectors for backward compatibility. */
type BackwardCompatibleEntitySelector = BackwardCompatibleEntitySingleSelector | BackwardCompatibleEntitySingleSelector[];
type EntitySingleSelectorNormalized = {
    /** The element associated with this entity, or undefined to ignore the element in the matching process */
    element?: ElementSelectorNormalized;
    /** The file associated with this entity, or undefined to ignore the file in the matching process */
    file?: FileSelectorNormalized;
    /** The module associated with this entity, or undefined to ignore the module in the matching process */
    module?: ModuleSelectorNormalized;
};
/** Normalized selector for an entity, being always an array of single selectors */
type EntitySelectorNormalized = EntitySingleSelectorNormalized[];

/**
 * Matcher class to determine if entities match a given entity selector.
 */
declare class EntitiesMatcher extends BaseElementsMatcher {
    /**
     * Elements matcher to use for matching elements within entities.
     */
    private readonly _elementsMatcher;
    private readonly _filesMatcher;
    private readonly _modulesMatcher;
    /**
     * Creates a new EntitiesMatcher.
     * @param elementsMatcher Elements matcher to use for matching elements within entities.
     * @param config Configuration options for the matcher.
     * @param micromatch Micromatch instance for matching.
     * @param globalCache Global cache instance.
     */
    constructor(elementsMatcher: ElementsMatcher, filesMatcher: FilesMatcher, modulesMatcher: ModulesMatcher, config: MatchersOptionsNormalized, micromatch: Micromatch);
    /**
     * Returns the selectors matching result for the given entity.
     * @param entity The entity description.
     * @param selector The entity selector normalized.
     * @param extraTemplateData The extra template data for selector values.
     * @returns The selectors matching result for the given entity.
     */
    private _getSingleSelectorMatching;
    /**
     * Returns the selectors matching result for the given entity.
     * @param entity The entity to check.
     * @param selector The selector to check against.
     * @param options Extra options for matching, such as templates data, etc.
     * @returns The matching result for the entity against the selector.
     */
    getSelectorMatching(entity: EntityDescription, selector: BackwardCompatibleEntitySelector, { extraTemplateData }?: MatcherOptions): EntitySingleSelectorMatchResult | null;
    /**
     * Returns whether the given entity matches the selector.
     * @param entity The entity to check.
     * @param selector The selector to check against.
     * @param options Extra options for matching, such as templates data, etc.
     * @returns Whether the entity matches the selector properties.
     */
    isEntityMatch(entity: EntityDescription, selector: BackwardCompatibleEntitySelector, options?: MatcherOptions): boolean;
}

/**
 * Determines if the given entity selector is a legacy entity selector, in the form of a legacy element selector or an element selector
 * @param selector The selector to check.
 * @returns True if the selector is a legacy entity selector, false otherwise.
 */
declare function isLegacyEntitySingleSelector(selector: unknown): selector is LegacyEntitySingleSelector;
/**
 * Determines if the given entity selector is a legacy entity selector, in the form of a legacy element selector or an element selector
 * @param selector The selector to check.
 * @returns True if the selector is a legacy entity selector, false otherwise.
 */
declare function isLegacyEntitySelector(selector?: unknown): selector is LegacyEntitySelector;
/**
 * Determines if the given selector is a single entity selector
 * @param value The value to check.
 * @returns True if the selector is a single entity selector, false otherwise.
 */
declare function isEntitySingleSelector(value: unknown): value is EntitySingleSelector;
/**
 * Determines if the given value is an entity selector.
 * @param value The value to check.
 * @returns True if the value is an entity selector, false otherwise.
 */
declare function isEntitySelector(value: unknown): value is EntitySingleSelector | EntitySingleSelector[];
/**
 * Normalizes a single entity selector, ensuring it has the correct structure and default values.
 * @param selector The selector to normalize.
 * @returns The normalized selector.
 */
declare function normalizeSingleEntitySelector(selector: BackwardCompatibleEntitySingleSelector): EntitySelectorNormalized;
/**
 * Normalizes an EntitySelector into an array of EntitySingleSelector.
 * @param entitySelector The entity selector, in any supported format.
 * @returns The normalized array of single entity selectors.
 */
declare function normalizeEntitySelector(entitySelector: BackwardCompatibleEntitySelector): EntitySelectorNormalized;

/**
 * Selector for dependency information.
 */
type DependencyInfoSingleSelector = {
    /** Relationship between both elements, from both perspectives */
    relationship?: {
        /** Relationship from dependant element perspective */
        from?: MicromatchPatternNullable;
        /** Relationship from dependency element perspective */
        to?: MicromatchPatternNullable;
    };
    /** Dependency kind to filter elements */
    kind?: MicromatchPatternNullable;
    /** Micromatch pattern(s) to match only specific imports/exports */
    specifiers?: MicromatchPatternNullable;
    /** Node kind to filter elements */
    nodeKind?: MicromatchPatternNullable;
    /** Dependency source used in import/export statements */
    source?: MicromatchPatternNullable;
};
type LegacyDependencyInfoSingleSelector = DependencyInfoSingleSelector & {
    /**
     * @deprecated Module source used in import/export statements (legacy property, use 'source' instead)
     **/
    module?: MicromatchPatternNullable;
};
type LegacyDependencyInfoSelector = LegacyDependencyInfoSingleSelector | LegacyDependencyInfoSingleSelector[];
type BackwardCompatibleDependencyInfoSingleSelector = DependencyInfoSingleSelector | LegacyDependencyInfoSingleSelector;
type BackwardCompatibleDependencyInfoSelector = BackwardCompatibleDependencyInfoSingleSelector | BackwardCompatibleDependencyInfoSingleSelector[];
/** Dependency information selector, which can be a single selector or an array of selectors. */
type DependencyInfoSelector = DependencyInfoSingleSelector | DependencyInfoSingleSelector[];
/** Normalized dependency information selector, where all properties are always arrays */
type DependencyInfoSelectorNormalized = DependencyInfoSingleSelector[];
/** Legacy dependency selector containing legacy entity selectors for 'from' and 'to'; */
type LegacyDependencySingleSelector = {
    to?: LegacyEntitySelector | EntitySelector;
    from?: LegacyEntitySelector | EntitySelector;
    dependency?: LegacyDependencyInfoSelector | DependencyInfoSelector;
};
type LegacyDependencySelector = LegacyDependencySingleSelector | LegacyDependencySingleSelector[];
/**
 * Dependency selector, which includes optional 'from' and 'to' entities selectors.
 */
type DependencySingleSelector = {
    /** Selector for the dependant entities. The entity originating the dependency */
    from?: EntitySelector;
    /** Selector for the dependency entities. The entity being imported/exported */
    to?: EntitySelector;
    /** Selector for dependency metadata */
    dependency?: DependencyInfoSelector;
};
/** Dependency selector, which can be a single selector or an array of selectors. */
type DependencySelector = DependencySingleSelector | DependencySingleSelector[];
type BackwardCompatibleDependencySingleSelector = DependencySingleSelector | LegacyDependencySingleSelector;
type BackwardCompatibleDependencySelector = BackwardCompatibleDependencySingleSelector | BackwardCompatibleDependencySingleSelector[];
/**
 * Normalized dependency selector, where 'from' and 'to' are always arrays or null.
 */
type DependencySingleSelectorNormalized = {
    /** Selector for the dependant entities. The entity originating the dependency */
    from?: EntitySelectorNormalized;
    /** Selector for the dependency entities. The entity being imported/exported */
    to?: EntitySelectorNormalized;
    /** Selector for dependency metadata */
    dependency?: DependencyInfoSelectorNormalized;
};
/** Normalized dependency selector, which can be a single normalized selector or an array of normalized selectors. */
type DependencySelectorNormalized = DependencySingleSelectorNormalized[];

/**
 * The result of matching a single dependency selector, containing the matching results for each selector property (from, to and dependency).
 */
type DependencySingleSelectorMatchResult = {
    /** The single selector matching result for the 'from' entity. */
    from?: EntitySingleSelectorMatchResult;
    /** The single selector matching result for the 'to' entity. */
    to?: EntitySingleSelectorMatchResult;
    /** The single selector matching result for the dependency information. */
    dependency?: DependencyInfoSingleSelector;
};
/**
 * Result of matching an element selector against an element.
 */
type DependencyMatchResult = {
    selector: DependencySingleSelectorMatchResult | null;
    /** Whether the dependency matches all the selector properties provided */
    isMatch: boolean;
};

/**
 * Matcher class to determine if dependencies match a given dependencies selector.
 */
declare class DependenciesMatcher extends BaseElementsMatcher {
    /**
     * Entities matcher to use for matching entities within dependencies.
     */
    private readonly _entitiesMatcher;
    /**
     * Creates a new DependenciesMatcher.
     * @param entitiesMatcher Entities matcher to use for matching entities within dependencies.
     * @param config Configuration options for the matcher.
     * @param micromatch Micromatch instance for matching.
     * @param globalCache Global cache instance.
     */
    constructor(entitiesMatcher: EntitiesMatcher, config: MatchersOptionsNormalized, micromatch: Micromatch);
    /**
     * Returns the selectors matching result for the given dependency.
     * @param dependency The dependency description.
     * @param selector The dependency selector normalized.
     * @param extraTemplateData The extra template data for selector values.
     * @returns The selectors matching result for the given dependency.
     */
    private _getSingleSelectorMatching;
    /**
     * Determines if the dependency relationship matches the selector.
     * @param dependency The dependency description.
     * @param selector The data of an element selector.
     * @returns Whether the dependency relationship matches the selector.
     */
    private _relationshipFromMatches;
    /**
     * Determines if the dependency origin relationship matches the selector.
     * @param selector The dependency selector data.
     * @param relationship The relationship from origin element to target element.
     * @param templateData The template data for rendering selector values.
     * @returns Whether the dependency origin relationship matches.
     */
    private _relationshipToMatches;
    /**
     * Determines if the selector matches an specific kind
     * @param selector The dependency selector data
     * @param kind Kind to check
     * @param templateData The template data for rendering selector values
     * @returns Whether the selector matches the kind
     */
    private _kindMatches;
    /**
     * Determines if the selector matches some of the specifiers
     * @param selector The dependency selector data
     * @param specifiers Specifiers to check
     * @param templateData The template data for rendering selector values
     * @returns Whether the selector matches some of the specifiers
     */
    private _specifierMatches;
    /**
     * Determines if the selector matches the nodeKind
     * @param selector The dependency selector data
     * @param nodeKind The nodeKind to check
     * @param templateData The template data for rendering selector values
     * @returns Whether the selector matches the nodeKind
     */
    private _nodeKindMatches;
    /**
     * Determines if the dependency description matches the selector for 'to'.
     * @param dependency The dependency description.
     * @param toSelector The selector for 'to' elements.
     * @param templateData The template data for rendering selector values
     * @returns Whether the dependency properties match the selector for 'to'.
     */
    private _sourceMatches;
    /**
     * Determines if the dependency description matches the selector for dependency metadata.
     * @param dependency The dependency description.
     * @param selectorData The selector for dependency metadata.
     * @param templateData The template data for rendering selector values
     * @returns Whether the dependency properties match the selector.
     */
    private _dependencyPropertiesMatch;
    /**
     * Returns the selectors matching result for the given dependency.
     * @param dependency The dependency to check.
     * @param selector The selector to check against.
     * @param options Extra options for matching, such as templates data, etc.
     * @returns The matching result for the dependency against the selector.
     */
    getSelectorMatching(dependency: DependencyDescription, selector: BackwardCompatibleDependencySelector, { extraTemplateData }?: MatcherOptions): DependencySingleSelectorMatchResult | null;
    /**
     * Returns whether the given dependency matches the selector.
     * @param dependency The dependency to check.
     * @param selector The selector to check against.
     * @param options Extra options for matching, such as templates data, etc.
     * @returns Whether the dependency matches the selector properties.
     */
    isDependencyMatch(dependency: DependencyDescription, selector: BackwardCompatibleDependencySelector, options?: MatcherOptions): boolean;
}

/**
 * Determines if the given selector is a legacy dependency info single selector.
 * @param selector The selector to check.
 * @returns True if the selector is a legacy dependency info single selector, false otherwise.
 */
declare function isLegacyDependencyInfoSingleSelector(selector: unknown): selector is LegacyDependencyInfoSingleSelector;
declare function isLegacyDependencyInfoSelector(selector: unknown): selector is LegacyDependencyInfoSelector;
/**
 * Determines if the given value is dependency information selector
 * @param value The value to check.
 * @returns True if the value is dependency information selector, false otherwise.
 */
declare function isDependencyInfoSingleSelector(value: unknown): value is DependencyInfoSingleSelector;
/**
 * Determines if the given value is dependency information selector(s).
 * @param value The value to check.
 * @returns True if the value is dependency information selector(s), false otherwise.
 */
declare function isDependencyInfoSelector(value: unknown): value is DependencyInfoSelector;
declare function isBackwardCompatibleDependencyInfoSingleSelector(selector: unknown): selector is BackwardCompatibleDependencyInfoSingleSelector;
declare function isBackwardCompatibleDependencyInfoSelector(selector: unknown): selector is BackwardCompatibleDependencyInfoSelector;
declare function normalizeLegacyDependencyInfoSingleSelector(selector: LegacyDependencyInfoSingleSelector): DependencyInfoSingleSelector;
declare function isBaseDependencySingleSelector(selector: unknown): selector is {
    from?: unknown;
    to?: unknown;
    dependency?: unknown;
};
declare function isLegacyDependencySingleSelector(selector: unknown): selector is LegacyDependencySingleSelector;
declare function isLegacyDependencySelector(selector: unknown): selector is LegacyDependencySelector;
/**
 * Determines if the given value is a dependency single selector.
 * @param value The value to check
 * @returns True if the value is a dependency selector, false otherwise.
 */
declare function isDependencySingleSelector(value: unknown): value is DependencySingleSelector;
/**
 * Determines if the given value is a dependency selector, which can be a single selector or an array of selectors.
 * @param value The value to check
 * @returns True if the value is a dependency selector, false otherwise.
 */
declare function isDependencySelector(value: unknown): value is DependencySelector;
declare function isBackwardCompatibleDependencySingleSelector(selector: unknown): selector is BackwardCompatibleDependencySingleSelector;
declare function isBackwardCompatibleDependencySelector(selector: unknown): selector is BackwardCompatibleDependencySelector;
/**
 * Normalizes a single dependency information selector, ensuring it has the correct structure and default values.
 * @param selector The selector to normalize.
 * @returns The normalized selector.
 */
declare function normalizeSingleDependencyInfoSelector(selector: BackwardCompatibleDependencyInfoSingleSelector): DependencyInfoSingleSelector;
declare function normalizeDependencyInfoSelector(selector: BackwardCompatibleDependencyInfoSelector): DependencyInfoSelectorNormalized;
declare function normalizeLegacyDependencySingleSelector(selector: LegacyDependencySingleSelector): DependencySelectorNormalized;
/**
 * Normalizes a single entity selector, ensuring it has the correct structure and default values.
 * @param selector The selector to normalize.
 * @returns The normalized selector.
 */
declare function normalizeSingleDependencySelector(selector: BackwardCompatibleDependencySingleSelector): DependencySelectorNormalized;
/**
 * Normalizes a dependency selector, which can be a single selector or an array of selectors, ensuring it has the correct structure and default values.
 * @param selector The selector to normalize.
 * @returns The normalized selector.
 */
declare function normalizeDependencySelector(selector: BackwardCompatibleDependencySelector): DependencySelectorNormalized;

/**
 * Serialized cache of matcher descriptors.
 */
type MatcherSerializedCache = {
    descriptors: DescriptorsSerializedCache;
};

/**
 * Matcher class to evaluate if elements or dependencies match given selectors.
 */
declare class Matcher {
    private readonly _elementsMatcher;
    private readonly _filesMatcher;
    private readonly _entitiesMatcher;
    private readonly _modulesMatcher;
    private readonly _dependenciesMatcher;
    private readonly _originalDescriptors;
    private readonly _descriptorOptions;
    private readonly _micromatch;
    private readonly _descriptors;
    /**
     * Constructor for the Matcher class.
     * @param options The options to configure the Matcher instance, including descriptors, matchers for elements and dependencies, and micromatch instance for pattern matching.
     * @param options.descriptors The descriptors configuration to use for describing elements and dependencies.
     * @param options.options.descriptors The normalized descriptor options to use for describing elements and dependencies.
     * @param options.options.matchers The matchers configuration for elements and dependencies.
     * @param options.micromatch The micromatch instance to use for pattern matching.
     */
    constructor({ descriptors, options: { descriptors: descriptorOptions, matchers: matchersOptions }, micromatch, }: {
        descriptors: DescriptorsConfig;
        options: {
            descriptors: DescriptorOptionsNormalized;
            matchers: MatchersOptionsNormalized;
        };
        micromatch: Micromatch;
    });
    /**
     * Describes an element given its file path.
     * @param filePath The path of the file to describe.
     * @returns The description of the element.
     */
    describeElement(filePath: string): ElementDescription;
    /**
     * Describes elements in a dependency relationship, and provides additional information about the dependency itself.
     * @param options The options for describing the elements and the dependency details.
     * @returns The description of the dependency between the elements.
     */
    describeDependency(options: DependencyDescriptorOptions): DependencyDescription;
    /**
     * Describes an entity given its file path, including both the file, element and origin description.
     * @param filePath The path of the file to describe.
     * @param source The optional dependency source (e.g., the importer file path) to use for describing the origin of the entity being imported.
     * @returns The description of the entity.
     */
    describeEntity(filePath?: string, source?: string): EntityDescription;
    /**
     * Describes the module of a file given its path and the path of the importer file.
     * @param filePath The path of the file to describe.
     * @param source The optional dependency source (e.g., the importer file path) to use for describing the module of the entity being imported.
     * @returns The description of the file's module.
     */
    describeModule(filePath?: string, source?: string): ModuleDescription;
    /**
     * Returns the description of a file given its path.
     * @param filePath The path of the file to describe.
     * @returns The description of the file.
     */
    describeFile(filePath: string): FileDescription;
    /**
     * Determines if an element matches a given selector.
     * @param filePath The file path of the element
     * @param selector The selector to match against
     * @param options Extra matcher options
     * @returns True if the element matches the selector, false otherwise
     */
    isElementMatch(filePath: string, selector: BackwardCompatibleElementSelector, options?: MatcherOptions): boolean;
    /**
     * Determines if a dependency matches a given selector.
     * @param dependencyData The data describing the dependency
     * @param selector The selector to match against
     * @param options Extra matcher options
     * @returns True if the dependency matches the selector, false otherwise
     */
    isDependencyMatch(dependencyData: DependencyDescriptorOptions, selector: BackwardCompatibleDependencySelector, options?: MatcherOptions): boolean;
    /**
     * Determines if an entity matches a given selector.
     * @param filePath The file path of the entity
     * @param selector The selector to match against
     * @param options Extra matcher options
     * @returns True if the entity matches the selector, false otherwise
     */
    isEntityMatch(filePath: string, selector: BackwardCompatibleEntitySelector, options?: EntityMatcherOptions): boolean;
    /**
     * Determines if an origin matches a given selector.
     * @param filePath The file path of the origin
     * @param selector The selector to match against
     * @param options Extra matcher options
     * @returns True if the module matches the selector, false otherwise
     */
    isModuleMatch(filePath: string, selector: ModuleSelector, options?: EntityMatcherOptions): boolean;
    /**
     * Determines if a file matches a given selector.
     * @param filePath The file path to check
     * @param selector The selector to match against
     * @param options Extra matcher options
     * @returns True if the file matches the selector, false otherwise
     */
    isFileMatch(filePath: string, selector: FileSelector, options?: MatcherOptions): boolean;
    /**
     * Determines if an entity matches a given selector.
     * @param filePath The file path of the entity
     * @param selector The selector to match against
     * @param options Extra matcher options
     * @returns True if the entity matches the selector, false otherwise
     */
    getEntitySelectorMatching(filePath: string, selector: BackwardCompatibleEntitySelector, options?: EntityMatcherOptions): EntitySingleSelectorMatchResult | null;
    /**
     * Determines the selector matching for an element.
     * @param filePath The file path of the element
     * @param selector The selectors to match against
     * @param options Extra options for matching
     * @returns The matching selector data or null if no match is found
     */
    getElementSelectorMatching(filePath: string, selector: BackwardCompatibleElementSelector, options?: MatcherOptions): ElementSingleSelectorMatchResult | null;
    /**
     * Determines the selector matching for a dependency.
     * @param dependencyData The data describing the dependency
     * @param selector The selectors to match against
     * @param options Extra options for matching
     * @returns The matching dependency result or null if no match is found
     */
    getDependencySelectorMatching(dependencyData: DependencyDescriptorOptions, selector: BackwardCompatibleDependencySelector, options?: MatcherOptions): DependencySingleSelectorMatchResult | null;
    /**
     * Determines the selector matching for an origin.
     * @param filePath The file path of the origin
     * @param selector The selector to match against
     * @param options Extra options for matching
     * @returns The matching module result or null if no match is found
     */
    getModuleSelectorMatching(filePath: string, selector: ModuleSelector, options?: EntityMatcherOptions): ModuleSingleSelector | null;
    /**
     * Determines the selector matching for a file.
     * @param filePath The file path to check
     * @param selector The selector to match against
     * @param options Extra options for matching
     * @returns The matching file selector or null if no match is found
     */
    getFileSelectorMatching(filePath: string, selector: FileSelector, options?: MatcherOptions): FileSingleSelector | null;
    /**
     * Returns the first selector matching result for the given entity and selector.
     * @param description The entity description to check.
     * @param selector The selector to check against.
     * @param options Extra options for matching, such as templates data, etc.
     * @returns The first selector matching result for the given entity and selector, or null if no match is found.
     */
    getEntitySelectorMatchingDescription(description: EntityDescription, selector: BackwardCompatibleEntitySelector, options?: MatcherOptions): EntitySingleSelectorMatchResult | null;
    /**
     * Returns the selectors matching result for the given element or dependency description.
     * @param description The element or dependency  description to check.
     * @param selector The selector to check against.
     * @param options Extra options for matching, such as templates data, etc.
     * @returns The selectors matching result for the given description, and whether it matches or not.
     */
    getDependencySelectorMatchingDescription(description: DependencyDescription, selector: BackwardCompatibleDependencySelector, options?: MatcherOptions): DependencySingleSelectorMatchResult | null;
    /**
     * Returns the first element selector matching result for the given element description.
     * @param description The element description to check.
     * @param selector The selector to check against.
     * @param options Extra options for matching, such as templates data, etc.
     * @returns The first matching selector result for the given description, or null if no match is found.
     */
    getElementSelectorMatchingDescription(description: ElementDescription, selector: BackwardCompatibleElementSelector, options?: MatcherOptions): ElementSingleSelector | null;
    getModuleSelectorMatchingDescription(description: ModuleDescription, selector: ModuleSelector, options?: EntityMatcherOptions): ModuleSingleSelector | null;
    /**
     * Returns the first file selector matching result for the given file description.
     * @param description The file description to check.
     * @param selector The selector to check against.
     * @param options Extra options for matching, such as templates data, etc.
     * @returns The first matching selector result for the given description, or null if no match is found.
     */
    getFileSelectorMatchingDescription(description: FileDescription, selector: FileSelector, options?: MatcherOptions): FileSingleSelector | null;
    /**
     * Clears all caches.
     */
    clearCache(): void;
    /**
     * Serializes the descriptors matchers cache to a plain object.
     * @returns The serialized cache
     */
    serializeCache(): MatcherSerializedCache;
    /**
     * Sets the descriptors matchers cache from a serialized object.
     * @param serializedCache The serialized cache
     */
    setCacheFromSerialized(serializedCache: {
        descriptors: ReturnType<Descriptors["serializeCache"]>;
    }): void;
}

/**
 * Pattern(s) to match files for a descriptor.
 */
type DescriptorPattern = string | string[];
/**
 * Descriptor for an element or file in the project.
 * Defines the type of the element or file, the pattern to match files, and optional settings;
 */
type BaseDescriptor = {
    /** Micromatch pattern(s) to match files belonging to this descriptor. */
    pattern: DescriptorPattern;
    /**
     * It allows to capture values of some fragments in the matching path to use them later in the rules configuration.
     * Must be an array of strings representing the names of the capture groups in the pattern.
     * The number of capture names must be equal to the number of capturing groups in the pattern.
     * For example, if the pattern is "src/modules/(* *)/(* *).service.js" the capture could be ["module", "service"].
     * Then, in the rules configuration, you could use ["service", { module: "auth" }] to match only services from the auth module.
     */
    capture?: string[];
    /**
     * When `true`, if this descriptor matches, previously accumulated matches (at the same level) are kept
     * and no further descriptors are evaluated for this file/level. Default `false` (accumulate).
     */
    stopMatching?: boolean;
    /**
     * When `true`, if this descriptor matches, previously accumulated matches (at the same level) are discarded,
     * only this descriptor's match is kept, and no further descriptors are evaluated. Takes precedence over
     * `stopMatching` when both are set. Default `false` (accumulate).
     */
    exclusive?: boolean;
};

/**
 * Map of the modes to interpret the pattern in an ElementDescriptor.
 */
declare const ELEMENT_DESCRIPTOR_MODES_MAP: {
    /** Mode to interpret the pattern as a folder */
    readonly FOLDER: "folder";
    /** Mode to interpret the pattern as a file */
    readonly FILE: "file";
    /** Mode to interpret the pattern as a full path */
    readonly FULL: "full";
};
/**
 * Mode to interpret the pattern in an ElementDescriptor.
 */
type ElementDescriptorMode = (typeof ELEMENT_DESCRIPTOR_MODES_MAP)[keyof typeof ELEMENT_DESCRIPTOR_MODES_MAP];
/**
 * Element descriptor, which must define a pattern and a type. The pattern is used to match files and capture values, while the type is used to categorize the element.
 */
type ElementDescriptor = BaseDescriptor & {
    /** Type of the element (e.g., "service", "component", "util"). */
    type?: string;
    /**
     * Category of the element
     * @deprecated The category property is deprecated and will be removed in future versions. Use the category property in file descriptors instead to add multiple categories to different files in the same element, instead of categorizing the whole element with a single category. This allows for more flexibility and better organization of files within an element.
     **/
    category?: string;
    /**
     * The mode to interpret the pattern in the descriptor. It can be "folder", "file", or "full".
     * @deprecated The mode property is deprecated and will be removed in future versions. For file descriptors, the mode is always "file". For element descriptors, the mode is always "folder". Use `partialMatch: false` in element descriptors to require full path matching instead.
     */
    mode?: ElementDescriptorMode;
    /**
     * Optional micromatch pattern. If provided, the left side of the descriptor path must match also with this pattern from the root of the project (like if pattern is [basePattern]/** /[pattern]).
     * This option is only useful when `fullMatch` is false (default), but capturing fragments from the rest of the full path is also needed.
     **/
    basePattern?: string;
    /**
     * Like capture, but for the basePattern.
     * This allows to capture values from the left side of the path, which is useful when using the basePattern option.
     * The captured values will be merged with the ones from the capture option. If the same name is used in both captures, the value from capture will take precedence.
     */
    baseCapture?: string[];
    /**
     * Whether the pattern is allowed to match only a suffix of the file path.
     *
     * When `true` (the default), the pattern is matched using right-to-left incremental
     * segment accumulation, so it only needs to match the end of the path: `components/*`
     * matches `src/components/Button`, `packages/ui/src/components/Button`, and any other
     * path ending in `components/<something>`, without writing the full prefix.
     *
     * When `false`, the pattern is matched against the full file path from the project root
     * (relative to `rootPath`). The pattern is still expanded with `/**\/*` (folder
     * semantics), so the resolved element `path` is the matched folder prefix, not the full
     * file path, and `fileInternalPath` is computed the same way as in folder mode. When set
     * to `false`, the `mode` option has no effect.
     *
     * This option defaults to `true` for backward compatibility. It will most likely default
     * to `false` in a future major version, and eventually be removed, because matching the
     * full pattern is more intuitive and is already the behavior of file descriptors (which
     * have no equivalent option).
     */
    partialMatch?: boolean;
};
/**
 * Array of element descriptors.
 */
type ElementDescriptors = ElementDescriptor[];
/**
 * Serialized cache of ElementsDescriptor class, which is a record of element descriptions indexed by their paths.
 */
type ElementsDescriptorSerializedCache = Record<string, ElementDescription>;

/**
 * Class describing elements in a project given their paths and configuration.
 */
declare class ElementsDescriptor {
    /**
     * Cache to store previously described elements.
     */
    private readonly _descriptionsCache;
    /**
     * Cache storing the folder-stable base description for each folder.
     * Multiple files in the same folder share the same base (path, types, category,
     * captured, parents), so it is computed once per folder and extended per file with
     * the file-specific fields (fileInternalPath, isIgnored).
     */
    private readonly _folderDescriptionsCache;
    /**
     * Whether the folder-level cache can be used. It is only sound when no descriptor
     * relies on the file name to match, i.e. no descriptor uses the deprecated "file" or
     * "full" modes. In those modes a sibling file could match a different descriptor, so
     * the description is not folder-deterministic and the per-file path must be used.
     */
    private readonly _canCacheByFolder;
    /**
     * Configuration instance for this descriptor.
     */
    private readonly _config;
    /**
     * Element descriptors used by this descriptor.
     */
    private readonly _elementDescriptors;
    /** Micromatch instance for path matching */
    private readonly _micromatch;
    /** Whether single-type matching is enabled (only first matching type is kept) */
    private readonly _singleType;
    /** Shared path helper providing root-path and include/ignore utilities */
    private readonly _pathHelper;
    /**
     * The configuration options for this descriptor.
     * @param elementDescriptors The element descriptors.
     * @param configOptions The configuration options.
     * @param globalCache The global cache for various caching needs.
     * @param micromatch The micromatch instance for path matching.
     * @param singleType Whether single-type matching is enabled.
     */
    constructor(elementDescriptors: ElementDescriptors, configOptions: DescriptorOptionsNormalized, micromatch: Micromatch, singleType?: boolean);
    /**
     * Serializes the elements cache to a plain object.
     * @returns The serialized elements cache.
     */
    serializeCache(): ElementsDescriptorSerializedCache;
    /**
     * Sets the elements cache from a serialized object.
     * @param serializedCache The serialized elements cache.
     */
    setCacheFromSerialized(serializedCache: ElementsDescriptorSerializedCache): void;
    /**
     * Clears the elements cache.
     */
    clearCache(): void;
    /**
     * Validates the element descriptors to ensure they are correctly defined.
     */
    private _validateDescriptors;
    /**
     * Gets the element path based on the path pattern, path segments to the element, and all path segments from the file path.
     * @param pathPattern The element path pattern.
     * @param pathSegments The path segments leading to the element.
     * @param allPathSegments The full path segments from the file path.
     * @returns The element path.
     */
    private _getElementPath;
    /**
     * Gets the element folder path for a `partialMatch: false` descriptor.
     * Walks `filePath` from the project root and returns the first prefix that satisfies
     * `basePattern`. This gives the folder path rather than the full file path.
     * @param basePattern The raw element pattern WITHOUT the `/**\/*` suffix.
     * @param filePath The full file path relative to rootPath.
     * @returns The folder path prefix that the pattern matches.
     */
    private _getFullFolderMatchElementPath;
    /**
     * Determines if an element descriptor matches the given parameters in the provided path.
     * @param options The options for matching the descriptor.
     * @returns The result of the match, including whether it matched and any captured values.
     */
    private _fileDescriptorMatch;
    /**
     * Describes an element given its file path
     * @param elementPath The path of the element to describe.
     * @returns The description of the element.
     */
    private _describeElement;
    /**
     * Sets the main element data on the element result being built.
     * @param elementResult The element result being built.
     * @param elementDescriptor The descriptor that matched as the main element.
     * @param elementPath The resolved path of the main element.
     * @param filePath The full file path being described.
     * @param capturedValues The captured values for this match.
     */
    private _setMainElement;
    /**
     * Applies a matching descriptor's types/category/captured values onto an accumulated
     * element or parent level. When the descriptor is `exclusive`, previously accumulated
     * types, category and captured values at that level are discarded and replaced with
     * this descriptor's match instead; otherwise the type and captured values are merged
     * into the existing accumulation.
     * @param target The element result or parent being built at this level.
     * @param elementDescriptor The descriptor that matched at this level.
     * @param capturedValues The captured values for this match.
     */
    private _applyAccumulatedMatch;
    /**
     * Adds a new parent element or merges into the last parent when it resolves to the same path.
     * @param parents The accumulated list of parent elements.
     * @param elementDescriptor The descriptor that matched as a parent.
     * @param elementPath The resolved path of the parent element.
     * @param capturedValues The captured values for this match.
     */
    private _addOrMergeParent;
    /**
     * Gets the folder key used to cache the folder-stable base description.
     * @param relativePath The relative file path.
     * @returns The folder portion of the path (everything but the last segment, empty for a file at the root).
     */
    private _getFolderKey;
    /**
     * Gets the file path relative to its element folder.
     * This is only used in the folder-cacheable branch, where all descriptors are in
     * folder mode, so the element path is always a folder containing the file.
     * @param relativePath The relative file path.
     * @param elementPath The matched element path.
     * @returns The file path relative to the element folder.
     */
    private _getFileInternalPath;
    /**
     * Describes an element reusing a folder-level cache.
     * The folder-stable base (path, types, category, captured, parents) is computed once
     * per folder and extended per file with the file-specific fields.
     * @param relativePath The relative file path.
     * @returns The description of the element.
     */
    private _describeElementWithFolderCache;
    /**
     * Describes the element of a file given its path.
     * @param filePath The path of the dependency target file, if known. Can be absolute if rootPath is configured, or relative if not.
     * @returns The description of the dependency element.
     */
    describeElement(filePath: string | undefined): ElementDescription;
}

/**
 * Determines if the given value is an element descriptor with type.
 * @param value The value to check.
 * @returns True if the value is an element descriptor with type, false otherwise.
 */
declare function isElementDescriptor(value: unknown): value is ElementDescriptor;

/**
 * Base file properties related to captured values
 */
type FileDescription = BaseDescription & {
    /** Categories of the file, or null if the file is ignored or unknown */
    categories: string[] | null;
};
/**
 * Description of an ignored file
 */
type IgnoredFileDescription = FileDescription & BaseIgnoredDescription & {
    /** Categories of the file */
    categories: null;
};
/**
 * Description of an unknown local element
 */
type UnknownFileDescription = FileDescription & BaseUnknownDescription & {
    /** Categories of the file */
    categories: null;
};
type KnownFileDescription = FileDescription & BaseKnownDescription & {
    /** Known files always have path  and categories */
    path: string;
    /** Categories of the file */
    categories: string[];
};

/**
 * File descriptor, which must define a pattern and a category. The pattern is used to match files and capture values, while the category is used to categorize the file.
 */
type FileDescriptor = BaseDescriptor & {
    /** Category of the file (e.g., "service", "component", "util"). */
    category: string;
    /**
     * @deprecated Backward compatibility with legacy element descriptors with mode "file". This option will be removed in future versions.
     **/
    type?: string;
    /**
     * Optional micromatch pattern. If provided, the left side of the descriptor path must match also with this pattern from the root of the project (like if pattern is [basePattern]/** /[pattern]).
     * This option is only useful when `fullMatch` is false (default), but capturing fragments from the rest of the full path is also needed.
     * @deprecated Used only internally for backward compatibility with legacy element descriptors with mode "file". This option will be removed in future versions.
     **/
    basePattern?: string;
    /**
     * Like capture, but for the basePattern.
     * This allows to capture values from the left side of the path, which is useful when using the basePattern option.
     * The captured values will be merged with the ones from the capture option. If the same name is used in both captures, the value from capture will take precedence.
     * @deprecated Used only internally for backward compatibility with legacy element descriptors with mode "file". This option will be removed in future versions.
     */
    baseCapture?: string[];
};
/**
 * Array of file descriptors.
 */
type FileDescriptors = FileDescriptor[];
/**
 * Serialized cache of file descriptions.
 */
type FileDescriptionsSerializedCache = Record<string, FileDescription>;
/**
 * Serialized cache for FilesDescriptor class.
 */
type FilesDescriptorSerializedCache = {
    /** Serialized descriptions cache */
    descriptions: FileDescriptionsSerializedCache;
};

/**
 * Class describing files in a project given their paths and configuration.
 */
declare class FilesDescriptor {
    /**
     * Cache to store previously described files.
     */
    private readonly _descriptionsCache;
    /**
     * Configuration instance for this descriptor.
     */
    private readonly _config;
    /**
     * File descriptors used by this descriptor.
     */
    private readonly _fileDescriptors;
    /** Micromatch instance for path matching */
    private readonly _micromatch;
    /** Shared path helper providing root-path and include/ignore utilities */
    private readonly _pathHelper;
    /**
     * When `true`, only the first matching file descriptor's category is kept and matching stops.
     * Global shorthand equivalent to setting `stopMatching: true` on every file descriptor.
     */
    private readonly _singleMatch;
    /**
     * The configuration options for this descriptor.
     * @param fileDescriptors The file descriptors.
     * @param configOptions The configuration options.
     * @param micromatch The micromatch instance for path matching.
     * @param singleMatch When `true`, only the first matching file descriptor's category is used; matching stops.
     */
    constructor(fileDescriptors: FileDescriptors, configOptions: DescriptorOptionsNormalized, micromatch: Micromatch, singleMatch?: boolean);
    /**
     * Serializes the elements cache to a plain object.
     * @returns The serialized elements cache.
     */
    serializeCache(): FilesDescriptorSerializedCache;
    /**
     * Sets the elements cache from a serialized object.
     * @param serializedCache The serialized files cache.
     */
    setCacheFromSerialized(serializedCache: FilesDescriptorSerializedCache): void;
    /**
     * Clears the files cache.
     */
    clearCache(): void;
    /**
     * Validates the file descriptors to ensure they are correctly defined.
     */
    private _validateDescriptors;
    /**
     * Determines if a file descriptor matches the provided file path, and captures values if it matches.
     * @param options The options for matching the descriptor.
     * @param options.fileDescriptor The file descriptor to match against.
     * @param options.filePath The file path to match against the descriptor.
     * @returns The result of the match, including whether it matched.
     */
    private _fileDescriptorMatch;
    /**
     * Returns the capture array for a file descriptor. When basePattern is used, combines baseCapture
     * and capture for backward compatibility with legacy mode "file". Otherwise, returns the plain
     * capture array as-is, matching it directly against the pattern's own capture groups.
     * @param fileDescriptor The file descriptor to get the capture array for.
     * @returns The capture array, or undefined if no capture is configured.
     */
    private _getCaptureArray;
    /**
     * Retrieves the description of a local file given its path.
     * @param elementPath The path of the element to describe.
     * @returns The description of the element.
     */
    private _getFileDescription;
    /**
     * Describes a file given its path.
     * @param filePath The absolute path of the file to describe
     */
    describeFile(filePath?: string): FileDescription;
}

/**
 * Determines if the given value is a file description.
 * @param value The value to check.
 * @returns True if the value is a file description, false otherwise.
 */
declare function isFileDescription(value: unknown): value is FileDescription;
/**
 * Determines if the given file is unknown, because its type could not be determined.
 * @param value The value to check.
 * @returns True if the file is an unknown file, false otherwise.
 */
declare function isUnknownFileDescription(value: unknown): value is UnknownFileDescription;
/**
 * Determines if the given file is known, because its type was determined.
 * @param value The value to check.
 * @returns True if the file is a known file, false otherwise.
 */
declare function isKnownFileDescription(value: unknown): value is KnownFileDescription;
/**
 * Determines if the given file is ignored.
 * @param value The value to check.
 * @returns True if the file is an ignored file, false otherwise.
 */
declare function isIgnoredFileDescription(value: unknown): value is IgnoredFileDescription;

/**
 * Determines if the given value is a file descriptor.
 * @param value The value to check.
 * @returns True if the value is a file descriptor, false otherwise.
 */
declare function isFileDescriptor(value: unknown): value is FileDescriptor;

/**
 * Origins of a module, either local, external, or core.
 */
declare const ORIGINS_MAP: {
    /** Origin of local files */
    readonly LOCAL: "local";
    /** Origin of external files (usually from node_modules, but also files flagged as external due to configuration) */
    readonly EXTERNAL: "external";
    /** Origin of built-in files (Node.js core modules) */
    readonly CORE: "core";
};
/** Set of all possible origins, used for fast validation of origin values. */
declare const ORIGINS_SET: Set<"local" | "external" | "core">;
/**
 * Kind of module origin, either local, external, or core.
 */
type Origin = (typeof ORIGINS_MAP)[keyof typeof ORIGINS_MAP];
/** Description of a module */
type ModuleDescription = {
    /** Origin of the module, either local, external, or core */
    origin: Origin;
    /** Base source of the module for external/core modules, or null for local origins */
    source: string | null;
    /** Internal path of the file relative to the base for external/core modules, or null for local origins */
    internalPath: string | null;
};

/**
 * Serialized cache of module descriptions.
 */
type ModuleDescriptionsSerializedCache = Record<string, ModuleDescription>;
/**
 * Serialized cache for ModulesDescriptor class.
 */
type ModulesDescriptorSerializedCache = {
    /** Serialized descriptions cache */
    descriptions: ModuleDescriptionsSerializedCache;
};

/**
 * Class describing entity modules.
 */
declare class ModulesDescriptor {
    private _mod;
    /**
     * Cache to store previously described modules.
     */
    private readonly _descriptionsCache;
    /**
     * Configuration instance for this descriptor.
     */
    private readonly _config;
    /** Micromatch instance for path matching */
    private readonly _micromatch;
    /** Shared path helper providing root-path utilities */
    private readonly _pathHelper;
    /**
     * The configuration options for this descriptor.
     * @param configOptions The configuration options.
     * @param micromatch The micromatch instance for path matching.
     */
    constructor(configOptions: DescriptorOptionsNormalized, micromatch: Micromatch);
    /**
     * Loads the Node.js module to access built-in modules information when running in Node.js environment.
     */
    private _loadModuleInNode;
    /**
     * Determines if a dependency source is a core module.
     * @param dependencySource The source of the dependency to check.
     * @param baseDependencySource The base source of the dependency to check.
     * @returns True if the dependency source is a core module, false otherwise.
     */
    private _dependencySourceIsCoreModule;
    /**
     * Determines if a dependency source is scoped (e.g., @scope/package).
     * @param dependencySource The source of the dependency to check.
     * @returns True if the dependency source is scoped, false otherwise.
     */
    private _dependencySourceIsScoped;
    /**
     * Determines if a dependency source is external or an alias.
     * @param dependencySource The source of the dependency to check.
     * @returns True if the dependency source is external or an alias, false otherwise.
     */
    private _dependencySourceIsExternalOrScoped;
    /**
     * Gets the base source of an external module.
     * @param dependencySource The source of the dependency to check.
     * @returns The base source of the external module. (e.g., for "@scope/package/submodule", it returns "@scope/package")
     */
    private _getExternalOrCoreSourceModule;
    /**
     * Checks if a source string matches any of the provided patterns using micromatch.
     * @param patterns - Array of micromatch patterns
     * @param source - The source string to match against patterns
     * @returns True if the source matches any pattern, false otherwise
     */
    private _matchesAnyPattern;
    /**
     * Determines if an element is external based on its file path and dependency source.
     * Uses the flagAsExternal configuration to evaluate multiple conditions with OR logic:
     * - unresolvableAlias: Files whose path cannot be resolved (filePath is null)
     * - inNodeModules: Non-relative paths that include "node_modules"
     * - outsideRootPath: Resolved path is outside the configured root path (only if rootPath is configured)
     * - customSourcePatterns: Source matches any of the configured patterns
     * @param filePath The resolved file path (null if unresolved). Can be absolute if rootPath is configured, or relative if rootPath is not configured.
     * @param isOutsideRootPath Whether the file path is outside the configured root path.
     * @param dependencySource The import/export source string
     * @returns True if any of the configured conditions is met, false otherwise
     */
    private _isExternal;
    /**
     * Serializes the origins cache to a plain object.
     * @returns The serialized origins cache.
     */
    serializeCache(): ModulesDescriptorSerializedCache;
    /**
     * Sets the origins cache from a serialized object.
     * @param serializedCache The serialized origins cache.
     */
    setCacheFromSerialized(serializedCache: ModulesDescriptorSerializedCache): void;
    /**
     * Clears the origins cache.
     */
    clearCache(): void;
    /**
     * Gets the module description for a given relative path and source.
     * @param relativePath The relative path of the file.
     * @param dependencySource The source of the dependency (e.g., the import statement or require call).
     * @returns The description of the file's module.
     */
    private _getDependencyModuleDescription;
    /**
     * Gets the module description for a file that is not imported as a dependency.
     * @param isOutsideRootPath Indicates if the file is outside the configured root path.
     * @param relativePath The relative path of the file.
     * @returns The description of the file's module.
     */
    private _getFileModuleDescription;
    /**
     * Gets the origin description for a given relative path and source.
     * @param relativePath The relative path of the file.
     * @param source The source of the dependency (e.g., the import statement or require call).
     * @param isOutsideRootPath Whether the file path is outside the configured root path.
     * @returns The description of the file's module.
     */
    private _getModuleDescription;
    /**
     * Describes the module of a file path given its dependency source and the file path itself.
     * @param filePath The absolute path of the file to describe
     * @param source The source of the dependency (e.g., the import statement or require call)
     * @returns The description of the file's module, including its origin, and module if applicable
     */
    describeModule(filePath?: string, source?: string): ModuleDescription;
}

/**
 * Determines if the given value is an OriginDescription.
 * @param value The value to check.
 * @returns True if the value is an OriginDescription, false otherwise.
 */
declare function isOriginDescription(value: unknown): value is ModuleDescription;

/** Description of an entity, which is the main unit under analysis */
type EntityDescription = {
    /** The element associated with this entity */
    element: ElementDescription;
    /** The entity file */
    file: FileDescription;
    /** Module of the entity, either local, external, or core (built-in module) */
    module: ModuleDescription;
};

/**
 * Determines if the given value is an EntityDescription.
 * @param value The value to check.
 * @returns True if the value is an EntityDescription, false otherwise.
 */
declare function isEntityDescription(value: unknown): value is EntityDescription;

/**
 * Serialized cache of entity descriptions.
 */
type EntityDescriptionsSerializedCache = Record<string, EntityDescription>;
/**
 * Serialized cache for EntitiesDescriptor class.
 */
type EntitiesDescriptorSerializedCache = {
    /** Serialized descriptions cache */
    descriptions: EntityDescriptionsSerializedCache;
};

/**
 * Class describing entities in a project given their paths and configuration.
 */
declare class EntitiesDescriptor {
    /**
     * Cache to store previously described entities.
     */
    private readonly _descriptionsCache;
    /**
     * Configuration instance for this descriptor.
     */
    private readonly _config;
    private readonly _elementsDescriptor;
    private readonly _filesDescriptor;
    private readonly _modulesDescriptor;
    /**
     * The configuration options for this descriptor.
     * @param elementsDescriptor The elements descriptor instance, used to describe elements when describing entities.
     * @param filesDescriptor The files descriptor instance, used to describe files when describing entities.
     * @param originsDescriptor The origins descriptor instance, used to describe the origin of entities when describing them.
     * @param config The configuration options for this descriptor.
     */
    constructor(elementsDescriptor: ElementsDescriptor, filesDescriptor: FilesDescriptor, modulesDescriptor: ModulesDescriptor, config: DescriptorOptionsNormalized);
    /**
     * Serializes the elements cache to a plain object.
     * @returns The serialized elements cache.
     */
    serializeCache(): EntitiesDescriptorSerializedCache;
    /**
     * Sets the elements cache from a serialized object.
     * @param serializedCache The serialized files cache.
     */
    setCacheFromSerialized(serializedCache: EntitiesDescriptorSerializedCache): void;
    /**
     * Clears the files cache.
     */
    clearCache(): void;
    /**
     * Describes an entity given its file path.
     * @param filePath The absolute path of the file to describe
     * @param source The optional dependency source (e.g., the importer file path) to use for describing the origin of the entity being imported.
     */
    describeEntity(filePath?: string, source?: string): EntityDescription;
}

declare const DEPENDENCY_KIND_TYPE: "type";
declare const DEPENDENCY_KIND_VALUE: "value";
declare const DEPENDENCY_KIND_TYPEOF: "typeof";
/** Map of the kinds of dependency, either a type dependency or a value dependency */
declare const DEPENDENCY_KINDS_MAP: {
    /** Type import, e.g., `import type { X } from 'module'` */
    readonly TYPE: "type";
    /** Value import, e.g., `import { X } from 'module'` */
    readonly VALUE: "value";
    /** typeof import, e.g. `type ModuleType = typeof import("./my_module");` */
    readonly TYPE_OF: "typeof";
};
/** Set of the kinds of dependency for fast lookup */
declare const DEPENDENCY_KINDS_SET: Set<"value" | "type" | "typeof">;
/** Kind of dependency, either a type dependency or a value dependency */
type DependencyKind = (typeof DEPENDENCY_KINDS_MAP)[keyof typeof DEPENDENCY_KINDS_MAP];
/** Map of possible kinds of relationships between elements being dependencies */
declare const DEPENDENCY_RELATIONSHIPS_MAP: {
    /** The dependency is internal to the element */
    readonly INTERNAL: "internal";
    /** The dependency is a child of the element */
    readonly CHILD: "child";
    /** The dependency is a descendant of the element */
    readonly DESCENDANT: "descendant";
    /** The dependency is a sibling of the element (both have the same parent) */
    readonly SIBLING: "sibling";
    /** The dependency is a parent of the element */
    readonly PARENT: "parent";
    /** The dependency is an uncle of the element */
    readonly UNCLE: "uncle";
    /** The dependency is a nephew of the element */
    readonly NEPHEW: "nephew";
    /** The dependency is an ancestor of the element */
    readonly ANCESTOR: "ancestor";
};
/** Set of the kinds of relationships between elements being dependencies for fast lookup */
declare const DEPENDENCY_RELATIONSHIPS_SET: Set<"parent" | "internal" | "child" | "descendant" | "sibling" | "uncle" | "nephew" | "ancestor">;
declare const DEPENDENCY_RELATIONSHIPS_INVERTED_MAP: {
    readonly internal: "internal";
    readonly child: "parent";
    readonly descendant: "ancestor";
    readonly sibling: "sibling";
    readonly parent: "child";
    readonly uncle: "nephew";
    readonly nephew: "uncle";
    readonly ancestor: "descendant";
};
/** Kind of relationship between elements being dependencies */
type DependencyRelationshipType = (typeof DEPENDENCY_RELATIONSHIPS_MAP)[keyof typeof DEPENDENCY_RELATIONSHIPS_MAP];
/**
 * Relationship between two elements being dependencies, from the perspective of both elements.
 */
type DependencyRelationship = {
    from: DependencyRelationshipType | null;
    to: DependencyRelationshipType | null;
};
/** Information about a dependency between two items */
type DependencyInfoDescription = {
    /** Source of the dependency (import/export path) */
    source: string;
    /** Kind of the dependency */
    kind: DependencyKind;
    /** Type of the node creating the dependency in the dependent item */
    nodeKind: string | null;
    /** Specifiers imported or exported in the dependency */
    specifiers: string[] | null;
    /** Relationship between the items from both perspectives */
    relationship: DependencyRelationship;
};
/**
 * Description of a dependency between two items
 */
type DependencyDescription = {
    /** Source entity of the dependency */
    from: EntityDescription;
    /** Target entity of the dependency */
    to: EntityDescription;
    /** Information about the dependency itself */
    dependency: DependencyInfoDescription;
};

/**
 * Serialized cache of dependency descriptor.
 */
type DependencyDescriptorSerializedCache = Record<string, DependencyDescription>;
/** Options for describing a dependency between two items */
type DependencyDescriptorOptions = {
    /** Path of the element where the dependency originates */
    from: string;
    /** Path of the element where the dependency points to */
    to?: string;
    /** Source of the dependency (import/export path) */
    source: string;
    /** Kind of the dependency (type, runtime) */
    kind: DependencyKind;
    /** Type of the node creating the dependency in the dependent element */
    nodeKind?: string;
    /** Specifiers imported or exported in the dependency */
    specifiers?: string[];
};

/**
 * Class describing dependencies between elements.
 */
declare class DependenciesDescriptor {
    /**
     * Cache to store previously described dependencies.
     */
    private readonly _dependenciesCache;
    /**
     * Elements descriptor instance.
     */
    private readonly _entitiesDescriptor;
    /**
     * Configuration options.
     */
    private readonly _config;
    /**
     * Creates a new DependenciesDescriptor instance.
     * @param entitiesDescriptor The entities descriptor instance.
     * @param config The configuration options.
     */
    constructor(entitiesDescriptor: EntitiesDescriptor, config: DescriptorOptionsNormalized);
    /**
     * Serializes the dependencies cache to a plain object.
     * @returns The serialized dependencies cache.
     */
    serializeCache(): DependencyDescriptorSerializedCache;
    /**
     * Sets the dependencies cache from a serialized object.
     * @param serializedCache The serialized dependencies cache.
     */
    setCacheFromSerialized(serializedCache: DependencyDescriptorSerializedCache): void;
    /**
     * Clears the dependencies cache.
     */
    clearCache(): void;
    /**
     * Retrieves the element path of the parent of a given element.
     * @param elementInfo The element whose parent is to be retrieved.
     * @returns The parent element path, or undefined if none exists.
     */
    private _getParent;
    /**
     * Retrieves the common ancestor of two elements.
     * @param elementInfoA The first element.
     * @param elementInfoB The second element.
     * @returns The common ancestor element path, or undefined if none exists.
     */
    private _getCommonAncestor;
    /**
     * Checks if the parent of element A is an ancestor of element B.
     * @param elementA The element A.
     * @param elementB The element B.
     * @returns True if the parent of element A is an ancestor of element B, false otherwise.
     */
    private _isDescendantOfParent;
    /**
     * Checks if two elements are siblings (same parent).
     * @param elementA The first element.
     * @param elementB The second element.
     * @returns True if the elements are siblings, false otherwise.
     */
    private _isSibling;
    /**
     * Checks if one element is a descendant of another.
     * @param elementA The potential descendant element.
     * @param elementB The potential ancestor element.
     * @returns True if elementA is a descendant of elementB, false otherwise.
     */
    private _isDescendant;
    /**
     * Checks if one element is a child of another.
     * @param elementA The potential child element.
     * @param elementB The potential parent element.
     * @returns True if elementA is a child of elementB, false otherwise.
     */
    private _isChild;
    /**
     * Checks if two local elements are internally related (same element).
     * @param elementA The first element.
     * @param elementB The second element.
     * @returns True if the elements are internally related, false otherwise.
     */
    private _isInternal;
    /**
     * Retrieves the relationship between two local known elements in terms of dependency.
     * @param from The element depending on another element.
     * @param to The element being depended on.
     * @returns The relationship between the elements.
     */
    private _dependencyRelationship;
    /**
     * Retrieves the relationships between two elements in terms of dependency, from the perspective of both elements.
     * @param from The element depending on another element.
     * @param to The element being depended on.
     * @returns The relationships between the elements from both perspectives.
     */
    private _dependencyRelationships;
    /**
     * Describes elements in a dependency relationship, and provides additional information about the dependency itself.
     * @param options The options for describing the elements and the dependency details.
     * @returns The description of the dependency between the elements.
     */
    describeDependency({ from, to, source, kind, nodeKind, specifiers, }: DependencyDescriptorOptions): DependencyDescription;
}

/**
 * Determines if the value is a valid dependency kind.
 * @param value The value to check
 * @returns True if the value is a valid dependency kind, false otherwise.
 */
declare function isDependencyKind(value: unknown): value is DependencyKind;
/**
 * Determines whether the given value is a valid DependencyDescription object.
 * @param value The value to check.
 * @returns True if the value is a valid DependencyDescription object, false otherwise.
 */
declare function isDependencyDescription(value: unknown): value is DependencyDescription;
/**
 * Determines whether the given dependency description has an internal relationship.
 * @param dependency The dependency to check
 * @returns True if the dependency has an internal relationship, false otherwise
 */
declare function isDependencyWithInternalRelationship(dependency: DependencyDescription): boolean;

/**
 * Descriptors for elements and files, which can be used to describe the structure of a project.
 */
type DescriptorsConfig = {
    /** Optional element descriptors. If not provided, no abstract layer of elements will be created and only file descriptors will be used to describe the files in the project. */
    elements?: ElementDescriptors;
    /** Optional file descriptors. If not provided, only element descriptors will be used to describe the files in the project. */
    files?: FileDescriptors;
    /** When true, only the first matching descriptor's type is used at each path level. When false (default), an element can match multiple type descriptors at the same path level, accumulating all matched types in the `types` array.
     * @deprecated Use `elementsSingleMatch` instead. Kept as a backward-compatible alias; `elementsSingleMatch` takes precedence when both are set.
     */
    elementsSingleType?: boolean;
    /** Alias of `elementsSingleType`, using vocabulary shared with `filesSingleMatch`. When true, only the first matching descriptor's type is used at each path level. When false (default), an element can match multiple type descriptors at the same path level, accumulating all matched types in the `types` array. Takes precedence over `elementsSingleType` when both are set. */
    elementsSingleMatch?: boolean;
    /** When true, only the first matching file descriptor's category is used; matching stops. When false (default), a file accumulates every category whose descriptor pattern matches it. */
    filesSingleMatch?: boolean;
};
/**
 * Serialized cache for Descriptors class.
 */
type DescriptorsSerializedCache = {
    /** Serialized elements cache */
    elements: ElementsDescriptorSerializedCache;
    /** Serialized files cache */
    files: FilesDescriptorSerializedCache;
    /** Serialized entities cache */
    entities: EntitiesDescriptorSerializedCache;
    /** Serialized dependencies cache */
    dependencies: DependencyDescriptorSerializedCache;
    /** Serialized modules cache */
    modules: ModulesDescriptorSerializedCache;
};

/**
 * Class with methods to describe files, elements, entities, and dependencies between them.
 */
declare class Descriptors {
    private readonly _elementsDescriptor;
    private readonly _filesDescriptor;
    private readonly _dependenciesDescriptor;
    private readonly _entitiesDescriptor;
    private readonly _modulesDescriptor;
    /** Creates a new DescriptorsManager instance
     * @param descriptors The descriptors.
     * @param configOptions The configuration options.
     * @param micromatch The Micromatch instance.
     */
    constructor(descriptors: DescriptorsConfig, config: DescriptorOptionsNormalized, micromatch: Micromatch);
    /**
     * Serializes the elements, files, entities, and dependencies cache to a plain object.
     * @returns The serialized elements, files, entities, and dependencies cache.
     */
    serializeCache(): DescriptorsSerializedCache;
    /**
     * Sets the elements, files, entities, and dependencies cache from a serialized object.
     * @param serializedCache The serialized elements, files, entities, and dependencies cache.
     */
    setCacheFromSerialized(serializedCache: DescriptorsSerializedCache): void;
    /**
     * Clears all caches.
     */
    clearCache(): void;
    /**
     * Describes an element given its file path.
     * @param filePath The path of the file to describe.
     * @returns The description of the element.
     */
    describeElement(filePath?: string): ElementDescription;
    /**
     * Returns the description of a file given its path.
     * @param filePath The path of the file to describe.
     * @returns The description of the file.
     */
    describeFile(filePath: string): FileDescription;
    /**
     * Describes a file given its path. It returns both the file description and the element description.
     * @param filePath The path of the file to describe.
     * @param source The optional dependency source (e.g., the importer file path) to use for describing the origin of the entity being imported.
     * @returns The entity description of the file, including both the file description and the element description.
     */
    describeEntity(filePath?: string, source?: string): EntityDescription;
    /**
     * Describes a module given its path and the path of the importer file.
     * @param filePath The path of the file to describe.
     * @param source The optional dependency source (e.g., the importer file path) to use for describing the origin of the entity being imported.
     * @returns The description of the module.
     */
    describeModule(filePath?: string, source?: string): ModuleDescription;
    /**
     * Describes elements in a dependency relationship, and provides additional information about the dependency itself.
     * @param options The options for describing the elements and the dependency details.
     * @returns The description of the dependency between the elements.
     */
    describeDependency(options: DependencyDescriptorOptions): DependencyDescription;
}

/**
 * Serialized cache for Elements class.
 */
type ElementsSerializedCache = {
    /** Cache for Matcher instances per configuration */
    matchers: Record<string, {
        config: ConfigOptionsNormalized;
        descriptors: DescriptorsConfig;
        cache: MatcherSerializedCache;
    }>;
    micromatch: MicromatchSerializedCache;
};

/**
 * Main class to interact with Elements functionality.
 * It include one method to get descriptors with different caching for different configurations, methods to manage the cache, and methods to match element selectors against element descriptions.
 */
declare class Elements {
    /** The global configuration options for Elements. Can be overridden when getting a descriptor */
    private readonly _globalConfigOptions;
    /** Cache manager for Matcher instances, unique for each different configuration */
    private readonly _matchersCache;
    /** Micromatch instances for pattern matching */
    private readonly _micromatchWithCache;
    private readonly _micromatchWithoutCache;
    /**
     * Creates a new Elements instance
     * @param configOptions The global configuration options for Elements. Can be overridden when getting a descriptor.
     */
    constructor(configOptions?: ConfigOptions);
    /**
     * Returns a serialized representation of the current state of the cache.
     * @returns A serialized representation of the cache.
     */
    serializeCache(): ElementsSerializedCache;
    /**
     * Sets the Elements cache from a serialized representation.
     * @param serializedCache The serialized cache to set.
     */
    setCacheFromSerialized(serializedCache: ElementsSerializedCache): void;
    /**
     * Clears cache
     */
    clearCache(): void;
    /**
     * Gets a Matcher instance for the given configuration options.
     * It uses caching to return the same instance for the same configuration options. If no options are provided, the global configuration options are used.
     * @param descriptors The descriptors to use.
     * @param config Optional configuration options to override the global ones.
     * @returns A matcher instance, unique for each different configuration.
     */
    getMatcher(descriptors: DescriptorsConfig, config?: ConfigOptions): Matcher;
}

export { ARRAY_QUERY_KEYS, type ArrayQuery, type ArrayQueryAtIndex, type ArrayQueryExpandItem, type BackwardCompatibleDependencyInfoSelector, type BackwardCompatibleDependencyInfoSingleSelector, type BackwardCompatibleDependencySelector, type BackwardCompatibleDependencySingleSelector, type BackwardCompatibleElementSelector, type BackwardCompatibleElementSingleSelector, type BackwardCompatibleEntitySelector, type BackwardCompatibleEntitySingleSelector, type BackwardCompatibleParentElementSelector, type BackwardCompatibleParentElementSingleSelector, type BaseDescription, type BaseDescriptor, BaseElementsMatcher, type BaseIgnoredDescription, type BaseKnownDescription, type BaseSingleSelector, type BaseUnknownDescription, type CapturedValues, type CapturedValuesSelector, type CapturedValuesSingleSelector, type ConfigOptions, DEPENDENCY_KINDS_MAP, DEPENDENCY_KINDS_SET, DEPENDENCY_KIND_TYPE, DEPENDENCY_KIND_TYPEOF, DEPENDENCY_KIND_VALUE, DEPENDENCY_RELATIONSHIPS_INVERTED_MAP, DEPENDENCY_RELATIONSHIPS_MAP, DEPENDENCY_RELATIONSHIPS_SET, DependenciesDescriptor, DependenciesMatcher, type DependencyDescription, type DependencyDescriptorOptions, type DependencyDescriptorSerializedCache, type DependencyInfoDescription, type DependencyInfoSelector, type DependencyInfoSelectorNormalized, type DependencyInfoSingleSelector, type DependencyKind, type DependencyMatchResult, type DependencyRelationship, type DependencyRelationshipType, type DependencySelector, type DependencySelectorNormalized, type DependencySingleSelector, type DependencySingleSelectorMatchResult, type DependencySingleSelectorNormalized, type DescriptorPattern, Descriptors, type DescriptorsConfig, type DescriptorsSerializedCache, ELEMENT_DESCRIPTOR_MODES_MAP, type ElementDescription, type ElementDescriptor, type ElementDescriptorMode, type ElementDescriptors, type ElementParent, type ElementSelector, type ElementSelectorNormalized, type ElementSingleSelector, type ElementSingleSelectorNormalized, Elements, ElementsDescriptor, type ElementsDescriptorSerializedCache, ElementsMatcher, type ElementsSerializedCache, EntitiesDescriptor, type EntitiesDescriptorSerializedCache, EntitiesMatcher, type EntityDescription, type EntityDescriptionsSerializedCache, type EntityMatchResult, type EntityMatcherOptions, type EntitySelector, type EntitySelectorNormalized, type EntitySingleSelector, type EntitySingleSelectorMatchResult, type EntitySingleSelectorNormalized, type FileDescription, type FileDescriptionsSerializedCache, type FileDescriptor, type FileDescriptors, type FileSelector, type FileSelectorNormalized, type FileSingleSelector, FilesDescriptor, type FilesDescriptorSerializedCache, FilesMatcher, type FlagAsExternalOptions, type IgnoredElementDescription, type IgnoredFileDescription, type KnownElementDescription, type KnownFileDescription, type LegacyDependencyInfoSelector, type LegacyDependencyInfoSingleSelector, type LegacyDependencySelector, type LegacyDependencySingleSelector, type LegacyElementObjectSelector, type LegacyElementSelector, type LegacyElementSimpleSelector, type LegacyElementSingleObjectSelector, type LegacyElementSingleSelector, type LegacyEntitySelector, type LegacyEntitySingleSelector, type LegacyParentElementSelector, type LegacyParentElementSingleSelector, type LegacySimpleElementSingleSelector, type LegacySimpleElementSingleSelectorByType, type LegacySimpleElementSingleSelectorByTypeWithOptions, Matcher, type MatcherOptions, type MatcherSerializedCache, Micromatch, type MicromatchMatchableValue, type MicromatchPattern, type MicromatchPatternNullable, type MicromatchSerializedCache, type ModuleDescription, type ModuleDescriptionsSerializedCache, type ModuleSelector, type ModuleSelectorNormalized, type ModuleSingleSelector, ModulesDescriptor, type ModulesDescriptorSerializedCache, ModulesMatcher, ORIGINS_MAP, ORIGINS_SET, type Origin, type ParentElementArrayQuery, type ParentElementSelector, type ParentElementSelectorNormalized, type ParentElementSingleSelector, type StringArrayQuery, type StringArrayQueryMatcher, type TemplateData, type UnknownElementDescription, type UnknownFileDescription, expandStringArrayQuery, extendsSingleSelector, isArrayQuery, isBackwardCompatibleDependencyInfoSelector, isBackwardCompatibleDependencyInfoSingleSelector, isBackwardCompatibleDependencySelector, isBackwardCompatibleDependencySingleSelector, isBackwardCompatibleElementSelector, isBackwardCompatibleElementSingleSelector, isBaseDependencySingleSelector, isCapturedValuesSelector, isCapturedValuesSingleSelector, isDependencyDescription, isDependencyInfoSelector, isDependencyInfoSingleSelector, isDependencyKind, isDependencySelector, isDependencySingleSelector, isDependencyWithInternalRelationship, isElementDescription, isElementDescriptor, isElementSelector, isElementSingleSelector, isEntityDescription, isEntitySelector, isEntitySingleSelector, isExpandItem, isFileDescription, isFileDescriptor, isFileSelector, isFileSingleSelector, isIgnoredElementDescription, isIgnoredFileDescription, isKnownElementDescription, isKnownFileDescription, isLegacyDependencyInfoSelector, isLegacyDependencyInfoSingleSelector, isLegacyDependencySelector, isLegacyDependencySingleSelector, isLegacyElementSelector, isLegacyElementSingleObjectSelector, isLegacyElementSingleSelector, isLegacyEntitySelector, isLegacyEntitySingleSelector, isLegacyParentElementSingleSelector, isLegacySimpleElementSelector, isLegacySimpleElementSingleSelector, isLegacySimpleElementSingleSelectorByType, isLegacySimpleElementSingleSelectorByTypeWithOptions, isModuleSelector, isModuleSingleSelector, isOriginDescription, isStringArrayQuery, isUnknownElementDescription, isUnknownFileDescription, normalizeDependencyInfoSelector, normalizeDependencySelector, normalizeElementSelector, normalizeEntitySelector, normalizeFileSelector, normalizeLegacyDependencyInfoSingleSelector, normalizeLegacyDependencySingleSelector, normalizeLegacyElementSingleObjectSelector, normalizeLegacyElementSingleSelector, normalizeLegacyParentElementSelectors, normalizeLegacySimpleElementSingleSelector, normalizeModuleSelector, normalizeModuleSingleSelector, normalizeParentElementSelector, normalizeParentInElementSingleSelector, normalizeSingleDependencyInfoSelector, normalizeSingleDependencySelector, normalizeSingleElementSelector, normalizeSingleEntitySelector, normalizeSingleFileSelector, resolveExpandItem };
