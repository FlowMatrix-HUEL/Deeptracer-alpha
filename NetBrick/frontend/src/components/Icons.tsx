import type { SVGProps } from "react";

export type IconName =
  | "plus"
  | "save"
  | "folder"
  | "undo"
  | "redo"
  | "play"
  | "code"
  | "check"
  | "trash"
  | "search"
  | "spark"
  | "download"
  | "upload"
  | "layout"
  | "close"
  | "chevron"
  | "warning"
  | "layers"
  | "python"
  | "package"
  | "copy"
  | "info";

const paths: Record<IconName, string> = {
  plus: "M12 5v14M5 12h14",
  save: "M5 3h12l2 2v16H5V3Zm3 0v6h8V3M8 21v-7h8v7",
  folder: "M3 7h7l2 2h9v10H3V7Z",
  undo: "M9 7 4 12l5 5M5 12h8a6 6 0 0 1 6 6",
  redo: "m15 7 5 5-5 5m4-5h-8a6 6 0 0 0-6 6",
  play: "m8 5 11 7-11 7V5Z",
  code: "m8 8-4 4 4 4m8-8 4 4-4 4M14 4l-4 16",
  check: "m5 12 4 4L19 6",
  trash: "M4 7h16M9 7V4h6v3m3 0-1 14H7L6 7m4 4v6m4-6v6",
  search: "m20 20-4.5-4.5M18 11a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z",
  spark: "m12 2 1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2Zm6 14 .9 3.1L22 20l-3.1.9L18 24l-.9-3.1L14 20l3.1-.9L18 16Z",
  download: "M12 3v12m-5-5 5 5 5-5M5 20h14",
  upload: "M12 17V5m-5 5 5-5 5 5M5 20h14",
  layout: "M4 4h7v7H4V4Zm9 0h7v4h-7V4ZM4 13h7v7H4v-7Zm9-3h7v10h-7V10Z",
  close: "M6 6l12 12M18 6 6 18",
  chevron: "m8 10 4 4 4-4",
  warning: "M12 3 2.5 20h19L12 3Zm0 6v5m0 3v.1",
  layers: "m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5m-18 4 9 5 9-5",
  python: "M8 3h5a3 3 0 0 1 3 3v4H8a4 4 0 0 0-4 4v1H3V7a4 4 0 0 1 4-4h1Zm8 18h-5a3 3 0 0 1-3-3v-4h8a4 4 0 0 0 4-4v-1h1v7a4 4 0 0 1-4 4h-1ZM8 7h.1M16 17h.1",
  package: "m4 7 8-4 8 4v10l-8 4-8-4V7Zm0 0 8 4 8-4m-8 4v10",
  copy: "M8 8h11v12H8V8Zm-3 8H3V4h11v2",
  info: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Zm0-11v6m0-10v.1",
};

export function Icon({
  name,
  size = 18,
  ...props
}: SVGProps<SVGSVGElement> & { name: IconName; size?: number }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      <path d={paths[name]} />
    </svg>
  );
}
