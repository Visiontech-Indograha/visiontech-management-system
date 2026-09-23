import type { Config } from "../Shared";
/**
 * Legacy strict configuration for eslint-plugin-boundaries.
 *
 * Identical to the `strict` configuration, but enables the deprecated `boundaries/no-ignored` and
 * `boundaries/no-unknown` rule names instead of their `boundaries/no-ignored-dependencies` and
 * `boundaries/no-unknown-dependencies` replacements.
 *
 * Use this preset only as a temporary measure right after upgrading from v6, if your codebase has
 * `eslint-disable` comments referencing the old rule names and you are not ready to update them yet.
 * Prefer the `strict` configuration otherwise: it does not print deprecation warnings and is the one
 * that will keep working in future major versions.
 */
declare const config: Config;
export default config;
