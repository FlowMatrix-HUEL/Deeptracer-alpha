interface SaveFileHandle {
  createWritable(): Promise<{
    write(data: Blob): Promise<void>;
    close(): Promise<void>;
  }>;
}

interface SaveFilePickerOptions {
  suggestedName: string;
  types: Array<{
    description: string;
    accept: Record<string, string[]>;
  }>;
}

declare global {
  interface Window {
    showSaveFilePicker?: (
      options: SaveFilePickerOptions,
    ) => Promise<SaveFileHandle>;
  }
}

export type SaveResult = "saved" | "downloaded" | "cancelled";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

export async function savePythonFile(
  filename: string,
  source: string,
): Promise<SaveResult> {
  const blob = new Blob([source], {
    type: "text/x-python;charset=utf-8",
  });
  if (window.showSaveFilePicker) {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: filename,
        types: [
          {
            description: "Python 源文件",
            accept: {
              "text/x-python": [".py"],
            },
          },
        ],
      });
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      return "saved";
    } catch (error) {
      if (
        error instanceof DOMException &&
        error.name === "AbortError"
      ) {
        return "cancelled";
      }
      // Fall through to the local native save dialog.
    }
  }
  try {
    const nativeResult = await api.savePythonNative(filename, source);
    if (nativeResult.status === "saved") return "saved";
    if (nativeResult.status === "cancelled") return "cancelled";
  } catch {
    // A stopped backend should not prevent the browser download fallback.
  }
  downloadBlob(blob, filename);
  return "downloaded";
}
import { api } from "./api";

