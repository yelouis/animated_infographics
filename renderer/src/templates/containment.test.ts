import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import registry from "../generated/templateRegistry.json";
import { TEMPLATES } from "./index";

describe("Template containment in both directions", () => {
  const templatesDir = path.resolve(__dirname);
  const registryTemplateNames = Object.keys(registry).filter(
    (k) => !k.startsWith("$")
  );

  it("has exactly 18 templates in templateRegistry.json", () => {
    expect(registryTemplateNames.length).toBe(18);
  });

  it("every template name in templateRegistry.json has a corresponding component file", () => {
    for (const name of registryTemplateNames) {
      const componentPath = path.join(templatesDir, `${name}.tsx`);
      expect(
        fs.existsSync(componentPath),
        `Expected component file to exist: ${componentPath}`
      ).toBe(true);
    }
  });

  it("every component file in src/templates/ is in templateRegistry.json", () => {
    const files = fs.readdirSync(templatesDir);
    const componentFiles = files.filter((f) => {
      // Ignore index files, tests, and non-component files
      if (
        f === "index.ts" ||
        f === "index.tsx" ||
        f.endsWith(".test.ts") ||
        f.endsWith(".test.tsx") ||
        f.startsWith(".")
      ) {
        return false;
      }
      return f.endsWith(".tsx") || f.endsWith(".ts");
    });

    // Verify count of component files is 18
    expect(componentFiles.length).toBe(18);

    for (const file of componentFiles) {
      const name = file.replace(/\.(tsx|ts)$/, "");
      expect(
        registryTemplateNames,
        `Component file ${file} has no entry in templateRegistry.json`
      ).toContain(name);
    }
  });

  it("every template name in templateRegistry.json is mapped in TEMPLATES map", () => {
    for (const name of registryTemplateNames) {
      expect(TEMPLATES[name], `Template ${name} is missing in TEMPLATES map`).toBeDefined();
    }
    expect(Object.keys(TEMPLATES).length).toBe(18);
  });
});
