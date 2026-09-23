var __require = /* @__PURE__ */ ((x) => typeof require !== "undefined" ? require : typeof Proxy !== "undefined" ? new Proxy(x, {
  get: (a, b) => (typeof require !== "undefined" ? require : a)[b]
}) : x)(function(x) {
  if (typeof require !== "undefined") return require.apply(this, arguments);
  throw Error('Dynamic require of "' + x + '" is not supported');
});

// src/Shared/Paths.ts
function normalizePath(filePath) {
  return filePath.replaceAll("\\", "/");
}

// src/Shared/TypeGuards.ts
function isString(value) {
  return typeof value === "string";
}
function isUndefined(value) {
  return value === void 0;
}
function isNull(value) {
  return value === null;
}
function isNullish(value) {
  return isUndefined(value) || isNull(value);
}
function isBoolean(value) {
  return typeof value === "boolean";
}
function isObject(value) {
  return !isNullish(value) && !isBoolean(value) && !isArray(value) && typeof value === "object";
}
function isEmptyObject(obj) {
  return isObject(obj) && Object.keys(obj).length === 0;
}
function isArray(value) {
  return Array.isArray(value);
}
function isEmptyArray(arr) {
  return arr.length === 0;
}
function isStringArray(value) {
  return isArray(value) && value.every(isString);
}
function isObjectWithProperty(value, key) {
  return isObject(value) && Object.hasOwn(value, key);
}
function isObjectWithAnyOfProperties(value, keys) {
  return isObject(value) && keys.some((key) => key in value);
}

// src/Config/Config.ts
var Config = class {
  /** The ignore paths */
  _ignorePaths;
  /** The include paths */
  _includePaths;
  /** Whether legacy template support is enabled */
  _legacyTemplates;
  /** Whether the cache is enabled */
  _cache;
  /** Configuration for categorizing dependencies as external or local */
  _flagAsExternal;
  /** Root path of the project */
  _rootPath;
  /**
   * Creates a new Config instance
   * @param options Configuration options
   */
  constructor(options) {
    this._ignorePaths = options?.ignorePaths;
    this._includePaths = options?.includePaths;
    this._legacyTemplates = options?.legacyTemplates ?? true;
    this._cache = options?.cache ?? true;
    const customSourcePatterns = options?.flagAsExternal?.customSourcePatterns;
    let normalizedCustomSourcePatterns;
    if (isString(customSourcePatterns)) {
      normalizedCustomSourcePatterns = [customSourcePatterns];
    } else if (isArray(customSourcePatterns)) {
      normalizedCustomSourcePatterns = customSourcePatterns;
    } else {
      normalizedCustomSourcePatterns = [];
    }
    this._flagAsExternal = {
      unresolvableAlias: options?.flagAsExternal?.unresolvableAlias ?? true,
      inNodeModules: options?.flagAsExternal?.inNodeModules ?? true,
      outsideRootPath: options?.flagAsExternal?.outsideRootPath ?? false,
      customSourcePatterns: normalizedCustomSourcePatterns
    };
    if (options?.rootPath) {
      const normalizedRoot = normalizePath(options.rootPath);
      this._rootPath = normalizedRoot.endsWith("/") ? normalizedRoot : `${normalizedRoot}/`;
    } else {
      this._rootPath = void 0;
    }
  }
  /**
   * The normalized configuration options
   */
  get options() {
    return {
      ignorePaths: this._ignorePaths,
      includePaths: this._includePaths,
      legacyTemplates: this._legacyTemplates,
      cache: this._cache,
      flagAsExternal: this._flagAsExternal,
      rootPath: this._rootPath
    };
  }
  /**
   * Normalized options for descriptors
   */
  get descriptorOptions() {
    return {
      ignorePaths: this._ignorePaths,
      includePaths: this._includePaths,
      cache: this._cache,
      flagAsExternal: this._flagAsExternal,
      rootPath: this._rootPath
    };
  }
  /**
   * Normalized options for element matchers
   */
  get matchersOptions() {
    return {
      legacyTemplates: this._legacyTemplates
    };
  }
  /**
   * Whether caching is enabled
   */
  get cache() {
    return this._cache;
  }
};

// src/Matcher/Shared/ArrayQuerySelectorHelpers.ts
var ARRAY_QUERY_KEYS = [
  "anyOf",
  "allOf",
  "noneOf",
  "equalsTo",
  "atIndex",
  "hasLength"
];
function isArrayQuery(value) {
  return isObjectWithAnyOfProperties(value, [...ARRAY_QUERY_KEYS]);
}
function isStringArrayQuery(value) {
  return isArrayQuery(value);
}
function isExpandItem(value) {
  return isObjectWithProperty(value, "expand") && isString(value.expand);
}
var SINGLE_TEMPLATE_REGEX = /^\s*\{\{([^{}]+)\}\}\s*$/;
function resolvePath(path, data) {
  const segments = path.replace(/\[(\d+)\]/g, ".$1").split(".").map((s) => s.trim()).filter(Boolean);
  let current = data;
  for (const segment of segments) {
    if (!isObject(current) && !isArray(current)) return void 0;
    current = current[segment];
  }
  return current;
}
function resolveExpandItem(item, templateData) {
  const match = SINGLE_TEMPLATE_REGEX.exec(item.expand);
  if (!match) return [];
  const value = resolvePath(match[1].trim(), templateData);
  if (isArray(value)) {
    return value.filter(
      (v) => !isNullish(v) && !isObject(v)
    ).map(String);
  }
  if (isString(value) || typeof value === "number" || typeof value === "boolean") {
    return [String(value)];
  }
  return [];
}
function expandMatchers(matchers, templateData) {
  return matchers.flatMap(
    (m) => isExpandItem(m) ? resolveExpandItem(m, templateData) : [m]
  );
}
function expandStringArrayQuery(query, templateData) {
  const expanded = { ...query };
  if (query.anyOf) expanded.anyOf = expandMatchers(query.anyOf, templateData);
  if (query.allOf) expanded.allOf = expandMatchers(query.allOf, templateData);
  if (query.noneOf)
    expanded.noneOf = expandMatchers(query.noneOf, templateData);
  if (query.equalsTo)
    expanded.equalsTo = expandMatchers(query.equalsTo, templateData);
  return expanded;
}

// src/Matcher/Shared/BaseMatcher.ts
import Handlebars from "handlebars";
var LEGACY_TEMPLATE_REGEX = /\$\{([^}]+)\}/g;
var HANDLEBARS_TEMPLATE_REGEX = /{{\s*[^{}\s][^{}]*}}/;
var BaseElementsMatcher = class {
  /**
   * Option to use legacy templates with ${} syntax.
   */
  _legacyTemplates;
  /**
   * Micromatch instance for matching.
   */
  micromatch;
  /**
   * Creates a new BaseElementsMatcher.
   * @param config Configuration options for the matcher.
   * @param globalCache Global cache instance.
   */
  constructor(config, micromatch2) {
    this.micromatch = micromatch2;
    this._legacyTemplates = config.legacyTemplates;
  }
  /**
   * Converts a template with ${} to Handlebars {{}} templates for backwards compatibility.
   * @param template The template to convert.
   * @returns The converted template.
   */
  _getBackwardsCompatibleTemplate(template) {
    if (!template) {
      return template;
    }
    return template.replaceAll(LEGACY_TEMPLATE_REGEX, "{{ $1 }}");
  }
  /**
   * Determines if a template contains Handlebars syntax.
   * @param template The template to check.
   * @returns True if the template contains Handlebars syntax, false otherwise.
   */
  _isHandlebarsTemplate(template) {
    if (!template) {
      return false;
    }
    return HANDLEBARS_TEMPLATE_REGEX.test(template);
  }
  /**
   * Returns a rendered template using the provided template data.
   * Optimized version with template caching for better performance.
   * @param template The template to render.
   * @param templateData The data to use for replace in the template.
   * @returns The rendered template.
   */
  _getRenderedTemplate(template, templateData) {
    const templateToUse = this._legacyTemplates ? this._getBackwardsCompatibleTemplate(template) : template;
    if (!this._isHandlebarsTemplate(templateToUse)) {
      return template;
    }
    const compiledTemplate = Handlebars.compile(templateToUse);
    return compiledTemplate(templateData);
  }
  /**
   * Returns rendered templates using the provided template data.
   * @param template The templates to render.
   * @param extraTemplateData The data to use for replace in the templates.
   * @returns The rendered templates.
   */
  getRenderedTemplates(template, templateData) {
    if (isArray(template)) {
      return template.map((temp) => {
        return this._getRenderedTemplate(temp, templateData);
      });
    }
    return this._getRenderedTemplate(template, templateData);
  }
  /**
   * Cleans a micromatch pattern by removing falsy values from arrays.
   * @param pattern The micromatch pattern(s) to clean.
   * @returns The cleaned pattern. If an array is provided, falsy entries are removed and the resulting array may be empty. If null is provided, null is returned unchanged.
   */
  cleanMicromatchPattern(pattern) {
    return isArray(pattern) ? pattern.filter(Boolean) : pattern;
  }
  /**
   * Returns whether the given value matches the micromatch pattern, converting non-string values to strings.
   * Optimized version with caching for better performance.
   * @param value The value to check.
   * @param pattern The micromatch pattern to match against.
   * @returns Whether the value matches the pattern.
   */
  isMicromatchMatch(value, pattern) {
    if (isNull(pattern)) {
      return isNull(value);
    }
    if (isNull(value)) {
      return isArray(pattern) && pattern.some(isNull);
    }
    const patternToCheck = this.cleanMicromatchPattern(pattern);
    if (!patternToCheck?.length) {
      return false;
    }
    const elementValueToCheck = !value || !isString(value) ? String(value) : value;
    return this.micromatch.isMatch(elementValueToCheck, patternToCheck);
  }
  /**
   * Returns whether the given value matches the micromatch pattern after rendering it as a template.
   * @param pattern The micromatch pattern to render and match against.
   * @param templateData The data to use for rendering the pattern as a template.
   * @param value The value to check.
   * @returns Whether the value matches the rendered pattern.
   */
  isTemplateMicromatchMatch(pattern, templateData, value) {
    if (isUndefined(value)) {
      return false;
    }
    const patternRendered = this.getRenderedTemplates(pattern, templateData);
    if (!isNull(patternRendered) && !patternRendered) {
      return false;
    }
    if (isArray(value)) {
      return value.some((val) => this.isMicromatchMatch(val, patternRendered));
    }
    return this.isMicromatchMatch(value, patternRendered);
  }
  /**
   * Whether the given element key matches the selector key as booleans.
   * @param param0 The parameters object.
   * @returns Whether the object key matches the selector key.
   */
  isObjectKeyBooleanMatch({
    /** The object to check. */
    object,
    /** The selector to check against. */
    selector,
    /** The key of the object to check. */
    objectKey,
    /** The key of the selector to check against. */
    selectorKey
  }) {
    if (!(selectorKey in selector) || isUndefined(selector[selectorKey])) {
      return true;
    }
    if (!(objectKey in object)) {
      return false;
    }
    if (!isBoolean(selector[selectorKey]) || !isBoolean(object[objectKey])) {
      return false;
    }
    return selector[selectorKey] === object[objectKey];
  }
  /**
   * Generic array-query matcher. All present operators are AND-combined.
   * @param array The target array from the description (may be null).
   * @param query The array query object.
   * @param matchElement Predicate matching one array element against one matcher.
   * @returns Whether the array satisfies the query.
   */
  isArrayQueryMatch(array, query, matchElement) {
    if (isNull(array)) {
      return false;
    }
    if (!isUndefined(query.hasLength) && array.length !== query.hasLength) {
      return false;
    }
    if (this._arrayQueryEqualsToFails(array, query, matchElement)) {
      return false;
    }
    if (this._arrayQueryAtIndexFails(array, query, matchElement)) {
      return false;
    }
    if (!isUndefined(query.anyOf) && !array.some(
      (element) => query.anyOf.some((matcher) => matchElement(element, matcher))
    )) {
      return false;
    }
    if (!isUndefined(query.allOf) && !query.allOf.every(
      (matcher) => array.some((element) => matchElement(element, matcher))
    )) {
      return false;
    }
    if (!isUndefined(query.noneOf) && query.noneOf.some(
      (matcher) => array.some((element) => matchElement(element, matcher))
    )) {
      return false;
    }
    return true;
  }
  /**
   * Whether the array-query `equalsTo` operator, if present, fails to match the array.
   * @param array The target array from the description.
   * @param query The array query object.
   * @param matchElement Predicate matching one array element against one matcher.
   * @returns Whether the `equalsTo` operator is present and not satisfied by the array.
   */
  _arrayQueryEqualsToFails(array, query, matchElement) {
    if (isUndefined(query.equalsTo)) {
      return false;
    }
    if (array.length !== query.equalsTo.length) {
      return true;
    }
    return !query.equalsTo.every(
      (matcher, index) => matchElement(array[index], matcher)
    );
  }
  /**
   * Whether the array-query `atIndex` operator, if present, fails to match the array.
   * @param array The target array from the description.
   * @param query The array query object.
   * @param matchElement Predicate matching one array element against one matcher.
   * @returns Whether the `atIndex` operator is present and not satisfied by the array.
   */
  _arrayQueryAtIndexFails(array, query, matchElement) {
    if (isUndefined(query.atIndex)) {
      return false;
    }
    const { index, matches } = query.atIndex;
    const resolvedIndex = index < 0 ? array.length + index : index;
    if (resolvedIndex < 0 || resolvedIndex >= array.length) {
      return true;
    }
    const matcherList = isArray(matches) ? matches : [matches];
    return !matcherList.some((m) => matchElement(array[resolvedIndex], m));
  }
  /**
   * String array query matcher with `expand` item support.
   * Expands `{ expand }` operand items against the template data, then evaluates
   * with the standard template-micromatch element matcher.
   */
  isStringArrayQueryMatch(array, query, templateData) {
    const expanded = expandStringArrayQuery(query, templateData);
    return this.isArrayQueryMatch(
      array,
      expanded,
      (value, pattern) => this.isTemplateMicromatchMatch(pattern, templateData, value)
    );
  }
  /**
   * Whether the given object key matches the selector key using micromatch.
   * @param param0 The parameters object.
   * @returns Whether the object key matches the selector key.
   */
  isObjectKeyMicromatchMatch({
    object,
    selector,
    objectKey,
    selectorKey,
    selectorValue,
    templateData
  }) {
    if (!(selectorKey in selector) || isUndefined(selectorValue)) {
      return true;
    }
    if (!isObjectWithProperty(object, String(objectKey))) {
      return false;
    }
    const objectValue = object[objectKey];
    return this.isTemplateMicromatchMatch(
      selectorValue,
      templateData,
      objectValue
    );
  }
};

// src/Matcher/Shared/BaseSelectorHelpers.ts
function isCapturedValuesSingleSelector(value) {
  if (!isObject(value)) {
    return false;
  }
  return Object.values(value).every(
    (pattern) => isString(pattern) || isStringArray(pattern)
  );
}
function isCapturedValuesSelector(value) {
  if (isArray(value)) {
    return value.every((item) => isCapturedValuesSingleSelector(item));
  }
  return isCapturedValuesSingleSelector(value);
}
function extendsSingleSelector(value) {
  return isObjectWithAnyOfProperties(value, [
    "path",
    "captured",
    "isIgnored",
    "isUnknown"
  ]);
}

// src/Matcher/Shared/Micromatch.ts
import micromatch from "micromatch";

// src/Cache/Cache.ts
var CacheManager = class {
  /**
   * Internal cache map
   */
  _cache;
  /**
   * Creates a new CacheManager instance
   */
  constructor() {
    this._cache = /* @__PURE__ */ new Map();
  }
  /**
   * Generates a string key from the given cache key. Has to be implemented for non-string keys.
   * @param key The cache key to generate from
   * @returns The generated string key
   */
  generateKey(key) {
    if (isString(key)) {
      return key;
    }
    const errorMessage = "Cache key generation for non-string keys is not implemented because it causes performance issues: " + JSON.stringify(key);
    throw new Error(errorMessage);
  }
  /**
   * Generates a hashed key for the given cache key
   * @param key The cache key to hash
   * @returns The hashed key as a string
   */
  getKey(key) {
    return this.generateKey(key);
  }
  /**
   * Retrieves a value from the cache based on the given hashed key
   * @param hashedKey The hashed key to retrieve
   * @returns The cached value or undefined if not found
   */
  get(hashedKey) {
    return this._cache.get(hashedKey);
  }
  /**
   * Stores a value in the cache with a given hashed key
   * @param hashedKey The hashed key to store
   * @param value The value to cache
   */
  set(hashedKey, value) {
    this._cache.set(hashedKey, value);
  }
  /**
   * Checks if a value exists in the cache based on the given hashed key
   * @param hashedKey The hashed key to check
   * @returns True if the value exists, false otherwise
   */
  has(hashedKey) {
    return this._cache.has(hashedKey);
  }
  /**
   * Retrieves all cached values
   * @returns A map of all cached values
   */
  getAll() {
    return this._cache;
  }
  /**
   * Clears the entire cache
   */
  clear() {
    this._cache.clear();
  }
  /**
   * Serializes the  cache to a plain object.
   * @returns The serialized cache.
   */
  serialize() {
    return Array.from(this.getAll().entries()).reduce(
      (acc, [key, value]) => {
        acc[key] = value;
        return acc;
      },
      {}
    );
  }
  /**
   * Sets the cache from a serialized object.
   * @param serializedCache The serialized cache.
   */
  setFromSerialized(serializedCache) {
    for (const key in serializedCache) {
      this.set(key, serializedCache[key]);
    }
  }
};

// src/Cache/CacheDisabled.ts
var CacheManagerDisabled = class extends CacheManager {
  /**
   * Generates a fake cache key as caching is disabled
   * @param key The cache key to hash
   * @returns An empty string
   */
  getKey(_key) {
    return "";
  }
  /**
   * Does nothing as caching is disabled
   * @param hashedKey The hashed key to retrieve
   * @returns Undefined as caching is disabled
   */
  get(_hashedKey) {
    return void 0;
  }
  /**
   * Does nothing as caching is disabled
   * @param hashedKey The hashed key to store
   * @param value The value to cache
   */
  set(_hashedKey, _value) {
    return;
  }
  /**
   * Does nothing as caching is disabled
   * @param hashedKey The hashed key to check
   * @returns False as caching is disabled
   */
  has(_hashedKey) {
    return false;
  }
};

