// 批量把 LaTeX 预渲染成 KaTeX HTML。
// 读取 stdin: [{ key, tex, block }]，输出 stdout: { key: html }
// 任何一条解析失败都会让构建失败（不静默降级）。
import katex from "katex";

let input = "";
process.stdin.setEncoding("utf8");
for await (const chunk of process.stdin) input += chunk;

const items = JSON.parse(input);
const out = {};
const failed = [];

for (const { key, tex, block } of items) {
  try {
    out[key] = katex.renderToString(block ? "\\displaystyle " + tex : tex, {
      throwOnError: true,
      displayMode: false,
      strict: false,
      trust: false,
      output: "htmlAndMathml",
    });
  } catch (err) {
    failed.push({ tex, error: err.message });
  }
}

if (failed.length) {
  process.stderr.write(
    "KaTeX 渲染失败 " + failed.length + " 条：\n" +
      failed.map((f) => "- " + f.tex.slice(0, 120) + "\n  " + f.error).join("\n") +
      "\n"
  );
  process.exit(1);
}

process.stdout.write(JSON.stringify(out));
