/**
 * Determines if the provided object is an array.
 * @param object The object to check.
 * @returns True if the object is an array, false otherwise.
 */
export declare function isArray(object: unknown): object is unknown[];
/**
 * Determines if the provided object is a string.
 * @param object The object to check.
 * @returns True if the object is a string, false otherwise.
 */
export declare function isString(object: unknown): object is string;
/**
 * Determines if the provided object is a boolean.
 * @param object The object to check.
 * @returns True if the object is a boolean, false otherwise.
 */
export declare function isBoolean(object: unknown): object is boolean;
/**
 * Determines if the provided object is null.
 * @param object The object to check.
 * @returns True if the object is null, false otherwise.
 */
export declare function isNull(object: unknown): object is null;
/**
 * Determines if the provided object is a non-null object (but not an array).
 * @param object The object to check.
 * @returns True if the object is a non-null object, false otherwise.
 */
export declare function isObject(object: unknown): object is Record<string, unknown>;
/**
 * Determines if the provided object is undefined.
 * @param object The object to check.
 * @returns True if the object is undefined, false otherwise.
 */
export declare function isUndefined(object: unknown): object is undefined;
/**
 * Determines if the provided object is null or undefined.
 * @param object The object to check.
 * @returns True if the object is null or undefined, false otherwise.
 */
export declare function isNullish(object: unknown): object is null | undefined;
/**
 * Returns the value as an array if it is an array, or null otherwise.
 * @param value The value to check.
 * @returns The value as an array or null.
 */
export declare function getArrayOrNull<T>(value: unknown): T[] | null;