// src/Matcher/Shared/Micromatch.ts
var MatchingResultsCache = class extends CacheManager {
  /**
   * Generates a unique cache key based on the value and pattern
   * @param param0 The cache key components
   * @returns The generated cache key
   */
  generateKey({ value, pattern }) {
    return `${value}::${isArray(pattern) ? pattern.join("|") : pattern}`;
  }
};
var CapturedValueCache = class extends CacheManager {
  /**
   * Generates a unique cache key based on the pattern and target
   * @param param0 The cache key components
   * @returns The generated cache key
   */
  generateKey({ pattern, target }) {
    return `${pattern}|${target}`;
  }
};
var Micromatch = class {
  /**
   * Cache for micromatch matching results
   */
  _matchingResultsCache;
  /**
   * Cache for micromatch captures
   */
  _capturesCache = new CacheManagerDisabled();
  /**
   * Cache for micromatch makeRe results
   */
  _makeReCache = new CacheManagerDisabled();
  /**
   * Creates an instance of Micromatch class.
   * @param cache Whether to use caching or not.
   */
  constructor(cache) {
    this._matchingResultsCache = cache ? new MatchingResultsCache() : new CacheManagerDisabled();
    this._capturesCache = cache ? new CapturedValueCache() : new CacheManagerDisabled();
    this._makeReCache = cache ? new CacheManager() : new CacheManagerDisabled();
  }
  /**
   * Clears all caches.
   */
  clearCache() {
    this._matchingResultsCache.clear();
    this._capturesCache.clear();
    this._makeReCache.clear();
  }
  /**
   * Serializes the current cache state.
   * @returns The serialized cache data.
   */
  serializeCache() {
    return {
      matchingResults: this._matchingResultsCache.serialize(),
      captures: this._capturesCache.serialize()
    };
  }
  /**
   * Restores the cache state from serialized data.
   * @param serializedCache The serialized cache data.
   */
  setFromSerialized(serializedCache) {
    this._matchingResultsCache.setFromSerialized(
      serializedCache.matchingResults
    );
    this._capturesCache.setFromSerialized(serializedCache.captures);
  }
  /**
   * Optimized micromatch match with caching.
   * @param value The value to match.
   * @param pattern The pattern to match against.
   * @returns True if the value matches the pattern, false otherwise.
   */
  isMatch(value, pattern) {
    const cacheKey = this._matchingResultsCache.getKey({
      value,
      pattern
    });
    if (this._matchingResultsCache.has(cacheKey)) {
      return this._matchingResultsCache.get(cacheKey);
    }
    const isMatch = micromatch.isMatch(value, pattern);
    this._matchingResultsCache.set(cacheKey, isMatch);
    return isMatch;
  }
  /**
   * Optimized micromatch capture with caching.
   * @param pattern The pattern to match against.
   * @param target The target string to test.
   * @returns Captured groups or null if no match.
   */
  capture(pattern, target) {
    const cacheKey = this._capturesCache.getKey({ pattern, target });
    if (this._capturesCache.has(cacheKey)) {
      return this._capturesCache.get(cacheKey);
    }
    const result = micromatch.capture(pattern, target);
    this._capturesCache.set(cacheKey, result);
    return result;
  }
  /**
   * Optimized micromatch makeRe with caching.
   * @param pattern The pattern to convert to RegExp.
   * @returns The RegExp instance.
   */
  makeRe(pattern) {
    if (this._makeReCache.has(pattern)) {
      return this._makeReCache.get(pattern);
    }
    const regexp = micromatch.makeRe(pattern);
    this._makeReCache.set(pattern, regexp);
    return regexp;
  }
};

// src/Descriptor/Dependency/DependencyDescription.types.ts
var DEPENDENCY_KIND_TYPE = "type";
var DEPENDENCY_KIND_VALUE = "value";
var DEPENDENCY_KIND_TYPEOF = "typeof";
var DEPENDENCY_KINDS_MAP = {
  /** Type import, e.g., `import type { X } from 'module'` */
  TYPE: DEPENDENCY_KIND_TYPE,
  /** Value import, e.g., `import { X } from 'module'` */
  VALUE: DEPENDENCY_KIND_VALUE,
  /** typeof import, e.g. `type ModuleType = typeof import("./my_module");` */
  TYPE_OF: DEPENDENCY_KIND_TYPEOF
};
var DEPENDENCY_KINDS_SET = new Set(
  Object.values(DEPENDENCY_KINDS_MAP)
);
var DEPENDENCY_RELATIONSHIPS_MAP = {
  /** The dependency is internal to the element */
  INTERNAL: "internal",
  /** The dependency is a child of the element */
  CHILD: "child",
  /** The dependency is a descendant of the element */
  DESCENDANT: "descendant",
  /** The dependency is a sibling of the element (both have the same parent) */
  SIBLING: "sibling",
  /** The dependency is a parent of the element */
  PARENT: "parent",
  /** The dependency is an uncle of the element */
  UNCLE: "uncle",
  /** The dependency is a nephew of the element */
  NEPHEW: "nephew",
  /** The dependency is an ancestor of the element */
  ANCESTOR: "ancestor"
};
var DEPENDENCY_RELATIONSHIPS_SET = new Set(
  Object.values(DEPENDENCY_RELATIONSHIPS_MAP)
);
var DEPENDENCY_RELATIONSHIPS_INVERTED_MAP = {
  [DEPENDENCY_RELATIONSHIPS_MAP.INTERNAL]: DEPENDENCY_RELATIONSHIPS_MAP.INTERNAL,
  [DEPENDENCY_RELATIONSHIPS_MAP.CHILD]: DEPENDENCY_RELATIONSHIPS_MAP.PARENT,
  [DEPENDENCY_RELATIONSHIPS_MAP.DESCENDANT]: DEPENDENCY_RELATIONSHIPS_MAP.ANCESTOR,
  [DEPENDENCY_RELATIONSHIPS_MAP.SIBLING]: DEPENDENCY_RELATIONSHIPS_MAP.SIBLING,
  [DEPENDENCY_RELATIONSHIPS_MAP.PARENT]: DEPENDENCY_RELATIONSHIPS_MAP.CHILD,
  [DEPENDENCY_RELATIONSHIPS_MAP.UNCLE]: DEPENDENCY_RELATIONSHIPS_MAP.NEPHEW,
  [DEPENDENCY_RELATIONSHIPS_MAP.NEPHEW]: DEPENDENCY_RELATIONSHIPS_MAP.UNCLE,
  [DEPENDENCY_RELATIONSHIPS_MAP.ANCESTOR]: DEPENDENCY_RELATIONSHIPS_MAP.DESCENDANT
};

// src/Descriptor/Shared/BaseDescriptionHelpers.ts
function isBaseDescription(value) {
  return isObjectWithProperty(value, "path") && isObjectWithProperty(value, "captured") && isObjectWithProperty(value, "isIgnored") && isObjectWithProperty(value, "isUnknown");
}
function isIgnoredDescription(description) {
  return description.isIgnored === true;
}
function isKnownDescription(description) {
  return !isIgnoredDescription(description) && !isUnknownDescription(description);
}
function isUnknownDescription(description) {
  return description.isUnknown === true;
}

// src/Descriptor/Shared/BaseDescriptorHelpers.ts
function isBaseDescriptorPattern(value) {
  return isString(value) || isArray(value) && !isEmptyArray(value) && value.every(isString);
}
function isBaseDescriptor(value) {
  return isObjectWithProperty(value, "pattern") && isBaseDescriptorPattern(value.pattern);
}

// src/Descriptor/Shared/PathHelper.ts
var PathHelper = class {
  _config;
  _micromatch;
  constructor(config, micromatch2) {
    this._config = config;
    this._micromatch = micromatch2;
  }
  /**
   * Determines if a file path is outside the configured root path.
   * Returns false when rootPath is not configured.
   */
  isOutsideRootPath(filePath) {
    if (!this._config.rootPath) {
      return false;
    }
    return !filePath.startsWith(this._config.rootPath);
  }
  /**
   * Converts an absolute file path to a relative path when rootPath is configured.
   * Returns the path unchanged when rootPath is absent or the path is outside it.
   */
  toRelativePath(filePath) {
    if (!this._config.rootPath || this.isOutsideRootPath(filePath)) {
      return filePath;
    }
    return filePath.replace(this._config.rootPath, "");
  }
  /**
   * Determines if a given path is included based on includePaths / ignorePaths config.
   * Returns true when neither option is set.
   */
  pathIsIncluded(elementPath) {
    let result;
    if (this._config.includePaths && this._config.ignorePaths) {
      const isIncluded = this._micromatch.isMatch(
        elementPath,
        this._config.includePaths
      );
      const isIgnored = this._micromatch.isMatch(
        elementPath,
        this._config.ignorePaths
      );
      result = isIncluded && !isIgnored;
    } else if (this._config.includePaths) {
      result = this._micromatch.isMatch(elementPath, this._config.includePaths);
    } else if (this._config.ignorePaths) {
      result = !this._micromatch.isMatch(elementPath, this._config.ignorePaths);
    } else {
      result = true;
    }
    return result;
  }
  /**
   * Maps captured glob groups to named keys defined in captureConfig.
   * Returns null when captureConfig is not provided.
   */
  getCapturedValues(captured, captureConfig) {
    if (!captureConfig) {
      return null;
    }
    return captured.reduce((capturedValues, captureValue, index) => {
      if (captureConfig[index]) {
        capturedValues[captureConfig[index]] = captureValue;
      }
      return capturedValues;
    }, {});
  }
};

// src/Descriptor/Element/ElementDescriptionHelpers.ts
function isElementDescription(value) {
  return isBaseDescription(value) && isObjectWithProperty(value, "types") && isObjectWithProperty(value, "parents");
}
function isUnknownElementDescription(value) {
  return isElementDescription(value) && isUnknownDescription(value);
}
function isKnownElementDescription(value) {
  return isElementDescription(value) && isKnownDescription(value);
}
function isIgnoredElementDescription(value) {
  return isElementDescription(value) && isIgnoredDescription(value);
}

// src/Descriptor/Element/ElementDescriptor.types.ts
var ELEMENT_DESCRIPTOR_MODES_MAP = {
  /** Mode to interpret the pattern as a folder */
  FOLDER: "folder",
  /** Mode to interpret the pattern as a file */
  FILE: "file",
  /** Mode to interpret the pattern as a full path */
  FULL: "full"
};

// src/Descriptor/Element/ElementDescriptorHelpers.ts
function isElementDescriptor(value) {
  return isBaseDescriptor(value) && isObjectWithAnyOfProperties(value, ["type", "category"]);
}

// src/Descriptor/Element/ElementDescriptor.ts
var UNKNOWN_ELEMENT = {
  path: null,
  fileInternalPath: null,
  filePath: null,
  parents: [],
  types: null,
  category: null,
  captured: null,
  isIgnored: false,
  isUnknown: true
};
var ElementsDescriptor = class {
  /**
   * Cache to store previously described elements.
   */
  _descriptionsCache;
  /**
   * Cache storing the folder-stable base description for each folder.
   * Multiple files in the same folder share the same base (path, types, category,
   * captured, parents), so it is computed once per folder and extended per file with
   * the file-specific fields (fileInternalPath, isIgnored).
   */
  _folderDescriptionsCache;
  /**
   * Whether the folder-level cache can be used. It is only sound when no descriptor
   * relies on the file name to match, i.e. no descriptor uses the deprecated "file" or
   * "full" modes. In those modes a sibling file could match a different descriptor, so
   * the description is not folder-deterministic and the per-file path must be used.
   */
  _canCacheByFolder;
  /**
   * Configuration instance for this descriptor.
   */
  _config;
  /**
   * Element descriptors used by this descriptor.
   */
  _elementDescriptors;
  /** Micromatch instance for path matching */
  _micromatch;
  /** Whether single-type matching is enabled (only first matching type is kept) */
  _singleType;
  /** Shared path helper providing root-path and include/ignore utilities */
  _pathHelper;
  /**
   * The configuration options for this descriptor.
   * @param elementDescriptors The element descriptors.
   * @param configOptions The configuration options.
   * @param globalCache The global cache for various caching needs.
   * @param micromatch The micromatch instance for path matching.
   * @param singleType Whether single-type matching is enabled.
   */
  constructor(elementDescriptors, configOptions, micromatch2, singleType = false) {
    this._micromatch = micromatch2;
    this._singleType = singleType;
    this._elementDescriptors = elementDescriptors;
    this._validateDescriptors(elementDescriptors);
    this._config = configOptions;
    this._pathHelper = new PathHelper(configOptions, micromatch2);
    this._descriptionsCache = this._config.cache ? new CacheManager() : new CacheManagerDisabled();
    this._canCacheByFolder = this._config.cache && !elementDescriptors.some(
      (descriptor) => descriptor.mode === ELEMENT_DESCRIPTOR_MODES_MAP.FILE || descriptor.mode === ELEMENT_DESCRIPTOR_MODES_MAP.FULL
    );
    this._folderDescriptionsCache = this._canCacheByFolder ? new CacheManager() : new CacheManagerDisabled();
  }
  /**
   * Serializes the elements cache to a plain object.
   * @returns The serialized elements cache.
   */
  serializeCache() {
    return this._descriptionsCache.serialize();
  }
  /**
   * Sets the elements cache from a serialized object.
   * @param serializedCache The serialized elements cache.
   */
  setCacheFromSerialized(serializedCache) {
    this._descriptionsCache.setFromSerialized(serializedCache);
  }
  /**
   * Clears the elements cache.
   */
  clearCache() {
    this._descriptionsCache.clear();
    this._folderDescriptionsCache.clear();
  }
  /**
   * Validates the element descriptors to ensure they are correctly defined.
   */
  _validateDescriptors(elementDescriptors) {
    let index = 0;
    for (const descriptor of elementDescriptors) {
      if (!isElementDescriptor(descriptor)) {
        throw new Error(
          `Element descriptor at index ${index} must have a pattern, and either a 'type' or 'category' defined.`
        );
      }
      index++;
    }
  }
  /**
   * Gets the element path based on the path pattern, path segments to the element, and all path segments from the file path.
   * @param pathPattern The element path pattern.
   * @param pathSegments The path segments leading to the element.
   * @param allPathSegments The full path segments from the file path.
   * @returns The element path.
   */
  _getElementPath(pathPattern, pathSegments, allPathSegments) {
    const elementPathRegexp = this._micromatch.makeRe(pathPattern);
    const testedSegments = [];
    let result;
    for (const pathSegment of pathSegments) {
      testedSegments.push(pathSegment);
      const joinedSegments = testedSegments.join("/");
      if (elementPathRegexp.test(joinedSegments)) {
        result = joinedSegments;
        break;
      }
    }
    return `${[...allPathSegments].reverse().join("/").split(result)[0]}${result}`;
  }
  /**
   * Gets the element folder path for a `partialMatch: false` descriptor.
   * Walks `filePath` from the project root and returns the first prefix that satisfies
   * `basePattern`. This gives the folder path rather than the full file path.
   * @param basePattern The raw element pattern WITHOUT the `/**\/*` suffix.
   * @param filePath The full file path relative to rootPath.
   * @returns The folder path prefix that the pattern matches.
   */
  _getFullFolderMatchElementPath(basePattern, filePath) {
    const elementPathRegexp = this._micromatch.makeRe(basePattern);
    const segments = filePath.split("/");
    const accumulated = [];
    for (const segment of segments) {
      accumulated.push(segment);
      if (elementPathRegexp.test(accumulated.join("/"))) {
        return accumulated.join("/");
      }
    }
    return filePath;
  }
  /**
   * Determines if an element descriptor matches the given parameters in the provided path.
   * @param options The options for matching the descriptor.
   * @param options.elementDescriptor The element descriptor to match.
   * @param options.filePath The file path to match against the descriptor.
   * @param options.currentPathSegments The current path segments leading to the element.
   * @param options.lastPathSegmentMatching The last path segment that was matched.
   * @param options.alreadyMatched Whether the element matched previously.
   * @returns The result of the match, including whether it matched.
   */
  _fileDescriptorMatch({
    elementDescriptor,
    filePath,
    currentPathSegments,
    lastPathSegmentMatching,
    alreadyMatched
  }) {
    const isFolderMode = elementDescriptor.partialMatch === false || !elementDescriptor.mode || elementDescriptor.mode === ELEMENT_DESCRIPTOR_MODES_MAP.FOLDER;
    const patterns = isArray(elementDescriptor.pattern) ? elementDescriptor.pattern : [elementDescriptor.pattern];
    for (const pattern of patterns) {
      const useFullPathMatch = elementDescriptor.mode === ELEMENT_DESCRIPTOR_MODES_MAP.FULL && elementDescriptor.partialMatch !== false && !alreadyMatched;
      const effectivePattern = isFolderMode && !alreadyMatched ? `${pattern}/**/*` : pattern;
      const targetPath = useFullPathMatch || elementDescriptor.partialMatch === false && !alreadyMatched ? filePath : currentPathSegments.join("/");
      let baseCapture = null;
      let hasCapture = true;
      if (elementDescriptor.basePattern) {
        const baseTarget = filePath.split("/").slice(0, filePath.split("/").length - lastPathSegmentMatching).join("/");
        baseCapture = this._micromatch.capture(
          [elementDescriptor.basePattern, "**", effectivePattern].join("/"),
          baseTarget
        );
        hasCapture = baseCapture !== null;
      }
      const capture = this._micromatch.capture(effectivePattern, targetPath);
      if (capture && hasCapture) {
        return {
          matched: true,
          capture,
          baseCapture,
          useFullPathMatch,
          patternUsed: pattern
        };
      }
    }
    return { matched: false };
  }
  /**
   * Describes an element given its file path
   * @param elementPath The path of the element to describe.
   * @returns The description of the element.
   */
  _describeElement(filePath) {
    if (!filePath) {
      return {
        ...UNKNOWN_ELEMENT
      };
    }
    if (!this._pathHelper.pathIsIncluded(filePath)) {
      return {
        ...UNKNOWN_ELEMENT,
        filePath,
        path: filePath,
        isIgnored: true
      };
    }
    const parents = [];
    const elementResult = {
      filePath,
      // For backward compatibility with legacy mode "file", where filePath was used to store the path of the element. --- IGNORE ---
      path: filePath,
      fileInternalPath: null,
      types: null,
      category: null,
      captured: null,
      isIgnored: false,
      isUnknown: true,
      parents
    };
    const state = {
      pathSegmentsAccumulator: [],
      lastPathSegmentMatching: 0
    };
    const pathSegments = filePath.split("/").reverse();
    const processElementMatch = (elementDescriptor, matchInfo, currentPathSegments, elementPaths, isMainElementLevel) => {
      const { capture, baseCapture, useFullPathMatch, patternUsed } = matchInfo;
      let capturedValues = this._pathHelper.getCapturedValues(
        capture,
        elementDescriptor.capture
      );
      if (elementDescriptor.basePattern && baseCapture) {
        capturedValues = {
          ...this._pathHelper.getCapturedValues(
            baseCapture,
            elementDescriptor.baseCapture
          ),
          ...capturedValues
        };
      }
      let elementPath;
      if (useFullPathMatch) {
        elementPath = filePath;
      } else if (elementDescriptor.partialMatch === false && isMainElementLevel) {
        elementPath = this._getFullFolderMatchElementPath(
          patternUsed,
          filePath
        );
      } else {
        elementPath = this._getElementPath(
          patternUsed,
          currentPathSegments,
          elementPaths
        );
      }
      if (!elementResult.types && !elementResult.category) {
        this._setMainElement(
          elementResult,
          elementDescriptor,
          elementPath,
          filePath,
          capturedValues
        );
      } else if (isMainElementLevel && !this._singleType) {
        this._applyAccumulatedMatch(
          elementResult,
          elementDescriptor,
          capturedValues
        );
      } else if (elementPath !== elementResult.path) {
        this._addOrMergeParent(
          parents,
          elementDescriptor,
          elementPath,
          capturedValues
        );
      }
    };
    for (let i = 0; i < pathSegments.length; i++) {
      const segment = pathSegments[i];
      state.pathSegmentsAccumulator.unshift(segment);
      const alreadyHasMainElement = Boolean(elementResult.types) || Boolean(elementResult.category);
      let matchFoundAtThisLevel = false;
      for (const elementDescriptor of this._elementDescriptors) {
        const match = this._fileDescriptorMatch({
          elementDescriptor,
          filePath,
          currentPathSegments: state.pathSegmentsAccumulator,
          lastPathSegmentMatching: state.lastPathSegmentMatching,
          alreadyMatched: alreadyHasMainElement
        });
        if (match.matched) {
          processElementMatch(
            elementDescriptor,
            match,
            state.pathSegmentsAccumulator,
            pathSegments,
            !alreadyHasMainElement
          );
          matchFoundAtThisLevel = true;
          if (this._singleType || elementDescriptor.exclusive || elementDescriptor.stopMatching) {
            break;
          }
        }
      }
      if (matchFoundAtThisLevel) {
        state.pathSegmentsAccumulator = [];
        state.lastPathSegmentMatching = i + 1;
      }
    }
    const result = { ...elementResult, parents };
    if (!isKnownElementDescription(result)) {
      return {
        ...UNKNOWN_ELEMENT,
        path: null
        // Path is null for unknown elements, as it can't be resolved to any descriptor
      };
    }
    return result;
  }
  /**
   * Sets the main element data on the element result being built.
   * @param elementResult The element result being built.
   * @param elementDescriptor The descriptor that matched as the main element.
   * @param elementPath The resolved path of the main element.
   * @param filePath The full file path being described.
   * @param capturedValues The captured values for this match.
   */
  _setMainElement(elementResult, elementDescriptor, elementPath, filePath, capturedValues) {
    const isFolderMode = elementDescriptor.partialMatch === false || !elementDescriptor.mode || elementDescriptor.mode === ELEMENT_DESCRIPTOR_MODES_MAP.FOLDER;
    elementResult.types = elementDescriptor.type ? [elementDescriptor.type] : null;
    elementResult.category = elementDescriptor.category || null;
    elementResult.isUnknown = false;
    elementResult.path = elementPath;
    elementResult.captured = capturedValues;
    elementResult.fileInternalPath = isFolderMode || filePath !== elementPath ? filePath.replace(`${elementPath}/`, "") : filePath.split("/").pop() || // istanbul ignore next -- Ensures non-empty string if filePath were a single segment. Unreachable: filePath is guaranteed non-empty, so split("/").pop() always returns a truthy string
    filePath;
  }
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
  _applyAccumulatedMatch(target, elementDescriptor, capturedValues) {
    if (elementDescriptor.exclusive) {
      target.types = elementDescriptor.type ? [elementDescriptor.type] : null;
      target.category = elementDescriptor.category || null;
      target.captured = capturedValues;
      return;
    }
    if (elementDescriptor.type && isArray(target.types)) {
      target.types = [...target.types, elementDescriptor.type];
    }
    if (isObject(capturedValues)) {
      target.captured = {
        ...target.captured,
        ...capturedValues
      };
    }
  }
  /**
   * Adds a new parent element or merges into the last parent when it resolves to the same path.
   * @param parents The accumulated list of parent elements.
   * @param elementDescriptor The descriptor that matched as a parent.
   * @param elementPath The resolved path of the parent element.
   * @param capturedValues The captured values for this match.
   */
  _addOrMergeParent(parents, elementDescriptor, elementPath, capturedValues) {
    const lastParent = parents.at(-1);
    if (lastParent?.path === elementPath) {
      this._applyAccumulatedMatch(
        lastParent,
        elementDescriptor,
        capturedValues
      );
    } else {
      parents.push({
        types: elementDescriptor.type ? [elementDescriptor.type] : null,
        category: elementDescriptor.category || null,
        path: elementPath,
        captured: capturedValues
      });
    }
  }
  /**
   * Gets the folder key used to cache the folder-stable base description.
   * @param relativePath The relative file path.
   * @returns The folder portion of the path (everything but the last segment, empty for a file at the root).
   */
  _getFolderKey(relativePath) {
    const lastSeparatorIndex = relativePath.lastIndexOf("/");
    return lastSeparatorIndex === -1 ? "" : relativePath.slice(0, lastSeparatorIndex);
  }
  /**
   * Gets the file path relative to its element folder.
   * This is only used in the folder-cacheable branch, where all descriptors are in
   * folder mode, so the element path is always a folder containing the file.
   * @param relativePath The relative file path.
   * @param elementPath The matched element path.
   * @returns The file path relative to the element folder.
   */
  _getFileInternalPath(relativePath, elementPath) {
    return relativePath.replace(`${elementPath}/`, "");
  }
  /**
   * Describes an element reusing a folder-level cache.
   * The folder-stable base (path, types, category, captured, parents) is computed once
   * per folder and extended per file with the file-specific fields.
   * @param relativePath The relative file path.
   * @returns The description of the element.
   */
  _describeElementWithFolderCache(relativePath) {
    if (!this._pathHelper.pathIsIncluded(relativePath)) {
      return {
        ...UNKNOWN_ELEMENT,
        filePath: relativePath,
        path: relativePath,
        isIgnored: true
      };
    }
    const folderKey = this._getFolderKey(relativePath);
    let base = this._folderDescriptionsCache.get(folderKey);
    if (base === void 0) {
      base = this._describeElement(relativePath);
      this._folderDescriptionsCache.set(folderKey, base);
    }
    if (base.isUnknown) {
      return base;
    }
    return {
      ...base,
      filePath: relativePath,
      fileInternalPath: this._getFileInternalPath(relativePath, base.path)
    };
  }
  /**
   * Describes the element of a file given its path.
   * @param filePath The path of the dependency target file, if known. Can be absolute if rootPath is configured, or relative if not.
   * @returns The description of the dependency element.
   */
  describeElement(filePath) {
    const normalizedFilePath = filePath ? normalizePath(filePath) : filePath;
    const relativePath = normalizedFilePath && this._config.rootPath ? this._pathHelper.toRelativePath(normalizedFilePath) : normalizedFilePath;
    const cacheKey = `${relativePath}`;
    if (this._descriptionsCache.has(cacheKey)) {
      return this._descriptionsCache.get(cacheKey);
    }
    const description = this._canCacheByFolder && relativePath ? this._describeElementWithFolderCache(relativePath) : this._describeElement(relativePath);
    this._descriptionsCache.set(cacheKey, description);
    return description;
  }
};

