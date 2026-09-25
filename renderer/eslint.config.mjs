import js from "@eslint/js";
import tseslint from "typescript-eslint";
import remotionPlugin from "@remotion/eslint-plugin";

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    plugins: {
      "@remotion": remotionPlugin.flatPlugin.plugins["@remotion"],
    },
    rules: {
      ...remotionPlugin.flatPlugin.rules,
    },
  },
  {
    ignores: [
      "node_modules/",
      "build/",
      "out/",
      "dist/",
      "**/*.d.ts",
    ],
  }
);
