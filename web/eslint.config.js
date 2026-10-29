import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

export default tseslint.config(
  // src/components/iso is the vendored anatomy kit (MIT, third-party): kept byte-identical to upstream, not linted.
  { ignores: ["dist", "node_modules", "src/api/schema.d.ts", "src/components/iso/**"] },
  js.configs.recommended,
  ...tseslint.configs.strict,
  {
    files: ["src/**/*.{ts,tsx}"],
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // Scanned text must never be injected as HTML.
      "no-restricted-properties": ["error", { property: "innerHTML" }, { property: "outerHTML" }],
      "no-restricted-syntax": ["error", { selector: "JSXAttribute[name.name='dangerouslySetInnerHTML']", message: "Render scanned text as plain text." }],
    },
  },
);