// src/Descriptor/Dependency/DependencyDescriptorCache.ts
var DependenciesDescriptionsCache = class extends CacheManager {
  /** Generates a unique key for the given dependency description options.
   * @param options The options to generate the key from.
   * @returns The generated key.
   */
  generateKey(options) {
    return `${options.from}|${options.to}|${options.source}|${options.kind}|${options.nodeKind}|${options.specifiers ? options.specifiers.join(",") : ""}`;
  }
};

// src/Descriptor/Dependency/DependencyDescriptor.ts
var DependenciesDescriptor = class {
  /**
   * Cache to store previously described dependencies.
   */
  _dependenciesCache;
  /**
   * Elements descriptor instance.
   */
  _entitiesDescriptor;
  /**
   * Configuration options.
   */
  _config;
  /**
   * Creates a new DependenciesDescriptor instance.
   * @param entitiesDescriptor The entities descriptor instance.
   * @param config The configuration options.
   */
  constructor(entitiesDescriptor, config) {
    this._entitiesDescriptor = entitiesDescriptor;
    this._config = config;
    this._dependenciesCache = this._config.cache ? new DependenciesDescriptionsCache() : new CacheManagerDisabled();
  }
  /**
   * Serializes the dependencies cache to a plain object.
   * @returns The serialized dependencies cache.
   */
  serializeCache() {
    return this._dependenciesCache.serialize();
  }
  /**
   * Sets the dependencies cache from a serialized object.
   * @param serializedCache The serialized dependencies cache.
   */
  setCacheFromSerialized(serializedCache) {
    this._dependenciesCache.setFromSerialized(serializedCache);
  }
  /**
   * Clears the dependencies cache.
   */
  clearCache() {
    this._dependenciesCache.clear();
  }
  /**
   * Retrieves the element path of the parent of a given element.
   * @param elementInfo The element whose parent is to be retrieved.
   * @returns The parent element path, or undefined if none exists.
   */
  _getParent(elementDescription) {
    if (isNull(elementDescription.parents)) {
      return;
    }
    return elementDescription.parents[0]?.path;
  }
  /**
   * Retrieves the common ancestor of two elements.
   * @param elementInfoA The first element.
   * @param elementInfoB The second element.
   * @returns The common ancestor element path, or undefined if none exists.
   */
  _getCommonAncestor(elementInfoA, elementInfoB) {
    const commonAncestor = elementInfoA.parents.find((elementParentA) => {
      return elementInfoB.parents.some((elementParentB) => {
        return elementParentA.path === elementParentB.path;
      });
    });
    return commonAncestor?.path;
  }
  /**
   * Checks if the parent of element A is an ancestor of element B.
   * @param elementA The element A.
   * @param elementB The element B.
   * @returns True if the parent of element A is an ancestor of element B, false otherwise.
   */
  _isDescendantOfParent(elementA, elementB) {
    const commonAncestor = this._getCommonAncestor(elementA, elementB);
    return commonAncestor && commonAncestor === this._getParent(elementA);
  }
  /**
   * Checks if two elements are siblings (same parent).
   * @param elementA The first element.
   * @param elementB The second element.
   * @returns True if the elements are siblings, false otherwise.
   */
  _isSibling(elementA, elementB) {
    const parentA = this._getParent(elementA);
    const parentB = this._getParent(elementB);
    return parentA && parentB && parentA === parentB;
  }
  /**
   * Checks if one element is a descendant of another.
   * @param elementA The potential descendant element.
   * @param elementB The potential ancestor element.
   * @returns True if elementA is a descendant of elementB, false otherwise.
   */
  _isDescendant(elementA, elementB) {
    return elementA.parents.some((parent) => parent.path === elementB.path);
  }
  /**
   * Checks if one element is a child of another.
   * @param elementA The potential child element.
   * @param elementB The potential parent element.
   * @returns True if elementA is a child of elementB, false otherwise.
   */
  _isChild(elementA, elementB) {
    return this._getParent(elementA) === elementB.path;
  }
  /**
   * Checks if two local elements are internally related (same element).
   * @param elementA The first element.
   * @param elementB The second element.
   * @returns True if the elements are internally related, false otherwise.
   */
  _isInternal(elementA, elementB) {
    return elementA.path === elementB.path;
  }
  /**
   * Retrieves the relationship between two local known elements in terms of dependency.
   * @param from The element depending on another element.
   * @param to The element being depended on.
   * @returns The relationship between the elements.
   */
  _dependencyRelationship(from, to) {
    if (isIgnoredElementDescription(to) || !isKnownElementDescription(to) || !isKnownElementDescription(from)) {
      return null;
    }
    if (this._isInternal(to, from)) {
      return DEPENDENCY_RELATIONSHIPS_MAP.INTERNAL;
    }
    if (this._isChild(to, from)) {
      return DEPENDENCY_RELATIONSHIPS_MAP.CHILD;
    }
    if (this._isDescendant(to, from)) {
      return DEPENDENCY_RELATIONSHIPS_MAP.DESCENDANT;
    }
    if (this._isSibling(to, from)) {
      return DEPENDENCY_RELATIONSHIPS_MAP.SIBLING;
    }
    if (this._isChild(from, to)) {
      return DEPENDENCY_RELATIONSHIPS_MAP.PARENT;
    }
    if (this._isDescendant(from, to)) {
      return DEPENDENCY_RELATIONSHIPS_MAP.ANCESTOR;
    }
    if (this._isDescendantOfParent(to, from)) {
      return DEPENDENCY_RELATIONSHIPS_MAP.UNCLE;
    }
    if (this._isDescendantOfParent(from, to)) {
      return DEPENDENCY_RELATIONSHIPS_MAP.NEPHEW;
    }
    return null;
  }
  /**
   * Retrieves the relationships between two elements in terms of dependency, from the perspective of both elements.
   * @param from The element depending on another element.
   * @param to The element being depended on.
   * @returns The relationships between the elements from both perspectives.
   */
  _dependencyRelationships(from, to) {
    if (!to) {
      return {
        from: null,
        to: null
      };
    }
    const toRelationship = this._dependencyRelationship(
      from.element,
      to.element
    );
    const fromRelationship = toRelationship ? DEPENDENCY_RELATIONSHIPS_INVERTED_MAP[toRelationship] : null;
    return {
      from: fromRelationship,
      to: toRelationship
    };
  }
  /**
   * Describes elements in a dependency relationship, and provides additional information about the dependency itself.
   * @param options The options for describing the elements and the dependency details.
   * @returns The description of the dependency between the elements.
   */
  describeDependency({
    from,
    to,
    source,
    kind,
    nodeKind,
    specifiers
  }) {
    const cacheKey = this._dependenciesCache.getKey({
      from,
      to,
      source,
      kind,
      nodeKind,
      specifiers
    });
    if (this._dependenciesCache.has(cacheKey)) {
      return this._dependenciesCache.get(cacheKey);
    }
    const fromEntity = this._entitiesDescriptor.describeEntity(from);
    const toEntity = this._entitiesDescriptor.describeEntity(to, source);
    const relationship = this._dependencyRelationships(fromEntity, toEntity);
    const result = {
      from: fromEntity,
      to: toEntity,
      dependency: {
        source,
        kind,
        nodeKind: nodeKind || null,
        relationship,
        specifiers: specifiers || null
      }
    };
    this._dependenciesCache.set(cacheKey, result);
    return result;
  }
};

// src/Descriptor/File/FileDescriptionHelpers.ts
function isFileDescription(value) {
  return isBaseDescription(value) && isObjectWithProperty(value, "categories");
}
function isUnknownFileDescription(value) {
  return isFileDescription(value) && isUnknownDescription(value);
}
function isKnownFileDescription(value) {
  return isFileDescription(value) && isKnownDescription(value);
}
function isIgnoredFileDescription(value) {
  return isFileDescription(value) && isIgnoredDescription(value);
}

// src/Descriptor/Entity/EntityDescriptionHelpers.ts
function isEntityDescription(value) {
  return isObjectWithProperty(value, "element") && isObjectWithProperty(value, "file") && isObjectWithProperty(value, "module") && isElementDescription(value.element) && isFileDescription(value.file);
}

// src/Descriptor/Entity/EntityDescriptor.ts
var EntitiesDescriptor = class {
  /**
   * Cache to store previously described entities.
   */
  _descriptionsCache;
  /**
   * Configuration instance for this descriptor.
   */
  _config;
  _elementsDescriptor;
  _filesDescriptor;
  _modulesDescriptor;
  /**
   * The configuration options for this descriptor.
   * @param elementsDescriptor The elements descriptor instance, used to describe elements when describing entities.
   * @param filesDescriptor The files descriptor instance, used to describe files when describing entities.
   * @param originsDescriptor The origins descriptor instance, used to describe the origin of entities when describing them.
   * @param config The configuration options for this descriptor.
   */
  constructor(elementsDescriptor, filesDescriptor, modulesDescriptor, config) {
    this._elementsDescriptor = elementsDescriptor;
    this._filesDescriptor = filesDescriptor;
    this._modulesDescriptor = modulesDescriptor;
    this._config = config;
    this._descriptionsCache = this._config.cache ? new CacheManager() : new CacheManagerDisabled();
  }
  /**
   * Serializes the elements cache to a plain object.
   * @returns The serialized elements cache.
   */
  serializeCache() {
    return {
      descriptions: this._descriptionsCache.serialize()
    };
  }
  /**
   * Sets the elements cache from a serialized object.
   * @param serializedCache The serialized files cache.
   */
  setCacheFromSerialized(serializedCache) {
    this._descriptionsCache.setFromSerialized(serializedCache.descriptions);
  }
  /**
   * Clears the files cache.
   */
  clearCache() {
    this._descriptionsCache.clear();
  }
  /**
   * Describes an entity given its file path.
   * @param filePath The absolute path of the file to describe
   * @param source The optional dependency source (e.g., the importer file path) to use for describing the origin of the entity being imported.
   */
  describeEntity(filePath, source) {
    const cacheKey = `${filePath}::${source}`;
    if (this._descriptionsCache.has(cacheKey)) {
      return this._descriptionsCache.get(cacheKey);
    }
    const elementDescription = this._elementsDescriptor.describeElement(filePath);
    const fileDescription = this._filesDescriptor.describeFile(filePath);
    const moduleDescription = this._modulesDescriptor.describeModule(
      filePath,
      source
    );
    const entityDescription = {
      element: elementDescription,
      file: fileDescription,
      module: moduleDescription
    };
    this._descriptionsCache.set(cacheKey, entityDescription);
    return entityDescription;
  }
};

// src/Descriptor/Dependency/DependencyDescriptionHelpers.ts
function isDependencyKind(value) {
  return isString(value) && DEPENDENCY_KINDS_SET.has(value);
}
function isDependencyRelationship(value) {
  return isString(value) && DEPENDENCY_RELATIONSHIPS_SET.has(value);
}
function isDependencyRelationshipDescription(value) {
  return isObjectWithProperty(value, "to") && (isNull(value.to) || isDependencyRelationship(value.to)) && isObjectWithProperty(value, "from") && (isNull(value.from) || isDependencyRelationship(value.from));
}
function isDependencyInfo(value) {
  return isObjectWithProperty(value, "source") && isString(value.source) && isObjectWithProperty(value, "kind") && isDependencyKind(value.kind) && isObjectWithProperty(value, "relationship") && isDependencyRelationshipDescription(value.relationship) && isObjectWithProperty(value, "nodeKind") && (isNull(value.nodeKind) || isString(value.nodeKind)) && isObjectWithProperty(value, "specifiers") && (isNull(value.specifiers) || isStringArray(value.specifiers));
}
function isDependencyDescription(value) {
  return isObjectWithProperty(value, "to") && isEntityDescription(value.to) && isObjectWithProperty(value, "from") && isEntityDescription(value.from) && isObjectWithProperty(value, "dependency") && isDependencyInfo(value.dependency);
}
function isDependencyWithInternalRelationship(dependency) {
  return dependency.dependency.relationship.to === DEPENDENCY_RELATIONSHIPS_MAP.INTERNAL;
}

// src/Descriptor/File/FileDescriptorHelpers.ts
function isFileDescriptor(value) {
  return isBaseDescriptor(value) && isObjectWithProperty(value, "category") && isString(value.category);
}

