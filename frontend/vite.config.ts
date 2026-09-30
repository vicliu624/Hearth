import { defineConfig } from "vite";
import { islandLocalization } from "./island-localization.ts";
export default defineConfig({
  base: "/static/island/",
  resolve: { dedupe: ["react", "react-dom"] },
  plugins: [
    islandLocalization(),
    {
      name: "animal-island-react-client-compatibility",
      // The published 2.0.0 package embeds React 18's react-dom/client shim.
      // Bind its notification portal to the app's real React 19 client API.
      transform(_code, id) {
        if (
          id
            .replaceAll("\\", "/")
            .endsWith("/animal-island-ui/dist/es/_virtual/client.js")
        ) {
          return 'import * as client from "react-dom/client"; export { client as c };';
        }
      },
    },
  ],
  css: {
    postcss: {
      // Replace upstream full-font declarations with local, subsetted Nunito /
      // Noto Sans SC. Preserve the actual typography without multi-MB CSS.
      plugins: [
        {
          postcssPlugin: "hearth-system-fonts",
          AtRule: {
            "font-face": (rule: {
              source?: { input?: { file?: string } };
              remove: () => void;
            }) => {
              if (rule.source?.input?.file?.includes("node_modules"))
                rule.remove();
            },
          },
        },
      ],
    },
  },
  build: {
    cssCodeSplit: false,
    outDir: "../src/hearth/web/static/island",
    emptyOutDir: true,
    rolldownOptions: {
      input: "src/main.tsx",
      output: {
        entryFileNames: "hearth.js",
        assetFileNames: "hearth.[ext]",
        codeSplitting: {
          groups: [
            {
              name: "react",
              test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/,
              priority: 20,
            },
            {
              name: "island",
              test: /node_modules[\\/](animal-island-ui|naive-icons)[\\/]/,
              priority: 10,
            },
          ],
        },
      },
    },
    sourcemap: false,
  },
});
