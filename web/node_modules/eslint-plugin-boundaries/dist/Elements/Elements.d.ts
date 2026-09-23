import type { Matcher, DependencyDescription, DependencyKind, EntityDescription } from "@boundaries/elements";
import type { Rule } from "eslint";
import type { SettingsNormalized } from "../Shared";
import type { EslintLiteralNode } from "./Elements.types";
/**
 * Returns the elements matcher based on the ESLint rule context settings already normalized, filtering out invalid descriptors
 * @param settings The ESLint rule context settings normalized
 * @returns The elements matcher
 */
export declare function getElementsMatcher(settings: SettingsNormalized): Matcher;
/**
 * Returns the specifiers used in an import or export statement
 * @param node The AST node representing the import or export
 * @returns The list of specifiers used in the import or export
 */
export declare function getSpecifiers(node: Rule.Node): string[];
/**
 * Returns the description of the current entity being linted
 * @param fileName The file name (absolute path)
 * @param settings The ESLint rule context settings normalized
 * @returns The description of the current entity being linted
 */
export declare function entityDescription(fileName: string, settings: SettingsNormalized): EntityDescription;
/**
 * Returns the description of a dependency node
 * @param options The dependency node info
 * @param options.node The dependency node
 * @param options.kind The kind of the dependency
 * @param options.nodeKind The kind of the node generating the dependency
 * @param fileName The file name (absolute path)
 * @param settings The ESLint rule context settings normalized
 * @param context The ESLint rule context
 * @returns The description of the dependency node
 */
export declare function dependencyDescription({ node, kind, nodeKind, }: {
    node: EslintLiteralNode;
    kind: DependencyKind;
    nodeKind?: string;
}, 
/** The file name (absolute path) */
fileName: string, 
/** The ESLint rule context settings normalized */
settings: SettingsNormalized, 
/** The ESLint rule context */
context: Rule.RuleContext): DependencyDescription;
