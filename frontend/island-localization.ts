import type { Plugin } from "vite";

// Authored translations for upstream controls without a locale prop. The
// installed 2.0.0 declarations are the contract; no network translation is used.
const labels: Record<string, [string, string]> = {
  close: ["关闭", "Close"],
  关闭: ["关闭", "Close"],
  关闭预览: ["关闭预览", "Close preview"],
  取消: ["取消", "Cancel"],
  确定: ["确定", "Confirm"],
  请选择: ["请选择", "Select an option"],
  暂无数据: ["暂无数据", "No data available"],
  上一页: ["上一页", "Previous page"],
  下一页: ["下一页", "Next page"],
  分页: ["分页", "Pagination"],
  选择每页条数: ["每页条数", "Rows per page"],
  跳转到指定页: ["跳转到指定页", "Go to page"],
  返回顶部: ["返回顶部", "Back to top"],
  复制: ["复制", "Copy"],
  复制代码: ["复制代码", "Copy code"],
  已复制: ["已复制", "Copied"],
  代码已复制: ["代码已复制", "Code copied"],
  复制失败: ["复制失败", "Copy failed"],
  代码复制失败: ["代码复制失败", "Could not copy code"],
  清除: ["清除", "Clear"],
  图片加载失败: ["图片加载失败", "Could not load image"],
  图片预览: ["图片预览", "Image preview"],
  " / 页": [" / 页", " / page"],
  "共 ": ["共 ", "Total: "],
  " 条": [" 条", " items"],
  跳至: ["跳至", "Go to"],
  " 页": [" 页", " page"],
  页: ["页", ""],
};
export function islandLocalization(): Plugin {
  return {
    name: "hearth-island-localization",
    transform(source, id) {
      const normalized = id.replaceAll("\\", "/");
      if (
        !normalized.includes("/animal-island-ui/dist/es/components/") ||
        !normalized.endsWith(".js") ||
        normalized.endsWith(".less.js")
      )
        return;
      let code = source;
      for (const [original, [cn, en]] of Object.entries(labels)) {
        code = code
          .split(JSON.stringify(original))
          .join(`(__hearthZh ? ${JSON.stringify(cn)} : ${JSON.stringify(en)})`);
      }
      if (normalized.endsWith("/Time/Time.js")) {
        code = code.replace(
          "u[a.getDay()]",
          '(__hearthZh ? ["星期日","星期一","星期二","星期三","星期四","星期五","星期六"][a.getDay()] : u[a.getDay()])',
        );
        code = code.replace(
          "p[a.getMonth()]",
          "(__hearthZh ? `${a.getMonth()+1}月` : p[a.getMonth()])",
        );
        code = code.replace(
          "a.getDate()",
          "(__hearthZh ? `${a.getDate()}日` : a.getDate())",
        );
      }
      if (normalized.endsWith("/Pagination/Pagination.js")) {
        code = code.replace(
          "`每页 ${a} 条`",
          "(__hearthZh ? `每页 ${a} 条` : `${a} rows per page`)",
        );
      }
      if (code !== source)
        return `const __hearthZh = typeof document !== "undefined" && document.documentElement.lang.startsWith("zh");\n${code}`;
    },
  };
}