// src/Descriptor/File/FileDescriptor.ts
var BACKWARD_COMPATIBILITY_CAPTURE_PROPERTY = "restOfPath";
var UNKNOWN_FILE_DESCRIPTION = {
  path: null,
  categories: null,
  isIgnored: false,
  isUnknown: true,
  captured: null
};
var FilesDescriptor = class {
  /**
   * Cache to store previously described files.
   */
  _descriptionsCache;
  /**
   * Configuration instance for this descriptor.
   */
  _config;
  /**
   * File descriptors used by this descriptor.
   */
  _fileDescriptors;
  /** Micromatch instance for path matching */
  _micromatch;
  /** Shared path helper providing root-path and include/ignore utilities */
  _pathHelper;
  /**
   * When `true`, only the first matching file descriptor's category is kept and matching stops.
   * Global shorthand equivalent to setting `stopMatching: true` on every file descriptor.
   */
  _singleMatch;
  /**
   * The configuration options for this descriptor.
   * @param fileDescriptors The file descriptors.
   * @param configOptions The configuration options.
   * @param micromatch The micromatch instance for path matching.
   * @param singleMatch When `true`, only the first matching file descriptor's category is used; matching stops.
   */
  constructor(fileDescriptors, configOptions, micromatch2, singleMatch = false) {
    this._micromatch = micromatch2;
    this._fileDescriptors = fileDescriptors;
    this._validateDescriptors(fileDescriptors);
    this._config = configOptions;
    this._pathHelper = new PathHelper(configOptions, micromatch2);
    this._singleMatch = singleMatch;
    this._descriptionsCache = this._config.cache ? new CacheManager() : new CacheManagerDisabled();
  }
  /**
   * Serializes the elements cache to a plain object.
   * @returns The serialized elements cache.
   */
  serializeCache() {
    return {
      descriptions: this._descriptionsCache.serialize()
    };
  }
  /**
   * Sets the elements cache from a serialized object.
   * @param serializedCache The serialized files cache.
   */
  setCacheFromSerialized(serializedCache) {
    this._descriptionsCache.setFromSerialized(serializedCache.descriptions);
  }
  /**
   * Clears the files cache.
   */
  clearCache() {
    this._descriptionsCache.clear();
  }
  /**
   * Validates the file descriptors to ensure they are correctly defined.
   */
  _validateDescriptors(fileDescriptors) {
    let index = 0;
    for (const descriptor of fileDescriptors) {
      if (!isFileDescriptor(descriptor)) {
        throw new Error(
          `File descriptor at index ${index} must have a pattern, and a 'category' defined.`
        );
      }
      index++;
    }
  }
  _fileDescriptorMatch({
    fileDescriptor,
    filePath
  }) {
    const patterns = isArray(fileDescriptor.pattern) ? fileDescriptor.pattern : [fileDescriptor.pattern];
    for (const pattern of patterns) {
      const patternUsed = fileDescriptor.basePattern ? `${fileDescriptor.basePattern}/${pattern}` : pattern;
      const capture = this._micromatch.capture(patternUsed, filePath);
      if (capture) {
        return {
          matched: true,
          capture
        };
      }
    }
    return { matched: false };
  }
  /**
   * Returns the capture array for a file descriptor. When basePattern is used, combines baseCapture
   * and capture for backward compatibility with legacy mode "file". Otherwise, returns the plain
   * capture array as-is, matching it directly against the pattern's own capture groups.
   * @param fileDescriptor The file descriptor to get the capture array for.
   * @returns The capture array, or undefined if no capture is configured.
   */
  _getCaptureArray(fileDescriptor) {
    if (fileDescriptor.basePattern) {
      if (fileDescriptor.baseCapture && fileDescriptor.capture) {
        return [
          ...fileDescriptor.baseCapture,
          BACKWARD_COMPATIBILITY_CAPTURE_PROPERTY,
          ...fileDescriptor.capture
        ];
      } else if (fileDescriptor.baseCapture) {
        return [
          ...fileDescriptor.baseCapture,
          BACKWARD_COMPATIBILITY_CAPTURE_PROPERTY
        ];
      } else if (fileDescriptor.capture) {
        return [
          BACKWARD_COMPATIBILITY_CAPTURE_PROPERTY,
          ...fileDescriptor.capture
        ];
      }
    }
    return fileDescriptor.capture;
  }
  /**
   * Retrieves the description of a local file given its path.
   * @param elementPath The path of the element to describe.
   * @returns The description of the element.
   */
  _getFileDescription(filePath) {
    if (!filePath) {
      return UNKNOWN_FILE_DESCRIPTION;
    }
    if (!this._pathHelper.pathIsIncluded(filePath)) {
      return {
        ...UNKNOWN_FILE_DESCRIPTION,
        path: filePath,
        categories: null,
        isIgnored: true
      };
    }
    const fileResult = {
      ...UNKNOWN_FILE_DESCRIPTION,
      path: filePath,
      isIgnored: false
    };
    const processElementMatch = (fileDescriptor, matchInfo) => {
      const { capture } = matchInfo;
      const capturedValues = this._pathHelper.getCapturedValues(
        capture,
        this._getCaptureArray(fileDescriptor)
      );
      if (fileDescriptor.exclusive) {
        fileResult.categories = [fileDescriptor.category];
        fileResult.captured = capturedValues;
      } else {
        fileResult.categories = isArray(fileResult.categories) ? [...fileResult.categories, fileDescriptor.category] : [fileDescriptor.category];
        if (isObject(capturedValues)) {
          fileResult.captured = {
            ...fileResult.captured,
            ...capturedValues
          };
        }
      }
      fileResult.isUnknown = false;
    };
    for (const fileDescriptor of this._fileDescriptors) {
      const match = this._fileDescriptorMatch({
        fileDescriptor,
        filePath
      });
      if (match.matched) {
        processElementMatch(fileDescriptor, match);
        if (fileDescriptor.basePattern) {
          break;
        }
        if (fileDescriptor.exclusive || fileDescriptor.stopMatching || this._singleMatch) {
          break;
        }
      }
    }
    if (!isKnownFileDescription(fileResult)) {
      const result = {
        ...fileResult,
        categories: null,
        isIgnored: false,
        isUnknown: true,
        captured: null
      };
      return result;
    }
    return fileResult;
  }
  /**
   * Describes a file given its path.
   * @param filePath The absolute path of the file to describe
   */
  describeFile(filePath) {
    const cacheKey = `$${filePath}`;
    if (this._descriptionsCache.has(cacheKey)) {
      return this._descriptionsCache.get(cacheKey);
    }
    const normalizedFilePath = filePath ? normalizePath(filePath) : filePath;
    const relativePath = normalizedFilePath && this._config.rootPath ? this._pathHelper.toRelativePath(normalizedFilePath) : normalizedFilePath;
    const fileDescription = this._getFileDescription(relativePath);
    this._descriptionsCache.set(cacheKey, fileDescription);
    return fileDescription;
  }
};

// src/Descriptor/Module/ModuleDescription.types.ts
var ORIGINS_MAP = {
  /** Origin of local files */
  LOCAL: "local",
  /** Origin of external files (usually from node_modules, but also files flagged as external due to configuration) */
  EXTERNAL: "external",
  /** Origin of built-in files (Node.js core modules) */
  CORE: "core"
};
var ORIGINS_SET = new Set(Object.values(ORIGINS_MAP));

// src/Descriptor/Module/ModuleDescriptor.ts
import isCoreModule from "is-core-module";
var SCOPED_PACKAGE_REGEX = /^@[^/]*\/?[^/]+/;
var EXTERNAL_PATH_REGEX = /^\w/;
var ModulesDescriptor = class {
  _mod = null;
  /**
   * Cache to store previously described modules.
   */
  _descriptionsCache;
  /**
   * Configuration instance for this descriptor.
   */
  _config;
  /** Micromatch instance for path matching */
  _micromatch;
  /** Shared path helper providing root-path utilities */
  _pathHelper;
  /**
   * The configuration options for this descriptor.
   * @param configOptions The configuration options.
   * @param micromatch The micromatch instance for path matching.
   */
  constructor(configOptions, micromatch2) {
    this._micromatch = micromatch2;
    this._config = configOptions;
    this._pathHelper = new PathHelper(configOptions, micromatch2);
    this._descriptionsCache = this._config.cache ? new CacheManager() : new CacheManagerDisabled();
    this._loadModuleInNode();
  }
  /**
   * Loads the Node.js module to access built-in modules information when running in Node.js environment.
   */
  _loadModuleInNode() {
    if (!this._mod && !isNullish(process) && !isNullish(process.versions) && !isNullish(process.versions.node)) {
      this._mod = __require("module");
    }
  }
  /**
   * Determines if a dependency source is a core module.
   * @param dependencySource The source of the dependency to check.
   * @param baseDependencySource The base source of the dependency to check.
   * @returns True if the dependency source is a core module, false otherwise.
   */
  _dependencySourceIsCoreModule(dependencySource, baseDependencySource) {
    if (this._mod) {
      const moduleWithoutPrefix = baseDependencySource.startsWith("node:") ? baseDependencySource.slice(5) : baseDependencySource;
      return this._mod.builtinModules.includes(moduleWithoutPrefix);
    }
    return isCoreModule(dependencySource);
  }
  /**
   * Determines if a dependency source is scoped (e.g., @scope/package).
   * @param dependencySource The source of the dependency to check.
   * @returns True if the dependency source is scoped, false otherwise.
   */
  _dependencySourceIsScoped(dependencySource) {
    return SCOPED_PACKAGE_REGEX.test(dependencySource);
  }
  /**
   * Determines if a dependency source is external or an alias.
   * @param dependencySource The source of the dependency to check.
   * @returns True if the dependency source is external or an alias, false otherwise.
   */
  _dependencySourceIsExternalOrScoped(dependencySource) {
    return EXTERNAL_PATH_REGEX.test(dependencySource) || this._dependencySourceIsScoped(dependencySource);
  }
  /**
   * Gets the base source of an external module.
   * @param dependencySource The source of the dependency to check.
   * @returns The base source of the external module. (e.g., for "@scope/package/submodule", it returns "@scope/package")
   */
  _getExternalOrCoreSourceModule(dependencySource) {
    if (this._dependencySourceIsScoped(dependencySource)) {
      const [scope, packageName] = dependencySource.split("/");
      return `${scope}/${packageName}`;
    }
    const [pkg] = dependencySource.split("/");
    return pkg;
  }
  /**
   * Checks if a source string matches any of the provided patterns using micromatch.
   * @param patterns - Array of micromatch patterns
   * @param source - The source string to match against patterns
   * @returns True if the source matches any pattern, false otherwise
   */
  _matchesAnyPattern(patterns, source) {
    if (!source || patterns.length === 0) {
      return false;
    }
    return this._micromatch.isMatch(source, patterns);
  }
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
  _isExternal(filePath, isOutsideRootPath, dependencySource) {
    const {
      unresolvableAlias,
      inNodeModules,
      outsideRootPath,
      customSourcePatterns
    } = this._config.flagAsExternal;
    if (outsideRootPath && isOutsideRootPath) {
      return true;
    }
    if (inNodeModules && filePath?.includes("node_modules")) {
      return true;
    }
    if (unresolvableAlias && !filePath && dependencySource && this._dependencySourceIsExternalOrScoped(dependencySource)) {
      return true;
    }
    if (this._matchesAnyPattern(customSourcePatterns, dependencySource)) {
      return true;
    }
    return false;
  }
  /**
   * Serializes the origins cache to a plain object.
   * @returns The serialized origins cache.
   */
  serializeCache() {
    return {
      descriptions: this._descriptionsCache.serialize()
    };
  }
  /**
   * Sets the origins cache from a serialized object.
   * @param serializedCache The serialized origins cache.
   */
  setCacheFromSerialized(serializedCache) {
    this._descriptionsCache.setFromSerialized(serializedCache.descriptions);
  }
  /**
   * Clears the origins cache.
   */
  clearCache() {
    this._descriptionsCache.clear();
  }
  /**
   * Gets the module description for a given relative path and source.
   * @param relativePath The relative path of the file.
   * @param dependencySource The source of the dependency (e.g., the import statement or require call).
   * @returns The description of the file's module.
   */
  _getDependencyModuleDescription(isOutsideRootPath, dependencySource, relativePath) {
    const baseDependencySource = this._getExternalOrCoreSourceModule(dependencySource);
    const moduleInternalPath = dependencySource.startsWith(
      `${baseDependencySource}/`
    ) ? dependencySource.slice(baseDependencySource.length + 1) : null;
    const isCore = this._dependencySourceIsCoreModule(
      dependencySource,
      baseDependencySource
    );
    if (isCore) {
      return {
        origin: ORIGINS_MAP.CORE,
        source: baseDependencySource,
        internalPath: moduleInternalPath
      };
    }
    const isExternal = this._isExternal(
      relativePath || null,
      isOutsideRootPath,
      dependencySource
    );
    if (isExternal) {
      return {
        origin: ORIGINS_MAP.EXTERNAL,
        source: baseDependencySource,
        internalPath: moduleInternalPath
      };
    }
    return {
      origin: ORIGINS_MAP.LOCAL,
      source: null,
      internalPath: null
    };
  }
  /**
   * Gets the module description for a file that is not imported as a dependency.
   * @param isOutsideRootPath Indicates if the file is outside the configured root path.
   * @param relativePath The relative path of the file.
   * @returns The description of the file's module.
   */
  _getFileModuleDescription(isOutsideRootPath, relativePath) {
    const isExternal = this._isExternal(
      relativePath || null,
      isOutsideRootPath
    );
    if (isExternal) {
      return {
        origin: ORIGINS_MAP.EXTERNAL,
        source: null,
        internalPath: null
      };
    }
    return {
      origin: ORIGINS_MAP.LOCAL,
      source: null,
      internalPath: null
    };
  }
  /**
   * Gets the origin description for a given relative path and source.
   * @param relativePath The relative path of the file.
   * @param source The source of the dependency (e.g., the import statement or require call).
   * @param isOutsideRootPath Whether the file path is outside the configured root path.
   * @returns The description of the file's module.
   */
  _getModuleDescription(isOutsideRootPath, relativePath, source) {
    if (source) {
      return this._getDependencyModuleDescription(
        isOutsideRootPath,
        source,
        relativePath
      );
    }
    return this._getFileModuleDescription(isOutsideRootPath, relativePath);
  }
  /**
   * Describes the module of a file path given its dependency source and the file path itself.
   * @param filePath The absolute path of the file to describe
   * @param source The source of the dependency (e.g., the import statement or require call)
   * @returns The description of the file's module, including its origin, and module if applicable
   */
  describeModule(filePath, source) {
    const cacheKey = `${filePath}::${source}`;
    if (this._descriptionsCache.has(cacheKey)) {
      return this._descriptionsCache.get(cacheKey);
    }
    const normalizedFilePath = filePath ? normalizePath(filePath) : filePath;
    const isOutsideRootPath = normalizedFilePath ? this._pathHelper.isOutsideRootPath(normalizedFilePath) : true;
    const relativePath = normalizedFilePath && this._config.rootPath ? this._pathHelper.toRelativePath(normalizedFilePath) : normalizedFilePath;
    const moduleDescription = this._getModuleDescription(
      isOutsideRootPath,
      relativePath,
      source
    );
    this._descriptionsCache.set(cacheKey, moduleDescription);
    return moduleDescription;
  }
};

// src/Descriptor/Module/ModuleDescriptionHelpers.ts
function isOriginDescription(value) {
  return isObjectWithAnyOfProperties(value, ["origin", "source", "internalPath"]) && ORIGINS_SET.has(value.origin);
}

// src/Descriptor/Descriptors.ts
function resolveElementsSingleMatch(descriptors) {
  return descriptors.elementsSingleMatch ?? descriptors.elementsSingleType ?? false;
}
var Descriptors = class {
  _elementsDescriptor;
  _filesDescriptor;
  _dependenciesDescriptor;
  _entitiesDescriptor;
  _modulesDescriptor;
  /** Creates a new DescriptorsManager instance
   * @param descriptors The descriptors.
   * @param configOptions The configuration options.
   * @param micromatch The Micromatch instance.
   */
  constructor(descriptors, config, micromatch2) {
    this._elementsDescriptor = new ElementsDescriptor(
      descriptors.elements || [],
      config,
      micromatch2,
      resolveElementsSingleMatch(descriptors)
    );
    this._filesDescriptor = new FilesDescriptor(
      descriptors.files || [],
      config,
      micromatch2,
      descriptors.filesSingleMatch ?? false
    );
    this._modulesDescriptor = new ModulesDescriptor(config, micromatch2);
    this._entitiesDescriptor = new EntitiesDescriptor(
      this._elementsDescriptor,
      this._filesDescriptor,
      this._modulesDescriptor,
      config
    );
    this._dependenciesDescriptor = new DependenciesDescriptor(
      this._entitiesDescriptor,
      config
    );
  }
  /**
   * Serializes the elements, files, entities, and dependencies cache to a plain object.
   * @returns The serialized elements, files, entities, and dependencies cache.
   */
  serializeCache() {
    return {
      elements: this._elementsDescriptor.serializeCache(),
      files: this._filesDescriptor.serializeCache(),
      entities: this._entitiesDescriptor.serializeCache(),
      dependencies: this._dependenciesDescriptor.serializeCache(),
      modules: this._modulesDescriptor.serializeCache()
    };
  }
  /**
   * Sets the elements, files, entities, and dependencies cache from a serialized object.
   * @param serializedCache The serialized elements, files, entities, and dependencies cache.
   */
  setCacheFromSerialized(serializedCache) {
    this._elementsDescriptor.setCacheFromSerialized(serializedCache.elements);
    this._filesDescriptor.setCacheFromSerialized(serializedCache.files);
    this._entitiesDescriptor.setCacheFromSerialized(serializedCache.entities);
    this._dependenciesDescriptor.setCacheFromSerialized(
      serializedCache.dependencies
    );
    this._modulesDescriptor.setCacheFromSerialized(serializedCache.modules);
  }
  /**
   * Clears all caches.
   */
  clearCache() {
    this._elementsDescriptor.clearCache();
    this._filesDescriptor.clearCache();
    this._entitiesDescriptor.clearCache();
    this._dependenciesDescriptor.clearCache();
    this._modulesDescriptor.clearCache();
  }
  /**
   * Describes an element given its file path.
   * @param filePath The path of the file to describe.
   * @returns The description of the element.
   */
  describeElement(filePath) {
    return this._elementsDescriptor.describeElement(filePath);
  }
  /**
   * Returns the description of a file given its path.
   * @param filePath The path of the file to describe.
   * @returns The description of the file.
   */
  describeFile(filePath) {
    return this._filesDescriptor.describeFile(filePath);
  }
  /**
   * Describes a file given its path. It returns both the file description and the element description.
   * @param filePath The path of the file to describe.
   * @param source The optional dependency source (e.g., the importer file path) to use for describing the origin of the entity being imported.
   * @returns The entity description of the file, including both the file description and the element description.
   */
  describeEntity(filePath, source) {
    return this._entitiesDescriptor.describeEntity(filePath, source);
  }
  /**
   * Describes a module given its path and the path of the importer file.
   * @param filePath The path of the file to describe.
   * @param source The optional dependency source (e.g., the importer file path) to use for describing the origin of the entity being imported.
   * @returns The description of the module.
   */
  describeModule(filePath, source) {
    return this._modulesDescriptor.describeModule(filePath, source);
  }
  /**
   * Describes elements in a dependency relationship, and provides additional information about the dependency itself.
   * @param options The options for describing the elements and the dependency details.
   * @returns The description of the dependency between the elements.
   */
  describeDependency(options) {
    return this._dependenciesDescriptor.describeDependency(options);
  }
};

