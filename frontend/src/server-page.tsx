/** Server-defined management forms keep their existing endpoints and permissions.
 * Rendering uses the same island controls as the data-driven operational pages. */
import React, { useState } from "react";
import parse, {
  attributesToProps,
  domToReact,
  Element,
  type DOMNode,
  type HTMLReactParserOptions,
} from "html-react-parser";
import {
  Button,
  Card,
  Checkbox,
  CodeBlock,
  Collapse,
  Input,
  Radio,
  Select,
  Table,
  Tag,
  Title,
} from "animal-island-ui";
import { BookIcon, LeafIcon, SaveIcon } from "naive-icons";
import { Empty, PageHeading, originalContent, t, shell } from "./core";

const childrenOf = (node: Element, tag: string) =>
  node.children.filter(
    (child): child is Element => child instanceof Element && child.name === tag,
  );
function textContent(node: DOMNode): string {
  return "data" in node
    ? String(node.data)
    : "children" in node
      ? node.children.map((child) => textContent(child as DOMNode)).join("")
      : "";
}
function IslandSelect({ node }: { node: Element }) {
  const options = childrenOf(node, "option").map((option) => ({
    key: option.attribs.value ?? textContent(option),
    label: textContent(option),
  }));
  const selected = childrenOf(node, "option").find(
    (option) => "selected" in option.attribs,
  );
  const [value, setValue] = useState(
    selected?.attribs.value ?? options[0]?.key ?? "",
  );
  return (
    <>
      <Select
        options={options}
        value={value}
        onChange={setValue}
        disabled={"disabled" in node.attribs}
        aria-label={node.attribs["aria-label"] || node.attribs.name}
      />
      <input type="hidden" name={node.attribs.name} value={value} />
    </>
  );
}
function IslandCheck({ node }: { node: Element }) {
  const [values, setValues] = useState<Array<string | number>>(
    "checked" in node.attribs ? [node.attribs.value || "on"] : [],
  );
  const value = node.attribs.value || "on";
  return (
    <>
      <Checkbox
        value={values}
        onChange={setValues}
        disabled={"disabled" in node.attribs}
        options={[
          {
            value,
            label:
              node.attribs["aria-label"] || node.attribs.name || t("ui.enable"),
          },
        ]}
      />
      {values.length > 0 && (
        <input type="hidden" name={node.attribs.name} value={value} />
      )}
    </>
  );
}
const options: HTMLReactParserOptions = {
  replace(node) {
    if (!(node instanceof Element)) return;
    const props = attributesToProps(node.attribs),
      classes = node.attribs.class || "";
    const child = () => domToReact(node.children as DOMNode[], options);
    if (classes.includes("page-hero")) return <></>;
    if (node.name === "button") {
      const { type, ...rest } = props;
      const primary = /save|create|enable|install|apply/.test(
        node.attribs.value || "",
      );
      return (
        <Button
          {...rest}
          htmlType={(type || "submit") as "button" | "submit" | "reset"}
          type={primary ? "primary" : "default"}
          danger={/delete|remove|uninstall|stop/.test(node.attribs.value || "")}
          size="small"
        >
          {child()}
        </Button>
      );
    }
    if (node.name === "select") return <IslandSelect node={node} />;
    if (node.name === "input" && node.attribs.type === "checkbox")
      return <IslandCheck node={node} />;
    if (
      node.name === "input" &&
      !["hidden", "file", "radio"].includes(node.attribs.type || "")
    ) {
      const { size, ...rest } = props;
      return (
        <Input
          {...rest}
          aria-label={
            node.attribs["aria-label"] ||
            node.attribs.placeholder ||
            node.attribs.name
          }
        />
      );
    }
    if (classes.split(" ").includes("panel"))
      return (
        <Card className={`management-board ${classes}`} pattern="none">
          {child()}
        </Card>
      );
    if (classes.includes("metric-card"))
      return (
        <Card
          className="management-metric"
          pattern="app-yellow"
          color="app-yellow"
        >
          {child()}
        </Card>
      );
    if (node.name === "h2")
      return (
        <Title size="small" color="app-teal">
          {child()}
        </Title>
      );
    if (node.name === "pre")
      return (
        <Collapse
          question={t("ui.inspect_details")}
          answer={<CodeBlock code={textContent(node)} />}
        />
      );
    if (classes.includes("status-chip"))
      return (
        <Tag
          variant="soft"
          color={
            /error|critical/.test(classes)
              ? "app-red"
              : /success/.test(classes)
                ? "app-teal"
                : "app-orange"
          }
          size="small"
        >
          {child()}
        </Tag>
      );
    if (classes.includes("empty-state"))
      return <Empty title={textContent(node)} />;
    if (node.name === "table") {
      const head = childrenOf(node, "thead")[0],
        body = childrenOf(node, "tbody")[0];
      const headrow = head && childrenOf(head, "tr")[0],
        heads = headrow && childrenOf(headrow, "th"),
        rows = body && childrenOf(body, "tr");
      if (heads?.length && rows?.length) {
        const empty =
          rows.length === 1 &&
          childrenOf(rows[0], "td").length === 1 &&
          childrenOf(rows[0], "td")[0].attribs.colspan;
        if (empty) return <Empty title={textContent(rows[0])} />;
        if (rows.every((row) => childrenOf(row, "td").length === heads.length))
          return (
            <Table
              rowKey="key"
              scroll={{ x: "max-content" }}
              pagination={rows.length > 10 ? { pageSize: 10 } : false}
              columns={heads.map((cell, i) => ({
                title: domToReact(cell.children as DOMNode[], options),
                dataIndex: `c${i}`,
              }))}
              dataSource={rows.map((row, i) => ({
                key: String(i),
                ...Object.fromEntries(
                  childrenOf(row, "td").map((cell, j) => [
                    `c${j}`,
                    domToReact(cell.children as DOMNode[], options),
                  ]),
                ),
              }))}
            />
          );
      }
      return (
        <div className="table-scroll">
          <table {...props}>{child()}</table>
        </div>
      );
    }
  },
};
export function ServerPage() {
  const descriptionKey = `description.${location.pathname.split("/")[1]}`;
  const description = t(descriptionKey);
  return (
    <>
      <PageHeading
        title={shell.title}
        subtitle={description === descriptionKey ? undefined : description}
      />
      <div className="management-content">
        {parse(originalContent, options)}
      </div>
    </>
  );
}
