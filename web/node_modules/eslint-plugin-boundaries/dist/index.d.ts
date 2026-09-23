import type { PluginBoundaries } from "./Shared";
export * from "./Public";
/**
 * Eslint plugin ensuring that architecture boundaries are respected by the elements in a project
 * It enables to check the folders and files structure and the dependencies and relationships between them.
 */
declare const publicInterface: PluginBoundaries;
export default publicInterface;