// src/Matcher/Element/ElementSelectorHelpers.ts
function isLegacySimpleElementSingleSelectorByType(value) {
  return isString(value);
}
function isLegacySimpleElementSingleSelectorByTypeWithOptions(value) {
  return isArray(value) && (value.length === 2 && isLegacySimpleElementSingleSelectorByType(value[0]) && // NOTE: Arrays of length 2 with captured values selector as second will be treated as legacy options instead of two different selectors. We have to live with this limitation for now.
  isCapturedValuesSelector(value[1]) || // NOTE: Backwards compatibility: Allow arrays of length 1 with simple element selector. Some users might defined arrays without options.
  value.length === 1 && isLegacySimpleElementSingleSelectorByType(value[0]));
}
function isLegacySimpleElementSingleSelector(value) {
  return isLegacySimpleElementSingleSelectorByType(value) || isLegacySimpleElementSingleSelectorByTypeWithOptions(value);
}
function isLegacySimpleElementSelector(value) {
  return isLegacySimpleElementSingleSelector(value) || isArray(value) && value.some(isLegacySimpleElementSingleSelector);
}
function isLegacyParentElementSingleSelector(selector) {
  return isObjectWithProperty(selector, "elementPath");
}
function isLegacyElementSingleObjectSelector(selector) {
  return isObjectWithAnyOfProperties(selector, [
    "origin",
    "elementPath",
    "internalPath"
  ]) || isObjectWithProperty(selector, "parent") && isLegacyParentElementSingleSelector(selector.parent);
}
function isLegacyElementSingleSelector(selector) {
  return isLegacyElementSingleObjectSelector(selector) || isLegacySimpleElementSingleSelector(selector);
}
function isLegacyElementSelector(selector) {
  return isLegacyElementSingleSelector(selector) || isArray(selector) && selector.some(isLegacyElementSingleSelector);
}
function isElementSingleSelector(value) {
  return isObjectWithAnyOfProperties(value, [
    "type",
    "types",
    "parent",
    "parents",
    "category",
    "fileInternalPath"
  ]) || extendsSingleSelector(value);
}
function isElementSelector(value) {
  return isElementSingleSelector(value) || isArray(value) && value.every(isElementSingleSelector);
}
function isBackwardCompatibleElementSingleSelector(selector) {
  return isLegacyElementSingleSelector(selector) || isElementSingleSelector(selector);
}
function isBackwardCompatibleElementSelector(selector) {
  return isLegacyElementSelector(selector) || isElementSelector(selector);
}
function normalizeLegacySimpleElementSingleSelector(selector) {
  if (isLegacySimpleElementSingleSelectorByType(selector)) {
    return { type: selector };
  }
  if (isLegacySimpleElementSingleSelectorByTypeWithOptions(selector)) {
    const objectSelector = {
      type: selector[0]
    };
    if (selector[1] && isCapturedValuesSelector(selector[1])) {
      objectSelector.captured = { ...selector[1] };
    }
    return objectSelector;
  }
  throw new Error("Invalid legacy simple element single selector");
}
function normalizeLegacyParentElementSingleSelector(selector) {
  const { elementPath, ...parentSelector } = selector;
  if (!isUndefined(elementPath)) {
    parentSelector.path = elementPath;
  }
  return parentSelector;
}
function normalizeLegacyParentElementSelectors(selector) {
  return selector.map(
    (sel) => isLegacyParentElementSingleSelector(sel) ? normalizeLegacyParentElementSingleSelector(sel) : sel
  );
}
function normalizeParentElementSelector(selector) {
  if (isNull(selector)) {
    return null;
  }
  if (isArray(selector)) {
    return normalizeLegacyParentElementSelectors(selector);
  }
  return [
    isLegacyParentElementSingleSelector(selector) ? normalizeLegacyParentElementSingleSelector(selector) : selector
  ];
}
function normalizeParentInElementSingleSelector(selector) {
  const { parent, ...rest } = selector;
  const normalizedSelector = { ...rest };
  if (!isUndefined(parent)) {
    normalizedSelector.parent = normalizeParentElementSelector(parent);
  }
  return normalizedSelector;
}
function normalizeLegacyElementSingleObjectSelector(selector) {
  const { origin, elementPath, internalPath, parent, ...rest } = selector;
  if (!isUndefined(origin)) {
    throw new Error(
      `Cannot convert legacy element selector to element selector: the "origin" property is an entity-level property and cannot be represented in an element selector. Use convertLegacyElementSingleSelectorToEntitySelector instead.`
    );
  }
  const elementSelector = { ...rest };
  if (!isUndefined(parent)) {
    elementSelector.parent = parent;
  }
  if (!isUndefined(elementPath)) {
    elementSelector.path = elementPath;
  }
  if (!isUndefined(internalPath)) {
    elementSelector.fileInternalPath = internalPath;
  }
  return normalizeParentInElementSingleSelector(elementSelector);
}
function normalizeLegacyElementSingleSelector(selector) {
  if (isLegacySimpleElementSingleSelector(selector)) {
    return normalizeLegacySimpleElementSingleSelector(selector);
  }
  if (isLegacyElementSingleObjectSelector(selector)) {
    return normalizeLegacyElementSingleObjectSelector(selector);
  }
  throw new Error("Invalid legacy element single selector");
}
function normalizeSingleElementSelector(selector) {
  if (isLegacyElementSingleSelector(selector)) {
    return normalizeLegacyElementSingleSelector(selector);
  }
  if (!isElementSingleSelector(selector)) {
    throw new Error("Invalid element selector");
  }
  return normalizeParentInElementSingleSelector(selector);
}
function normalizeElementSelector(elementSelector) {
  if (isLegacySimpleElementSingleSelectorByTypeWithOptions(elementSelector)) {
    return [normalizeSingleElementSelector(elementSelector)];
  }
  if (isArray(elementSelector)) {
    return elementSelector.map((sel) => normalizeSingleElementSelector(sel));
  }
  return [normalizeSingleElementSelector(elementSelector)];
}

// src/Matcher/Element/ElementMatcher.ts
var ElementsMatcher = class extends BaseElementsMatcher {
  /**
   * Creates a new ElementsSelectorMatcher.
   * @param config Configuration options for the matcher.
   * @param micromatch Micromatch instance for matching.
   * @param globalCache Global cache instance.
   */
  constructor(config, micromatch2) {
    super(config, micromatch2);
  }
  /**
   * Whether the given element first type matches the selector type (singular).
   * @param element The element to check.
   * @param selector The selector to check against.
   * @param templateData The data to use for replace in selector value
   * @returns Whether the element first type matches the selector type.
   */
  _isSingleTypeMatch(element, selector, templateData) {
    if (isUndefined(selector.type)) {
      return true;
    }
    return this.isTemplateMicromatchMatch(
      selector.type,
      templateData,
      element.types?.[0] ?? null
    );
  }
  /**
   * Whether the given element type matches the selector type.
   * @param element The element to check.
   * @param selector The selector to check against.
   * @param templateData The data to use for replace in selector value
   * @returns Whether the element type matches the selector type.
   */
  _isTypeMatch(element, selector, templateData) {
    const typesSelector = selector.types;
    if (isUndefined(typesSelector)) {
      return true;
    }
    if (isStringArrayQuery(typesSelector)) {
      return this.isStringArrayQueryMatch(
        element.types,
        typesSelector,
        templateData
      );
    }
    return this.isObjectKeyMicromatchMatch({
      object: element,
      selector,
      objectKey: "types",
      selectorKey: "types",
      selectorValue: typesSelector,
      templateData
    });
  }
  /**
   * Whether the given element path matches the selector path.
   * @param element The element to check.
   * @param selector The selector to check against.
   * @param templateData The data to use for replace in selector value
   * @returns Whether the element path matches the selector path.
   */
  _isPathMatch(element, selector, templateData) {
    return this.isObjectKeyMicromatchMatch({
      object: element,
      selector,
      objectKey: "path",
      selectorKey: "path",
      selectorValue: selector.path,
      templateData
    });
  }
  /**
   * Whether the given element file internal path matches the selector file internal path.
   * @param element The element to check.
   * @param selector The selector to check against.
   * @param templateData The data to use for replace in selector value
   * @returns Whether the element file internal path matches the selector file internal path.
   */
  _isFileInternalPathMatch(element, selector, templateData) {
    return this.isObjectKeyMicromatchMatch({
      object: element,
      selector,
      objectKey: "fileInternalPath",
      selectorKey: "fileInternalPath",
      selectorValue: selector.fileInternalPath,
      templateData
    });
  }
  /**
   * Checks if a single captured values object matches the element.
   * @param capturedValues The captured values to check.
   * @param capturedSelector The captured values selector object to check against
   * @param templateData The data to use for replace in selector values
   * @returns True if all captured values in the selector match those in the element, false otherwise.
   */
  _checkCapturedValuesObject(capturedValues, capturedSelector, templateData) {
    if (!capturedValues) {
      return false;
    }
    for (const [key, pattern] of Object.entries(capturedSelector)) {
      const elementValue = capturedValues[key];
      if (!elementValue) {
        return false;
      }
      const renderedPattern = this.getRenderedTemplates(pattern, templateData);
      const filteredPattern = this.cleanMicromatchPattern(renderedPattern);
      if (!filteredPattern) {
        return false;
      }
      const isMatch = this.micromatch.isMatch(elementValue, filteredPattern);
      if (!isMatch) {
        return false;
      }
    }
    return true;
  }
  /**
   * Determines if the captured values of the element match those in the selector.
   * When the selector is an array, the element matches if it matches any of the array elements (OR logic).
   * @param element The element to check.
   * @param selector The selector to check against
   * @param templateData The data to use for replace in selector values
   * @returns True if the captured values match, false otherwise.
   */
  _isCapturedValuesMatch(element, selector, templateData) {
    if (!selector.captured || isEmptyObject(selector.captured)) {
      return true;
    }
    if (isArray(selector.captured)) {
      if (selector.captured.length === 0) {
        return false;
      }
      return selector.captured.some(
        (capturedSelector) => this._checkCapturedValuesObject(
          element.captured,
          capturedSelector,
          templateData
        )
      );
    }
    return this._checkCapturedValuesObject(
      element.captured,
      selector.captured,
      templateData
    );
  }
  /**
   * Determines if the parent captured values match the selector.
   * @param parentSelector The parent selector to match.
   * @param parentCaptured The captured values from first parent.
   * @param templateData The data to use for replace in selector values
   * @returns True if the captured values match, false otherwise.
   */
  _isParentCapturedValuesMatch(parentSelector, parentCaptured, templateData) {
    if (!parentSelector.captured || isEmptyObject(parentSelector.captured)) {
      return true;
    }
    if (isArray(parentSelector.captured)) {
      if (parentSelector.captured.length === 0) {
        return false;
      }
      return parentSelector.captured.some(
        (capturedSelector) => this._checkCapturedValuesObject(
          parentCaptured,
          capturedSelector,
          templateData
        )
      );
    }
    return this._checkCapturedValuesObject(
      parentCaptured,
      parentSelector.captured,
      templateData
    );
  }
  /**
   * Whether a specific parent element matches a parent single selector.
   * Does not handle null selectors or the "first parent" lookup.
   * @param parent The parent element to check.
   * @param selector The parent selector to check against.
   * @param templateData The data to use for replace in selector values.
   * @returns Whether the parent matches the selector.
   */
  _isParentMatch(parent, selector, templateData) {
    if (!isUndefined(selector.type) && !this.isTemplateMicromatchMatch(
      selector.type,
      templateData,
      parent.types?.[0] ?? null
    )) {
      return false;
    }
    if (!isUndefined(selector.types)) {
      if (isStringArrayQuery(selector.types)) {
        if (!this.isStringArrayQueryMatch(
          parent.types,
          selector.types,
          templateData
        )) {
          return false;
        }
      } else if (!this.isTemplateMicromatchMatch(
        selector.types,
        templateData,
        parent.types
      )) {
        return false;
      }
    }
    if (!isUndefined(selector.path) && !this.isTemplateMicromatchMatch(selector.path, templateData, parent.path)) {
      return false;
    }
    if (!isUndefined(selector.category) && !this.isTemplateMicromatchMatch(
      selector.category,
      templateData,
      parent.category
    )) {
      return false;
    }
    if (!this._isParentCapturedValuesMatch(
      selector,
      parent.captured,
      templateData
    )) {
      return false;
    }
    return true;
  }
  /**
   * Whether the given element first parent matches the selector parent.
   * @param element The element to check.
   * @param selector The selector to check against.
   * @param templateData The data to use for replace in selector values
   * @returns Whether the first parent matches the selector parent.
   */
  _isSingleParentMatch(element, selector, templateData) {
    if (isUndefined(selector)) {
      return false;
    }
    if (isNull(selector)) {
      return !element.parents || element.parents.length === 0;
    }
    const firstParent = element.parents?.[0];
    if (!firstParent) {
      return false;
    }
    return this._isParentMatch(firstParent, selector, templateData);
  }
  /**
   * Whether the element's full parent ancestor chain matches the `parents` array query.
   * @param element The element to check.
   * @param selector The normalized element selector.
   * @param templateData The data to use for replace in selector values.
   * @returns Whether the ancestor chain satisfies the query, or true if no `parents` selector is set.
   */
  _isParentsMatch(element, selector, templateData) {
    if (isUndefined(selector.parents)) {
      return true;
    }
    return this.isArrayQueryMatch(
      element.parents,
      selector.parents,
      (parent, parentSelector) => this._isParentMatch(parent, parentSelector, templateData)
    );
  }
  /**
   * Returns the parent selector that matches the element.
   * When the parent selector is an array, returns the first parent selector that matches (OR logic).
   * @param element The element to check.
   * @param selector The selector to check against.
   * @param templateData The data to use for replace in selector values
   * @returns The matching parent selector, null if the selector parent is null and the element has no parents, or undefined if there is no match.
   */
  _getParentSelectorMatching(element, selector, templateData) {
    if (isUndefined(selector.parent)) {
      return void 0;
    }
    if (isNull(selector.parent)) {
      if (element.parents.length === 0) {
        return selector.parent;
      }
      return void 0;
    }
    for (const parentSelector of selector.parent) {
      if (this._isSingleParentMatch(element, parentSelector, templateData)) {
        return parentSelector;
      }
    }
    return void 0;
  }
  /**
   * Determines if the isIgnored property of the element matches that in the selector.
   * @param element The element to check.
   * @param selector The selector to check against.
   * @returns True if the isIgnored properties match, false otherwise.
   */
  _isIgnoredMatch(element, selector) {
    return this.isObjectKeyBooleanMatch({
      object: element,
      selector,
      objectKey: "isIgnored",
      selectorKey: "isIgnored"
    });
  }
  /**
   * Determines if the isUnknown property of the element matches that in the selector.
   * @param element The element to check.
   * @param selector The selector to check against.
   * @returns True if the isUnknown properties match, false otherwise.
   */
  _isUnknownMatch(element, selector) {
    return this.isObjectKeyBooleanMatch({
      object: element,
      selector,
      objectKey: "isUnknown",
      selectorKey: "isUnknown"
    });
  }
  /**
   * Determines if the category of the element matches that in the selector.
   * @param element The element to check.
   * @param selector The selector to check against.
   * @param templateData The data to use for replace in selector value
   * @returns True if the categories match, false otherwise.
   */
  _isCategoryMatch(element, selector, templateData) {
    return this.isObjectKeyMicromatchMatch({
      object: element,
      selector,
      objectKey: "category",
      selectorKey: "category",
      selectorValue: selector.category,
      templateData
    });
  }
  /**
   * Determines if the filePath of the element matches that in the selector.
   * This is a legacy check for backward compatibility with legacy mode "file", where the element selector included filePath. It will be removed in future versions, so it shouldn't be used in new selectors.
   * @param element The element to check.
   * @param selector The selector to check against.
   * @param templateData The data to use for replace in selector value
   * @returns True if the filePaths match, false otherwise.
   */
  _isFilePathMatch(element, selector, templateData) {
    return this.isObjectKeyMicromatchMatch({
      object: element,
      selector,
      objectKey: "filePath",
      selectorKey: "filePath",
      selectorValue: selector.filePath,
      templateData
    });
  }
  /**
   * Returns the selector matching result for the given local or external element.
   * @param element The local or external element to check.
   * @param selector The selector to check against.
   * @param extraTemplateData Extra template data to use for matching.
   * @returns The selector matching result for the given element, or null if none matches.
   */
  _getSelectorMatching(element, selectorsData, extraTemplateData) {
    const templateData = {
      element,
      ...extraTemplateData
    };
    for (const selectorData of selectorsData) {
      if (!this._isSingleTypeMatch(element, selectorData, templateData) || !this._isTypeMatch(element, selectorData, templateData) || !this._isCategoryMatch(element, selectorData, templateData) || !this._isIgnoredMatch(element, selectorData) || !this._isUnknownMatch(element, selectorData) || !this._isPathMatch(element, selectorData, templateData) || !this._isFilePathMatch(element, selectorData, templateData) || !this._isFileInternalPathMatch(element, selectorData, templateData) || !this._isParentsMatch(element, selectorData, templateData) || !this._isCapturedValuesMatch(element, selectorData, templateData)) {
        continue;
      }
      if (isUndefined(selectorData.parent)) {
        return selectorData;
      }
      const matchingParentSelector = this._getParentSelectorMatching(
        element,
        selectorData,
        templateData
      );
      if (!isUndefined(matchingParentSelector)) {
        return {
          ...selectorData,
          parent: matchingParentSelector
        };
      }
    }
    return null;
  }
  /**
   * Returns the selector matching result for the given element, or null if none matches.
   * It omits checks in keys applying only to dependency between elements, such as relationship.
   * @param element The element to check.
   * @param selector The selector to check against.
   * @param options Extra options for matching, such as templates data, etc.
   * @returns The selector matching result for the given element, or null if none matches.
   */
  getSelectorMatching(element, selector, { extraTemplateData = {} } = {}) {
    if (!isElementDescription(element)) {
      throw new Error("Invalid element description");
    }
    const selectorsData = normalizeElementSelector(selector);
    return this._getSelectorMatching(element, selectorsData, extraTemplateData);
  }
  /**
   * Returns whether the given element matches the selector.
   * It omits checks in keys applying only to dependency between elements, such as relationship.
   * @param element The element to check.
   * @param selector The selector to check against.
   * @param options Extra options for matching, such as templates data, etc.
   * @returns Whether the element matches the selector properties applying to elements.
   */
  isElementMatch(element, selector, options) {
    const selectorMatching = this.getSelectorMatching(
      element,
      selector,
      options
    );
    return !isNullish(selectorMatching);
  }
};

