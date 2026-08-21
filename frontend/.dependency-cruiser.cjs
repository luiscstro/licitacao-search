/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: "no-components-importing-pages",
      severity: "error",
      comment:
        "src/components/** must stay leaf/presentational modules that pages depend on — " +
        "they must never import from src/pages/**.",
      from: { path: "^src/components" },
      to: { path: "^src/pages" },
    },
    {
      name: "no-circular",
      severity: "error",
      comment: "Circular dependencies make modules hard to reason about and can break bundling/HMR.",
      from: {},
      to: { circular: true },
    },
  ],
  options: {
    tsPreCompilationDeps: true,
    combinedDependencies: true,
    exclude: {
      path: "node_modules",
    },
    enhancedResolveOptions: {
      exportsFields: ["exports"],
      conditionNames: ["import", "require", "node", "default"],
    },
  },
};