// src/Matcher/File/FileSelectorHelpers.ts
function isFileSingleSelector(value) {
  return isObjectWithAnyOfProperties(value, ["categories"]) || extendsSingleSelector(value);
}
function isFileSelector(value) {
  return isFileSingleSelector(value) || isArray(value) && value.every(isFileSingleSelector);
}
function normalizeSingleFileSelector(selector) {
  if (isFileSingleSelector(selector)) {
    return { ...selector };
  }
  throw new Error("Invalid file selector");
}
function normalizeFileSelector(fileSelector) {
  if (isArray(fileSelector)) {
    return fileSelector.map((sel) => normalizeSingleFileSelector(sel));
  }
  return [normalizeSingleFileSelector(fileSelector)];
}

// src/Matcher/File/FileMatcher.ts
var FilesMatcher = class extends BaseElementsMatcher {
  /**
   * Creates a new FilesMatcher.
   * @param config Configuration options for the matcher.
   * @param micromatch Micromatch instance for matching.
   */
  constructor(config, micromatch2) {
    super(config, micromatch2);
  }
  /**
   * Whether the given file path matches the selector path.
   * @param file The file to check.
   * @param selector The selector to check against.
   * @param templateData The data to use for replace in selector value.
   * @returns Whether the file path matches the selector path.
   */
  _isPathMatch(file, selector, templateData) {
    return this.isObjectKeyMicromatchMatch({
      object: file,
      selector,
      objectKey: "path",
      selectorKey: "path",
      selectorValue: selector.path,
      templateData
    });
  }
  /**
   * Whether the given file categories match the selector categories.
   * File descriptions expose categories as an array, so it matches when any category matches the selector pattern.
   * @param file The file to check.
   * @param selector The selector to check against.
   * @param templateData The data to use for replace in selector value.
   * @returns Whether the file categories match the selector categories.
   */
  _isCategoriesMatch(file, selector, templateData) {
    const categoriesSelector = selector.categories;
    if (isNullish(categoriesSelector)) {
      return true;
    }
    if (isStringArrayQuery(categoriesSelector)) {
      return this.isStringArrayQueryMatch(
        file.categories,
        categoriesSelector,
        templateData
      );
    }
    return this.isTemplateMicromatchMatch(
      categoriesSelector,
      templateData,
      file.categories
    );
  }
  /**
   * Checks if a single captured values object matches the file.
   * @param capturedValues The captured values to check.
   * @param capturedSelector The captured values selector object to check against.
   * @param templateData The data to use for replace in selector values.
   * @returns True if all captured values in the selector match those in the file, false otherwise.
   */
  _checkCapturedValuesObject(capturedValues, capturedSelector, templateData) {
    if (!capturedValues) {
      return false;
    }
    for (const [key, pattern] of Object.entries(capturedSelector)) {
      const fileValue = capturedValues[key];
      if (!fileValue) {
        return false;
      }
      const renderedPattern = this.getRenderedTemplates(pattern, templateData);
      const filteredPattern = this.cleanMicromatchPattern(renderedPattern);
      if (!filteredPattern) {
        return false;
      }
      const isMatch = this.micromatch.isMatch(fileValue, filteredPattern);
      if (!isMatch) {
        return false;
      }
    }
    return true;
  }
  /**
   * Determines if the captured values of the file match those in the selector.
   * When the selector is an array, the file matches if it matches any of the array elements.
   * @param file The file to check.
   * @param selector The selector to check against.
   * @param templateData The data to use for replace in selector values.
   * @returns True if the captured values match, false otherwise.
   */
  _isCapturedValuesMatch(file, selector, templateData) {
    if (!selector.captured || isEmptyObject(selector.captured)) {
      return true;
    }
    if (isArray(selector.captured)) {
      if (selector.captured.length === 0) {
        return false;
      }
      return selector.captured.some(
        (capturedSelector) => this._checkCapturedValuesObject(
          file.captured,
          capturedSelector,
          templateData
        )
      );
    }
    return this._checkCapturedValuesObject(
      file.captured,
      selector.captured,
      templateData
    );
  }
  /**
   * Determines if the isIgnored property of the file matches that in the selector.
   * @param file The file to check.
   * @param selector The selector to check against.
   * @returns True if the isIgnored properties match, false otherwise.
   */
  _isIgnoredMatch(file, selector) {
    return this.isObjectKeyBooleanMatch({
      object: file,
      selector,
      objectKey: "isIgnored",
      selectorKey: "isIgnored"
    });
  }
  /**
   * Determines if the isUnknown property of the file matches that in the selector.
   * @param file The file to check.
   * @param selector The selector to check against.
   * @returns True if the isUnknown properties match, false otherwise.
   */
  _isUnknownMatch(file, selector) {
    return this.isObjectKeyBooleanMatch({
      object: file,
      selector,
      objectKey: "isUnknown",
      selectorKey: "isUnknown"
    });
  }
  /**
   * Returns the selector matching result for the given file.
   * @param file The file to check.
   * @param selectorsData The selectors to check against.
   * @param extraTemplateData Extra template data to use for matching.
   * @returns The selector matching result for the given file, or null if none matches.
   */
  _getSelectorMatching(file, selectorsData, extraTemplateData) {
    const templateData = {
      file,
      ...extraTemplateData
    };
    for (const selectorData of selectorsData) {
      if (!this._isIgnoredMatch(file, selectorData) || !this._isUnknownMatch(file, selectorData) || !this._isPathMatch(file, selectorData, templateData) || !this._isCategoriesMatch(file, selectorData, templateData) || !this._isCapturedValuesMatch(file, selectorData, templateData)) {
        continue;
      }
      return selectorData;
    }
    return null;
  }
  /**
   * Returns the selector matching result for the given file, or null if none matches.
   * @param file The file to check.
   * @param selector The selector to check against.
   * @param options Extra options for matching, such as templates data, etc.
   * @returns The selector matching result for the given file, or null if none matches.
   */
  getSelectorMatching(file, selector, { extraTemplateData = {} } = {}) {
    const selectorsData = normalizeFileSelector(selector);
    return this._getSelectorMatching(file, selectorsData, extraTemplateData);
  }
  /**
   * Returns whether the given file matches the selector.
   * @param file The file to check.
   * @param selector The selector to check against.
   * @param options Extra options for matching, such as templates data, etc.
   * @returns Whether the file matches the selector.
   */
  isFileMatch(file, selector, options) {
    const selectorMatching = this.getSelectorMatching(file, selector, options);
    return !isNullish(selectorMatching);
  }
};

// src/Matcher/Module/ModuleSelectorHelpers.ts
function isModuleSingleSelector(value) {
  return isObjectWithAnyOfProperties(value, [
    "origin",
    "source",
    "internalPath"
  ]);
}
function isModuleSelector(value) {
  return isModuleSingleSelector(value) || isArray(value) && value.every(isModuleSingleSelector);
}
function normalizeModuleSingleSelector(selector) {
  if (isModuleSingleSelector(selector)) {
    return selector;
  }
  throw new Error("Invalid module selector");
}
function normalizeModuleSelector(selector) {
  if (isModuleSingleSelector(selector)) {
    return [normalizeModuleSingleSelector(selector)];
  }
  if (isArray(selector)) {
    return selector.map(normalizeModuleSingleSelector);
  }
  throw new Error("Invalid module selector");
}

// src/Matcher/Module/ModuleMatcher.ts
var ModulesMatcher = class extends BaseElementsMatcher {
  /**
   * Creates a new ModulesMatcher.
   * @param config Configuration options for the matcher.
   * @param micromatch Micromatch instance for matching.
   */
  constructor(config, micromatch2) {
    super(config, micromatch2);
  }
  /**
   * Whether the given origin matches the selector.
   * @param origin The origin to check.
   * @param selector The selector to check against.
   * @param templateData The data to use for replace in selector value.
   * @returns Whether the origin matches the selector.
   */
  _isOriginMatch(origin, selector, templateData) {
    return this.isObjectKeyMicromatchMatch({
      object: origin,
      selector,
      objectKey: "origin",
      selectorKey: "origin",
      selectorValue: selector.origin,
      templateData
    });
  }
  /**
   * Whether the given module source matches the selector module.
   * @param origin The origin to check.
   * @param selector The selector to check against.
   * @param templateData The data to use for replace in selector value.
   * @returns Whether the module source matches the selector module.
   */
  _isSourceMatch(origin, selector, templateData) {
    return this.isObjectKeyMicromatchMatch({
      object: origin,
      selector,
      objectKey: "source",
      selectorKey: "source",
      selectorValue: selector.source,
      templateData
    });
  }
  /**
   * Whether the given module internal path matches the selector module.
   * @param origin The origin to check.
   * @param selector The selector to check against.
   * @param templateData The data to use for replace in selector value.
   * @returns Whether the module internal path matches the selector module.
   */
  _isInternalPathMatch(origin, selector, templateData) {
    return this.isObjectKeyMicromatchMatch({
      object: origin,
      selector,
      objectKey: "internalPath",
      selectorKey: "internalPath",
      selectorValue: selector.internalPath,
      templateData
    });
  }
  /**
   * Returns the selector matching result for the given module description, or null if none matches.
   * @param moduleDescription The module description to check.
   * @param selectorsData The selectors to check against.
   * @param extraTemplateData Extra template data to use for matching.
   * @returns The selector matching result for the given module description, or null if none matches.
   */
  _getSelectorMatching(moduleDescription, selectorsData, extraTemplateData) {
    const templateData = {
      origin: moduleDescription,
      ...extraTemplateData
    };
    for (const selectorData of selectorsData) {
      if (!this._isOriginMatch(moduleDescription, selectorData, templateData) || !this._isSourceMatch(moduleDescription, selectorData, templateData) || !this._isInternalPathMatch(
        moduleDescription,
        selectorData,
        templateData
      )) {
        continue;
      }
      return selectorData;
    }
    return null;
  }
  /**
   * Returns the selector matching result for the given module, or null if none matches.
   * @param moduleDescription The module to check.
   * @param selector The selector to check against.
   * @param options Extra options for matching, such as templates data, etc.
   * @returns The selector matching result for the given module, or null if none matches.
   */
  getSelectorMatching(moduleDescription, selector, { extraTemplateData = {} } = {}) {
    const selectorsData = normalizeModuleSelector(selector);
    return this._getSelectorMatching(
      moduleDescription,
      selectorsData,
      extraTemplateData
    );
  }
  /**
   * Returns whether the given module matches the selector.
   * @param moduleDescription The module to check.
   * @param selector The selector to check against.
   * @param options Extra options for matching, such as templates data, etc.
   * @returns Whether the module matches the selector.
   */
  isModuleMatch(moduleDescription, selector, options) {
    const selectorMatching = this.getSelectorMatching(
      moduleDescription,
      selector,
      options
    );
    return !isNull(selectorMatching);
  }
};

// src/Matcher/Entity/EntitySelectorHelpers.ts
function isLegacyEntitySingleSelector(selector) {
  if (isEntitySingleSelector(selector)) {
    return false;
  }
  return isBackwardCompatibleElementSingleSelector(selector);
}
function isLegacyEntitySelector(selector) {
  return isBackwardCompatibleElementSingleSelector(selector) || isArray(selector) && selector.some(isBackwardCompatibleElementSingleSelector);
}
function isEntitySingleSelector(value) {
  if (!isObjectWithAnyOfProperties(value, ["element", "file", "module"])) {
    return false;
  }
  const elementIsValid = !isObjectWithProperty(value, "element") || isElementSelector(value.element);
  const fileIsValid = !isObjectWithProperty(value, "file") || isFileSelector(value.file);
  const moduleIsValid = !isObjectWithProperty(value, "module") || isModuleSelector(value.module);
  return elementIsValid && fileIsValid && moduleIsValid;
}
function isEntitySelector(value) {
  return isEntitySingleSelector(value) || isArray(value) && value.every(isEntitySingleSelector);
}
function stripLeadingSlash(pattern) {
  const stripOne = (entry) => {
    if (entry === null) {
      return null;
    }
    return entry.startsWith("/") ? entry.slice(1) : entry;
  };
  if (isArray(pattern)) {
    return pattern.map(stripOne);
  }
  return stripOne(pattern);
}
function normalizeBackwardCompatibleElementSingleSelectorToEntitySingleSelector(selector) {
  let originalSelectorPathProperty = void 0;
  const toEntitySelectors = (sourceElementSelector, sourceOrigin) => {
    const selectors = [];
    const baseModule = isUndefined(sourceOrigin) ? void 0 : { origin: sourceOrigin };
    const elementEntitySelector = {};
    if (Object.keys(sourceElementSelector).length > 0) {
      elementEntitySelector.element = [sourceElementSelector];
      if (!isUndefined(originalSelectorPathProperty)) {
        elementEntitySelector.element[0].filePath = originalSelectorPathProperty;
      }
    }
    if (!isUndefined(baseModule)) {
      elementEntitySelector.module = [baseModule];
    }
    if (Object.keys(elementEntitySelector).length > 0) {
      selectors.push(elementEntitySelector);
    }
    return selectors;
  };
  if (isLegacySimpleElementSingleSelector(selector)) {
    return toEntitySelectors(
      normalizeLegacySimpleElementSingleSelector(selector)
    );
  }
  originalSelectorPathProperty = selector.path;
  if (!isLegacyElementSingleObjectSelector(selector) && isElementSingleSelector(selector)) {
    return [{ element: [normalizeSingleElementSelector(selector)] }];
  }
  const { origin, ...rest } = selector;
  const elementSelector = Object.keys(rest).length === 0 ? rest : normalizeSingleElementSelector(rest);
  const baseResult = toEntitySelectors(elementSelector, origin);
  const legacyInternalPath = selector.internalPath;
  if (!isUndefined(legacyInternalPath)) {
    const moduleFallbackEntry = {};
    const elementWithoutFileInternalPath = {
      ...elementSelector
    };
    delete elementWithoutFileInternalPath.fileInternalPath;
    if (Object.keys(elementWithoutFileInternalPath).length > 0) {
      moduleFallbackEntry.element = [elementWithoutFileInternalPath];
      if (!isUndefined(originalSelectorPathProperty)) {
        moduleFallbackEntry.element[0].filePath = originalSelectorPathProperty;
      }
    }
    moduleFallbackEntry.module = [
      {
        ...isUndefined(origin) ? {} : { origin },
        internalPath: stripLeadingSlash(legacyInternalPath)
      }
    ];
    baseResult.push(moduleFallbackEntry);
  }
  return baseResult;
}
function normalizeSingleEntitySelector(selector) {
  if (isEntitySingleSelector(selector)) {
    const baseSelector = {};
    if (!isUndefined(selector.element)) {
      baseSelector.element = normalizeElementSelector(selector.element);
    }
    if (!isUndefined(selector.file)) {
      baseSelector.file = normalizeFileSelector(selector.file);
    }
    if (!isUndefined(selector.module)) {
      baseSelector.module = normalizeModuleSelector(selector.module);
    }
    return [baseSelector];
  }
  if (isBackwardCompatibleElementSingleSelector(selector)) {
    return normalizeBackwardCompatibleElementSingleSelectorToEntitySingleSelector(
      selector
    );
  }
  throw new Error("Invalid entity selector");
}
function normalizeEntitySelector(entitySelector) {
  if (isLegacyEntitySingleSelector(entitySelector)) {
    return normalizeSingleEntitySelector(entitySelector);
  }
  if (isArray(entitySelector)) {
    return entitySelector.flatMap((sel) => normalizeSingleEntitySelector(sel));
  }
  return normalizeSingleEntitySelector(entitySelector);
}

// src/Matcher/Entity/EntityMatcher.ts
var EntitiesMatcher = class extends BaseElementsMatcher {
  /**
   * Elements matcher to use for matching elements within entities.
   */
  _elementsMatcher;
  _filesMatcher;
  _modulesMatcher;
  /**
   * Creates a new EntitiesMatcher.
   * @param elementsMatcher Elements matcher to use for matching elements within entities.
   * @param config Configuration options for the matcher.
   * @param micromatch Micromatch instance for matching.
   * @param globalCache Global cache instance.
   */
  constructor(elementsMatcher, filesMatcher, modulesMatcher, config, micromatch2) {
    super(config, micromatch2);
    this._elementsMatcher = elementsMatcher;
    this._filesMatcher = filesMatcher;
    this._modulesMatcher = modulesMatcher;
  }
  /**
   * Returns the selectors matching result for the given entity.
   * @param entity The entity description.
   * @param selector The entity selector normalized.
   * @param extraTemplateData The extra template data for selector values.
   * @returns The selectors matching result for the given entity.
   */
  _getSingleSelectorMatching(entity, selector, templateData) {
    const elementSelectorMatching = isUndefined(selector.element) ? void 0 : this._elementsMatcher.getSelectorMatching(
      entity.element,
      selector.element,
      {
        extraTemplateData: templateData
      }
    );
    const fileSelectorMatching = isUndefined(selector.file) ? void 0 : this._filesMatcher.getSelectorMatching(entity.file, selector.file, {
      extraTemplateData: templateData
    });
    const moduleSelectorMatching = isUndefined(selector.module) ? void 0 : this._modulesMatcher.getSelectorMatching(
      entity.module,
      selector.module,
      {
        extraTemplateData: templateData
      }
    );
    const selectorResult = {};
    if (elementSelectorMatching) {
      selectorResult.element = elementSelectorMatching;
    }
    if (fileSelectorMatching) {
      selectorResult.file = fileSelectorMatching;
    }
    if (moduleSelectorMatching) {
      selectorResult.module = moduleSelectorMatching;
    }
    const isMatch = Boolean(
      (selector.element ? elementSelectorMatching : true) && (selector.file ? fileSelectorMatching : true) && (selector.module ? moduleSelectorMatching : true)
    );
    return {
      selector: isMatch ? selectorResult : null,
      isMatch
    };
  }
  /**
   * Returns the selectors matching result for the given entity.
   * @param entity The entity to check.
   * @param selector The selector to check against.
   * @param options Extra options for matching, such as templates data, etc.
   * @returns The matching result for the entity against the selector.
   */
  getSelectorMatching(entity, selector, { extraTemplateData = {} } = {}) {
    const normalizedSelector = normalizeEntitySelector(selector);
    const elementExtraData = extraTemplateData.element || {};
    const fileExtraData = extraTemplateData.file || {};
    const moduleExtraData = extraTemplateData.module || {};
    const templateData = {
      ...extraTemplateData,
      element: { ...entity.element, ...elementExtraData },
      file: { ...entity.file, ...fileExtraData },
      module: { ...entity.module, ...moduleExtraData }
    };
    for (const selectorData of normalizedSelector) {
      const result = this._getSingleSelectorMatching(
        entity,
        selectorData,
        templateData
      );
      if (result.isMatch) {
        return result.selector;
      }
    }
    return null;
  }
  /**
   * Returns whether the given entity matches the selector.
   * @param entity The entity to check.
   * @param selector The selector to check against.
   * @param options Extra options for matching, such as templates data, etc.
   * @returns Whether the entity matches the selector properties.
   */
  isEntityMatch(entity, selector, options) {
    const matchResult = this.getSelectorMatching(entity, selector, options);
    return !isNull(matchResult);
  }
};

// src/Matcher/Dependency/DependencySelectorHelpers.ts
function isLegacyDependencyInfoSingleSelector(selector) {
  return isObjectWithProperty(selector, "module");
}
function isLegacyDependencyInfoSelector(selector) {
  return isLegacyDependencyInfoSingleSelector(selector) || isArray(selector) && selector.some(isLegacyDependencyInfoSingleSelector);
}
function isDependencyInfoSingleSelector(value) {
  return isObjectWithAnyOfProperties(value, [
    "kind",
    "relationship",
    "specifiers",
    "nodeKind",
    "source"
  ]);
}
function isDependencyInfoSelector(value) {
  return isDependencyInfoSingleSelector(value) || isArray(value) && value.every(isDependencyInfoSingleSelector);
}
function isBackwardCompatibleDependencyInfoSingleSelector(selector) {
  return isDependencyInfoSingleSelector(selector) || isLegacyDependencyInfoSingleSelector(selector);
}
function isBackwardCompatibleDependencyInfoSelector(selector) {
  return isBackwardCompatibleDependencyInfoSingleSelector(selector) || isArray(selector) && selector.every(isBackwardCompatibleDependencyInfoSingleSelector);
}
function normalizeLegacyDependencyInfoSingleSelector(selector) {
  const { module: dependencyModule, ...rest } = selector;
  return rest;
}
function isBaseDependencySingleSelector(selector) {
  return isObjectWithAnyOfProperties(selector, ["from", "to", "dependency"]);
}
function isLegacyDependencySingleSelector(selector) {
  if (!isBaseDependencySingleSelector(selector)) {
    return false;
  }
  if (selector.from && isLegacyEntitySelector(selector.from)) {
    return true;
  }
  if (selector.to && isLegacyEntitySelector(selector.to)) {
    return true;
  }
  if (selector.dependency && isLegacyDependencyInfoSelector(selector.dependency)) {
    return true;
  }
  return false;
}
function isLegacyDependencySelector(selector) {
  return isLegacyDependencySingleSelector(selector) || isArray(selector) && selector.some(isLegacyDependencySingleSelector);
}
function isDependencySingleSelector(value) {
  if (!isBaseDependencySingleSelector(value)) {
    return false;
  }
  const fromIsValid = !isObjectWithProperty(value, "from") || isEntitySelector(value.from);
  const toIsValid = !isObjectWithProperty(value, "to") || isEntitySelector(value.to);
  const dependencyIsValid = !isObjectWithProperty(value, "dependency") || isDependencyInfoSelector(value.dependency);
  return fromIsValid && toIsValid && dependencyIsValid;
}
function isDependencySelector(value) {
  return isDependencySingleSelector(value) || isArray(value) && value.every(isDependencySingleSelector);
}
function isBackwardCompatibleDependencySingleSelector(selector) {
  return isDependencySingleSelector(selector) || isLegacyDependencySingleSelector(selector);
}
function isBackwardCompatibleDependencySelector(selector) {
  return isBackwardCompatibleDependencySingleSelector(selector) || isArray(selector) && selector.every(isBackwardCompatibleDependencySingleSelector);
}
function addModuleToEntitySelectorNormalized(entitySelector, legacyDependencySelector) {
  let dependencyItems;
  if (isArray(legacyDependencySelector)) {
    dependencyItems = legacyDependencySelector;
  } else if (legacyDependencySelector === void 0) {
    dependencyItems = [];
  } else {
    dependencyItems = [legacyDependencySelector];
  }
  const legacyItems = dependencyItems.filter(
    isLegacyDependencyInfoSingleSelector
  );
  if (legacyItems.length === 0) {
    return entitySelector ?? [];
  }
  const baseEntitySelectors = entitySelector && entitySelector.length > 0 ? entitySelector : [{}];
  return legacyItems.flatMap(
    ({ module: modulePattern }) => baseEntitySelectors.map((single) => ({
      ...single,
      module: single.module ? single.module.map((moduleDescription) => ({
        ...moduleDescription,
        source: modulePattern
      })) : [{ source: modulePattern }]
    }))
  );
}
function normalizeSingleDependencyInfoSelector(selector) {
  if (isLegacyDependencyInfoSingleSelector(selector)) {
    return normalizeLegacyDependencyInfoSingleSelector(selector);
  }
  if (!isDependencyInfoSingleSelector(selector)) {
    throw new Error("Invalid dependency information selector");
  }
  return selector;
}
function normalizeDependencyInfoSelector(selector) {
  if (isBackwardCompatibleDependencyInfoSingleSelector(selector)) {
    return [normalizeSingleDependencyInfoSelector(selector)];
  } else if (isArray(selector)) {
    return selector.map(
      (singleSelector) => normalizeSingleDependencyInfoSelector(singleSelector)
    );
  }
  throw new Error("Invalid dependency information selector");
}
function normalizeLegacyDependencySingleSelector(selector) {
  const normalizedFrom = selector.from ? normalizeEntitySelector(selector.from) : void 0;
  const normalizedBaseTo = selector.to ? normalizeEntitySelector(selector.to) : void 0;
  let dependencyItems;
  if (isArray(selector.dependency)) {
    dependencyItems = selector.dependency;
  } else if (selector.dependency === void 0) {
    dependencyItems = [void 0];
  } else {
    dependencyItems = [selector.dependency];
  }
  return dependencyItems.map((dependencyItem) => {
    const normalizedSelector = {};
    if (normalizedFrom) {
      normalizedSelector.from = normalizedFrom;
    }
    const normalizedTo = addModuleToEntitySelectorNormalized(
      normalizedBaseTo,
      dependencyItem
    );
    if (normalizedTo.length > 0) {
      normalizedSelector.to = normalizedTo;
    }
    if (dependencyItem) {
      const normalizedDependency = normalizeDependencyInfoSelector(
        dependencyItem
      ).filter((item) => !isEmptyObject(item));
      if (normalizedDependency.length > 0) {
        normalizedSelector.dependency = normalizedDependency;
      }
    }
    return normalizedSelector;
  });
}
function normalizeSingleDependencySelector(selector) {
  if (isBackwardCompatibleDependencySingleSelector(selector)) {
    return normalizeLegacyDependencySingleSelector(selector);
  }
  throw new Error("Invalid dependency selector");
}
function normalizeDependencySelector(selector) {
  if (isBackwardCompatibleDependencySingleSelector(selector)) {
    return normalizeSingleDependencySelector(selector);
  } else if (isArray(selector)) {
    return selector.flatMap(
      (singleSelector) => normalizeSingleDependencySelector(singleSelector)
    );
  }
  throw new Error("Invalid dependency selector");
}

// src/Matcher/Dependency/DependencyMatcher.ts
var DependenciesMatcher = class extends BaseElementsMatcher {
  /**
   * Entities matcher to use for matching entities within dependencies.
   */
  _entitiesMatcher;
  /**
   * Creates a new DependenciesMatcher.
   * @param entitiesMatcher Entities matcher to use for matching entities within dependencies.
   * @param config Configuration options for the matcher.
   * @param micromatch Micromatch instance for matching.
   * @param globalCache Global cache instance.
   */
  constructor(entitiesMatcher, config, micromatch2) {
    super(config, micromatch2);
    this._entitiesMatcher = entitiesMatcher;
  }
  /**
   * Returns the selectors matching result for the given dependency.
   * @param dependency The dependency description.
   * @param selector The dependency selector normalized.
   * @param extraTemplateData The extra template data for selector values.
   * @returns The selectors matching result for the given dependency.
   */
  _getSingleSelectorMatching(dependency, selector, templateData) {
    const getDependencyMetadataSelectorMatching = () => {
      for (const dependencySelectorData of selector.dependency) {
        const dependencyPropertiesMatch = this._dependencyPropertiesMatch(
          dependency,
          dependencySelectorData,
          templateData
        );
        if (dependencyPropertiesMatch) {
          return dependencySelectorData;
        }
      }
      return null;
    };
    const fromSelectorMatching = isUndefined(selector.from) ? void 0 : this._entitiesMatcher.getSelectorMatching(
      dependency.from,
      selector.from,
      {
        extraTemplateData: templateData
      }
    );
    const toSelectorMatching = isUndefined(selector.to) ? void 0 : this._entitiesMatcher.getSelectorMatching(dependency.to, selector.to, {
      extraTemplateData: templateData
    });
    const dependencyMetadataSelectorMatching = isUndefined(selector.dependency) ? void 0 : getDependencyMetadataSelectorMatching();
    const selectorResult = {};
    if (fromSelectorMatching) {
      selectorResult.from = fromSelectorMatching;
    }
    if (toSelectorMatching) {
      selectorResult.to = toSelectorMatching;
    }
    if (dependencyMetadataSelectorMatching) {
      selectorResult.dependency = dependencyMetadataSelectorMatching;
    }
    const isMatch = Boolean(
      (selector.from ? fromSelectorMatching : true) && (selector.to ? toSelectorMatching : true) && (selector.dependency ? dependencyMetadataSelectorMatching : true)
    );
    return {
      selector: isMatch ? selectorResult : null,
      isMatch
    };
  }
  /**
   * Determines if the dependency relationship matches the selector.
   * @param dependency The dependency description.
   * @param selector The data of an element selector.
   * @returns Whether the dependency relationship matches the selector.
   */
  _relationshipFromMatches(selector, relationship, templateData) {
    if (!selector.relationship?.from) {
      return true;
    }
    return this.isTemplateMicromatchMatch(
      selector.relationship.from,
      templateData,
      relationship
    );
  }
  /**
   * Determines if the dependency origin relationship matches the selector.
   * @param selector The dependency selector data.
   * @param relationship The relationship from origin element to target element.
   * @param templateData The template data for rendering selector values.
   * @returns Whether the dependency origin relationship matches.
   */
  _relationshipToMatches(selector, relationship, templateData) {
    if (!selector.relationship?.to) {
      return true;
    }
    return this.isTemplateMicromatchMatch(
      selector.relationship.to,
      templateData,
      relationship
    );
  }
  /**
   * Determines if the selector matches an specific kind
   * @param selector The dependency selector data
   * @param kind Kind to check
   * @param templateData The template data for rendering selector values
   * @returns Whether the selector matches the kind
   */
  _kindMatches(selector, kind, templateData) {
    if (!selector.kind) {
      return true;
    }
    return this.isTemplateMicromatchMatch(selector.kind, templateData, kind);
  }
  /**
   * Determines if the selector matches some of the specifiers
   * @param selector The dependency selector data
   * @param specifiers Specifiers to check
   * @param templateData The template data for rendering selector values
   * @returns Whether the selector matches some of the specifiers
   */
  _specifierMatches(selector, specifiers, templateData) {
    if (!selector.specifiers) {
      return true;
    }
    return this.isTemplateMicromatchMatch(
      selector.specifiers,
      templateData,
      specifiers
    );
  }
  /**
   * Determines if the selector matches the nodeKind
   * @param selector The dependency selector data
   * @param nodeKind The nodeKind to check
   * @param templateData The template data for rendering selector values
   * @returns Whether the selector matches the nodeKind
   */
  _nodeKindMatches(selector, nodeKind, templateData) {
    if (!selector.nodeKind) {
      return true;
    }
    return this.isTemplateMicromatchMatch(
      selector.nodeKind,
      templateData,
      nodeKind
    );
  }
  /**
   * Determines if the dependency description matches the selector for 'to'.
   * @param dependency The dependency description.
   * @param toSelector The selector for 'to' elements.
   * @param templateData The template data for rendering selector values
   * @returns Whether the dependency properties match the selector for 'to'.
   */
  _sourceMatches(selector, source, templateData) {
    if (!selector.source) {
      return true;
    }
    return this.isTemplateMicromatchMatch(
      selector.source,
      templateData,
      source
    );
  }
  /**
   * Determines if the dependency description matches the selector for dependency metadata.
   * @param dependency The dependency description.
   * @param selectorData The selector for dependency metadata.
   * @param templateData The template data for rendering selector values
   * @returns Whether the dependency properties match the selector.
   */
  _dependencyPropertiesMatch(dependency, selectorData, templateData) {
    const dependencyInfo = dependency.dependency;
    const relationshipFrom = dependencyInfo.relationship.from;
    const relationshipTo = dependencyInfo.relationship.to;
    const kind = dependencyInfo.kind;
    const nodeKind = dependencyInfo.nodeKind;
    const specifiers = dependencyInfo.specifiers;
    const source = dependencyInfo.source;
    return this._kindMatches(selectorData, kind, templateData) && this._nodeKindMatches(selectorData, nodeKind, templateData) && this._sourceMatches(selectorData, source, templateData) && this._relationshipFromMatches(
      selectorData,
      relationshipFrom,
      templateData
    ) && this._relationshipToMatches(selectorData, relationshipTo, templateData) && this._specifierMatches(selectorData, specifiers, templateData);
  }
  /**
   * Returns the selectors matching result for the given dependency.
   * @param dependency The dependency to check.
   * @param selector The selector to check against.
   * @param options Extra options for matching, such as templates data, etc.
   * @returns The matching result for the dependency against the selector.
   */
  getSelectorMatching(dependency, selector, { extraTemplateData = {} } = {}) {
    const normalizedSelector = normalizeDependencySelector(selector);
    const fromExtraData = extraTemplateData.from || {};
    const toExtraData = extraTemplateData.to || {};
    const templateData = {
      ...extraTemplateData,
      from: {
        ...dependency.from,
        ...fromExtraData
      },
      to: {
        ...dependency.to,
        ...toExtraData
      },
      dependency: dependency.dependency
    };
    for (const singleSelector of normalizedSelector) {
      const matchResult = this._getSingleSelectorMatching(
        dependency,
        singleSelector,
        templateData
      );
      if (matchResult.isMatch) {
        return matchResult.selector;
      }
    }
    return null;
  }
  /**
   * Returns whether the given dependency matches the selector.
   * @param dependency The dependency to check.
   * @param selector The selector to check against.
   * @param options Extra options for matching, such as templates data, etc.
   * @returns Whether the dependency matches the selector properties.
   */
  isDependencyMatch(dependency, selector, options) {
    const matchResult = this.getSelectorMatching(dependency, selector, options);
    return !isNull(matchResult);
  }
};

// src/Legacy/TemplateHelpers.ts
function getLegacyElementSelectorTemplateData(element, moduleDescription) {
  const parents = isArray(element.parents) ? element.parents.map((parent) => ({
    ...parent,
    type: parent.types?.[0] ?? null,
    elementPath: parent.path
  })) : element.parents;
  return {
    ...element,
    type: element.types?.[0] ?? null,
    elementPath: element.path,
    internalPath: moduleDescription?.internalPath || element.fileInternalPath,
    parents,
    ...isUndefined(moduleDescription?.origin) ? {} : { origin: moduleDescription?.origin }
  };
}
function getLegacyEntitySelectorExtraTemplateData(entity) {
  return {
    element: getLegacyElementSelectorTemplateData(
      entity.element,
      entity.module
    ),
    file: entity.file,
    origin: entity.module
  };
}
function getLegacyElementSelectorExtraTemplateData(element, moduleDescription) {
  return {
    element: getLegacyElementSelectorTemplateData(element, moduleDescription)
  };
}
function getLegacyDependencySelectorExtraTemplateData(dependency, extraTemplateData) {
  const optionsFromExtraTemplateData = isObject(extraTemplateData?.from) ? extraTemplateData?.from : {};
  const optionsToExtraTemplateData = isObject(extraTemplateData?.to) ? extraTemplateData?.to : {};
  const dependencyExtraTemplateData = isObject(extraTemplateData?.dependency) ? extraTemplateData?.dependency : {};
  const fromFile = dependency.from.file;
  const fromElement = getLegacyElementSelectorTemplateData(
    dependency.from.element,
    dependency.from.module
  );
  const toFile = dependency.to.file;
  const toElement = getLegacyElementSelectorTemplateData(
    dependency.to.element,
    dependency.to.module
  );
  return {
    ...extraTemplateData,
    from: {
      ...fromElement,
      ...dependency.from,
      element: fromElement,
      file: fromFile,
      ...optionsFromExtraTemplateData
    },
    to: {
      ...toElement,
      ...dependency.to,
      element: toElement,
      file: toFile,
      ...optionsToExtraTemplateData
    },
    dependency: {
      ...dependency.dependency,
      origin: dependency.to.module.origin,
      ...dependencyExtraTemplateData
    }
  };
}

// src/Matcher/Matcher.ts
var Matcher = class {
  _elementsMatcher;
  _filesMatcher;
  _entitiesMatcher;
  _modulesMatcher;
  _dependenciesMatcher;
  _originalDescriptors;
  _descriptorOptions;
  _micromatch;
  _descriptors;
  /**
   * Constructor for the Matcher class.
   * @param options The options to configure the Matcher instance, including descriptors, matchers for elements and dependencies, and micromatch instance for pattern matching.
   * @param options.descriptors The descriptors configuration to use for describing elements and dependencies.
   * @param options.options.descriptors The normalized descriptor options to use for describing elements and dependencies.
   * @param options.options.matchers The matchers configuration for elements and dependencies.
   * @param options.micromatch The micromatch instance to use for pattern matching.
   */
  constructor({
    descriptors,
    options: { descriptors: descriptorOptions, matchers: matchersOptions },
    micromatch: micromatch2
  }) {
    this._originalDescriptors = descriptors;
    this._descriptorOptions = descriptorOptions;
    this._micromatch = micromatch2;
    this._descriptors = new Descriptors(
      this._originalDescriptors,
      this._descriptorOptions,
      this._micromatch
    );
    this._elementsMatcher = new ElementsMatcher(matchersOptions, micromatch2);
    this._filesMatcher = new FilesMatcher(matchersOptions, micromatch2);
    this._modulesMatcher = new ModulesMatcher(matchersOptions, micromatch2);
    this._entitiesMatcher = new EntitiesMatcher(
      this._elementsMatcher,
      this._filesMatcher,
      this._modulesMatcher,
      matchersOptions,
      micromatch2
    );
    this._dependenciesMatcher = new DependenciesMatcher(
      this._entitiesMatcher,
      matchersOptions,
      micromatch2
    );
  }
  /**
   * Describes an element given its file path.
   * @param filePath The path of the file to describe.
   * @returns The description of the element.
   */
  describeElement(filePath) {
    return this._descriptors.describeElement(filePath);
  }
  /**
   * Describes elements in a dependency relationship, and provides additional information about the dependency itself.
   * @param options The options for describing the elements and the dependency details.
   * @returns The description of the dependency between the elements.
   */
  describeDependency(options) {
    return this._descriptors.describeDependency(options);
  }
  /**
   * Describes an entity given its file path, including both the file, element and origin description.
   * @param filePath The path of the file to describe.
   * @param source The optional dependency source (e.g., the importer file path) to use for describing the origin of the entity being imported.
   * @returns The description of the entity.
   */
  describeEntity(filePath, source) {
    return this._descriptors.describeEntity(filePath, source);
  }
  /**
   * Describes the module of a file given its path and the path of the importer file.
   * @param filePath The path of the file to describe.
   * @param source The optional dependency source (e.g., the importer file path) to use for describing the module of the entity being imported.
   * @returns The description of the file's module.
   */
  describeModule(filePath, source) {
    return this._descriptors.describeModule(filePath, source);
  }
  /**
   * Returns the description of a file given its path.
   * @param filePath The path of the file to describe.
   * @returns The description of the file.
   */
  describeFile(filePath) {
    return this._descriptors.describeFile(filePath);
  }
  /**
   * Determines if an element matches a given selector.
   * @param filePath The file path of the element
   * @param selector The selector to match against
   * @param options Extra matcher options
   * @returns True if the element matches the selector, false otherwise
   */
  isElementMatch(filePath, selector, options) {
    const description = this._descriptors.describeElement(filePath);
    const moduleDescription = this._descriptors.describeModule(filePath);
    const matcherOptions = {
      ...options,
      extraTemplateData: {
        ...getLegacyElementSelectorExtraTemplateData(
          description,
          moduleDescription
        ),
        ...options?.extraTemplateData
      }
    };
    return this._elementsMatcher.isElementMatch(
      description,
      selector,
      matcherOptions
    );
  }
  /**
   * Determines if a dependency matches a given selector.
   * @param dependencyData The data describing the dependency
   * @param selector The selector to match against
   * @param options Extra matcher options
   * @returns True if the dependency matches the selector, false otherwise
   */
  isDependencyMatch(dependencyData, selector, options) {
    const description = this._descriptors.describeDependency(dependencyData);
    const matcherOptions = {
      ...options,
      extraTemplateData: getLegacyDependencySelectorExtraTemplateData(
        description,
        options?.extraTemplateData
      )
    };
    return this._dependenciesMatcher.isDependencyMatch(
      description,
      selector,
      matcherOptions
    );
  }
  /**
   * Determines if an entity matches a given selector.
   * @param filePath The file path of the entity
   * @param selector The selector to match against
   * @param options Extra matcher options
   * @returns True if the entity matches the selector, false otherwise
   */
  isEntityMatch(filePath, selector, options) {
    const description = this._descriptors.describeEntity(
      filePath,
      options?.source
    );
    const matcherOptions = {
      ...options,
      extraTemplateData: {
        ...getLegacyEntitySelectorExtraTemplateData(description),
        ...options?.extraTemplateData
      }
    };
    return this._entitiesMatcher.isEntityMatch(
      description,
      selector,
      matcherOptions
    );
  }
  /**
   * Determines if an origin matches a given selector.
   * @param filePath The file path of the origin
   * @param selector The selector to match against
   * @param options Extra matcher options
   * @returns True if the module matches the selector, false otherwise
   */
  isModuleMatch(filePath, selector, options) {
    const description = this._descriptors.describeModule(
      filePath,
      options?.source
    );
    return this._modulesMatcher.isModuleMatch(description, selector, options);
  }
  /**
   * Determines if a file matches a given selector.
   * @param filePath The file path to check
   * @param selector The selector to match against
   * @param options Extra matcher options
   * @returns True if the file matches the selector, false otherwise
   */
  isFileMatch(filePath, selector, options) {
    const description = this._descriptors.describeFile(filePath);
    return this._filesMatcher.isFileMatch(description, selector, options);
  }
  /**
   * Determines if an entity matches a given selector.
   * @param filePath The file path of the entity
   * @param selector The selector to match against
   * @param options Extra matcher options
   * @returns True if the entity matches the selector, false otherwise
   */
  getEntitySelectorMatching(filePath, selector, options) {
    const description = this._descriptors.describeEntity(
      filePath,
      options?.source
    );
    const matcherOptions = {
      ...options,
      extraTemplateData: {
        ...getLegacyEntitySelectorExtraTemplateData(description),
        ...options?.extraTemplateData
      }
    };
    return this._entitiesMatcher.getSelectorMatching(
      description,
      selector,
      matcherOptions
    );
  }
  /**
   * Determines the selector matching for an element.
   * @param filePath The file path of the element
   * @param selector The selectors to match against
   * @param options Extra options for matching
   * @returns The matching selector data or null if no match is found
   */
  getElementSelectorMatching(filePath, selector, options) {
    const description = this._descriptors.describeElement(filePath);
    const moduleDescription = this._descriptors.describeModule(filePath);
    const matcherOptions = {
      ...options,
      extraTemplateData: {
        ...getLegacyElementSelectorExtraTemplateData(
          description,
          moduleDescription
        ),
        ...options?.extraTemplateData
      }
    };
    return this._elementsMatcher.getSelectorMatching(
      description,
      selector,
      matcherOptions
    );
  }
  /**
   * Determines the selector matching for a dependency.
   * @param dependencyData The data describing the dependency
   * @param selector The selectors to match against
   * @param options Extra options for matching
   * @returns The matching dependency result or null if no match is found
   */
  getDependencySelectorMatching(dependencyData, selector, options) {
    const description = this._descriptors.describeDependency(dependencyData);
    const matcherOptions = {
      ...options,
      extraTemplateData: getLegacyDependencySelectorExtraTemplateData(
        description,
        options?.extraTemplateData
      )
    };
    return this._dependenciesMatcher.getSelectorMatching(
      description,
      selector,
      matcherOptions
    );
  }
  /**
   * Determines the selector matching for an origin.
   * @param filePath The file path of the origin
   * @param selector The selector to match against
   * @param options Extra options for matching
   * @returns The matching module result or null if no match is found
   */
  getModuleSelectorMatching(filePath, selector, options) {
    const description = this._descriptors.describeModule(
      filePath,
      options?.source
    );
    return this._modulesMatcher.getSelectorMatching(
      description,
      selector,
      options
    );
  }
  /**
   * Determines the selector matching for a file.
   * @param filePath The file path to check
   * @param selector The selector to match against
   * @param options Extra options for matching
   * @returns The matching file selector or null if no match is found
   */
  getFileSelectorMatching(filePath, selector, options) {
    const description = this._descriptors.describeFile(filePath);
    return this._filesMatcher.getSelectorMatching(
      description,
      selector,
      options
    );
  }
  /**
   * Returns the first selector matching result for the given entity and selector.
   * @param description The entity description to check.
   * @param selector The selector to check against.
   * @param options Extra options for matching, such as templates data, etc.
   * @returns The first selector matching result for the given entity and selector, or null if no match is found.
   */
  getEntitySelectorMatchingDescription(description, selector, options) {
    const matcherOptions = {
      ...options,
      extraTemplateData: {
        ...getLegacyEntitySelectorExtraTemplateData(description),
        ...options?.extraTemplateData
      }
    };
    return this._entitiesMatcher.getSelectorMatching(
      description,
      selector,
      matcherOptions
    );
  }
  /**
   * Returns the selectors matching result for the given element or dependency description.
   * @param description The element or dependency  description to check.
   * @param selector The selector to check against.
   * @param options Extra options for matching, such as templates data, etc.
   * @returns The selectors matching result for the given description, and whether it matches or not.
   */
  getDependencySelectorMatchingDescription(description, selector, options) {
    const matcherOptions = {
      ...options,
      extraTemplateData: getLegacyDependencySelectorExtraTemplateData(
        description,
        options?.extraTemplateData
      )
    };
    return this._dependenciesMatcher.getSelectorMatching(
      description,
      selector,
      matcherOptions
    );
  }
  /**
   * Returns the first element selector matching result for the given element description.
   * @param description The element description to check.
   * @param selector The selector to check against.
   * @param options Extra options for matching, such as templates data, etc.
   * @returns The first matching selector result for the given description, or null if no match is found.
   */
  getElementSelectorMatchingDescription(description, selector, options) {
    const matcherOptions = {
      ...options,
      extraTemplateData: {
        ...getLegacyElementSelectorExtraTemplateData(description),
        ...options?.extraTemplateData
      }
    };
    return this._elementsMatcher.getSelectorMatching(
      description,
      selector,
      matcherOptions
    );
  }
  getModuleSelectorMatchingDescription(description, selector, options) {
    return this._modulesMatcher.getSelectorMatching(
      description,
      selector,
      options
    );
  }
  /**
   * Returns the first file selector matching result for the given file description.
   * @param description The file description to check.
   * @param selector The selector to check against.
   * @param options Extra options for matching, such as templates data, etc.
   * @returns The first matching selector result for the given description, or null if no match is found.
   */
  getFileSelectorMatchingDescription(description, selector, options) {
    return this._filesMatcher.getSelectorMatching(
      description,
      selector,
      options
    );
  }
  /**
   * Clears all caches.
   */
  clearCache() {
    this._descriptors.clearCache();
  }
  /**
   * Serializes the descriptors matchers cache to a plain object.
   * @returns The serialized cache
   */
  serializeCache() {
    return {
      descriptors: this._descriptors.serializeCache()
    };
  }
  /**
   * Sets the descriptors matchers cache from a serialized object.
   * @param serializedCache The serialized cache
   */
  setCacheFromSerialized(serializedCache) {
    this._descriptors.setCacheFromSerialized(serializedCache.descriptors);
  }
};

// src/MatchersCache.ts
var MatchersCache = class extends CacheManager {
  /**
   * Calculates a hash for the base properties of a descriptor to be used in the cache key.
   * @param descriptor The descriptor to calculate the hash for.
   * @returns A string hash representing the base properties of the descriptor.
   */
  _getBaseDescriptorsHash(descriptor) {
    const captureKey = descriptor.capture ? descriptor.capture.join(",") : "no-capture";
    return `${descriptor.pattern}|${captureKey}`;
  }
  /**
   * Calculates a hash for the element descriptors to be used in the cache key.
   * @param elementDescriptors The element descriptors to calculate the hash for.
   * @returns A string hash representing the element descriptors.
   */
  _getElementDescriptorsHash(elementDescriptors) {
    return elementDescriptors.map((descriptor) => {
      const baseCaptureKey = descriptor.baseCapture ? descriptor.baseCapture.join(",") : "no-base-capture";
      return `${this._getBaseDescriptorsHash(descriptor)}|${descriptor.type}|${descriptor.category}|${descriptor.mode}|${descriptor.basePattern}|${baseCaptureKey}|${descriptor.partialMatch}|${descriptor.stopMatching}|${descriptor.exclusive}`;
    }).join(",");
  }
  /**
   * Calculates a hash for the file descriptors to be used in the cache key.
   * @param fileDescriptors The file descriptors to calculate the hash for.
   * @returns A string hash representing the file descriptors.
   */
  _getFileDescriptorsHash(fileDescriptors) {
    return fileDescriptors.map(
      (descriptor) => `${this._getBaseDescriptorsHash(descriptor)}|${descriptor.category}|${descriptor.stopMatching}|${descriptor.exclusive}`
    ).join(",");
  }
  /**
   * Generates a unique key based on the configuration options and element descriptors
   * @param params The configuration and element descriptors
   * @returns A unique string key
   */
  generateKey({
    config,
    descriptors
  }) {
    const configHash = `${config.legacyTemplates}|${config.includePaths}|${config.ignorePaths}|${config.cache}|${config.rootPath}|${config.flagAsExternal.inNodeModules}|${config.flagAsExternal.unresolvableAlias}|${config.flagAsExternal.outsideRootPath}|${config.flagAsExternal.customSourcePatterns.join(",")}`;
    const elementDescriptorsHash = this._getElementDescriptorsHash(
      descriptors.elements || []
    );
    const elementsSingleMatch = resolveElementsSingleMatch(descriptors) ? "true" : "false";
    const filesSingleMatch = descriptors.filesSingleMatch ? "true" : "false";
    const fileDescriptorsHash = this._getFileDescriptorsHash(
      descriptors.files || []
    );
    return `|:config:|${configHash}|:elements:|${elementDescriptorsHash}|:elementsSingleMatch:|${elementsSingleMatch}|:files:|${fileDescriptorsHash}|:filesSingleMatch:|${filesSingleMatch}`;
  }
};

// src/Elements.ts
var Elements = class {
  /** The global configuration options for Elements. Can be overridden when getting a descriptor */
  _globalConfigOptions;
  /** Cache manager for Matcher instances, unique for each different configuration */
  _matchersCache = new MatchersCache();
  /** Micromatch instances for pattern matching */
  _micromatchWithCache = new Micromatch(true);
  _micromatchWithoutCache = new Micromatch(false);
  /**
   * Creates a new Elements instance
   * @param configOptions The global configuration options for Elements. Can be overridden when getting a descriptor.
   */
  constructor(configOptions) {
    const globalConfig = new Config(configOptions);
    this._globalConfigOptions = globalConfig.options;
  }
  /**
   * Returns a serialized representation of the current state of the cache.
   * @returns A serialized representation of the cache.
   */
  serializeCache() {
    const matchersCache = Array.from(
      this._matchersCache.getAll().entries()
    ).reduce(
      (acc, [key, cache]) => {
        acc[key] = {
          config: cache.config,
          descriptors: cache.descriptors,
          cache: cache.matcher.serializeCache()
        };
        return acc;
      },
      {}
    );
    const micromatchCache = this._micromatchWithCache.serializeCache();
    return {
      matchers: matchersCache,
      micromatch: micromatchCache
    };
  }
  /**
   * Sets the Elements cache from a serialized representation.
   * @param serializedCache The serialized cache to set.
   */
  setCacheFromSerialized(serializedCache) {
    this._micromatchWithCache.setFromSerialized(serializedCache.micromatch);
    for (const key in serializedCache.matchers) {
      const matcher = this.getMatcher(
        serializedCache.matchers[key].descriptors,
        serializedCache.matchers[key].config
      );
      matcher.setCacheFromSerialized(serializedCache.matchers[key].cache);
      this._matchersCache.set(key, {
        config: serializedCache.matchers[key].config,
        descriptors: serializedCache.matchers[key].descriptors,
        matcher
      });
    }
  }
  /**
   * Clears cache
   */
  clearCache() {
    for (const { matcher } of this._matchersCache.getAll().values()) {
      matcher.clearCache();
    }
    this._matchersCache.clear();
    this._micromatchWithCache.clearCache();
  }
  /**
   * Gets a Matcher instance for the given configuration options.
   * It uses caching to return the same instance for the same configuration options. If no options are provided, the global configuration options are used.
   * @param descriptors The descriptors to use.
   * @param config Optional configuration options to override the global ones.
   * @returns A matcher instance, unique for each different configuration.
   */
  getMatcher(descriptors, config) {
    const optionsToUse = config || this._globalConfigOptions;
    const configInstance = new Config(optionsToUse);
    const cacheIsEnabled = configInstance.cache;
    const configOptionsNormalized = configInstance.options;
    const descriptorNormalizedOptions = configInstance.descriptorOptions;
    const matchersNormalizedOptions = configInstance.matchersOptions;
    const cacheKey = this._matchersCache.getKey({
      config: configOptionsNormalized,
      descriptors
    });
    if (this._matchersCache.has(cacheKey)) {
      return this._matchersCache.get(cacheKey).matcher;
    }
    const micromatch2 = cacheIsEnabled ? this._micromatchWithCache : this._micromatchWithoutCache;
    const matcher = new Matcher({
      descriptors,
      micromatch: micromatch2,
      options: {
        descriptors: descriptorNormalizedOptions,
        matchers: matchersNormalizedOptions
      }
    });
    this._matchersCache.set(cacheKey, {
      config: configOptionsNormalized,
      descriptors,
      matcher
    });
    return matcher;
  }
};
export {
  ARRAY_QUERY_KEYS,
  BaseElementsMatcher,
  DEPENDENCY_KINDS_MAP,
  DEPENDENCY_KINDS_SET,
  DEPENDENCY_KIND_TYPE,
  DEPENDENCY_KIND_TYPEOF,
  DEPENDENCY_KIND_VALUE,
  DEPENDENCY_RELATIONSHIPS_INVERTED_MAP,
  DEPENDENCY_RELATIONSHIPS_MAP,
  DEPENDENCY_RELATIONSHIPS_SET,
  DependenciesDescriptor,
  DependenciesMatcher,
  Descriptors,
  ELEMENT_DESCRIPTOR_MODES_MAP,
  Elements,
  ElementsDescriptor,
  ElementsMatcher,
  EntitiesDescriptor,
  EntitiesMatcher,
  FilesDescriptor,
  FilesMatcher,
  Matcher,
  Micromatch,
  ModulesDescriptor,
  ModulesMatcher,
  ORIGINS_MAP,
  ORIGINS_SET,
  expandStringArrayQuery,
  extendsSingleSelector,
  isArrayQuery,
  isBackwardCompatibleDependencyInfoSelector,
  isBackwardCompatibleDependencyInfoSingleSelector,
  isBackwardCompatibleDependencySelector,
  isBackwardCompatibleDependencySingleSelector,
  isBackwardCompatibleElementSelector,
  isBackwardCompatibleElementSingleSelector,
  isBaseDependencySingleSelector,
  isCapturedValuesSelector,
  isCapturedValuesSingleSelector,
  isDependencyDescription,
  isDependencyInfoSelector,
  isDependencyInfoSingleSelector,
  isDependencyKind,
  isDependencySelector,
  isDependencySingleSelector,
  isDependencyWithInternalRelationship,
  isElementDescription,
  isElementDescriptor,
  isElementSelector,
  isElementSingleSelector,
  isEntityDescription,
  isEntitySelector,
  isEntitySingleSelector,
  isExpandItem,
  isFileDescription,
  isFileDescriptor,
  isFileSelector,
  isFileSingleSelector,
  isIgnoredElementDescription,
  isIgnoredFileDescription,
  isKnownElementDescription,
  isKnownFileDescription,
  isLegacyDependencyInfoSelector,
  isLegacyDependencyInfoSingleSelector,
  isLegacyDependencySelector,
  isLegacyDependencySingleSelector,
  isLegacyElementSelector,
  isLegacyElementSingleObjectSelector,
  isLegacyElementSingleSelector,
  isLegacyEntitySelector,
  isLegacyEntitySingleSelector,
  isLegacyParentElementSingleSelector,
  isLegacySimpleElementSelector,
  isLegacySimpleElementSingleSelector,
  isLegacySimpleElementSingleSelectorByType,
  isLegacySimpleElementSingleSelectorByTypeWithOptions,
  isModuleSelector,
  isModuleSingleSelector,
  isOriginDescription,
  isStringArrayQuery,
  isUnknownElementDescription,
  isUnknownFileDescription,
  normalizeDependencyInfoSelector,
  normalizeDependencySelector,
  normalizeElementSelector,
  normalizeEntitySelector,
  normalizeFileSelector,
  normalizeLegacyDependencyInfoSingleSelector,
  normalizeLegacyDependencySingleSelector,
  normalizeLegacyElementSingleObjectSelector,
  normalizeLegacyElementSingleSelector,
  normalizeLegacyParentElementSelectors,
  normalizeLegacySimpleElementSingleSelector,
  normalizeModuleSelector,
  normalizeModuleSingleSelector,
  normalizeParentElementSelector,
  normalizeParentInElementSingleSelector,
  normalizeSingleDependencyInfoSelector,
  normalizeSingleDependencySelector,
  normalizeSingleElementSelector,
  normalizeSingleEntitySelector,
  normalizeSingleFileSelector,
  resolveExpandItem
};
//# sourceMappingURL=index.browser.mjs.map