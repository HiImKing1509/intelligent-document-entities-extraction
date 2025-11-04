type NodeBuffer = typeof import("buffer").Buffer;

export async function readFileAsBase64(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const maybeBuffer = (globalThis as unknown as { Buffer?: NodeBuffer }).Buffer;

  if (maybeBuffer) {
    return maybeBuffer.from(buffer).toString("base64");
  }

  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  let binary = "";

  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    const chunk = bytes.subarray(offset, offset + chunkSize);
    binary += String.fromCharCode(...chunk);
  }

  return globalThis.btoa(binary);
}

export function createDataUrl(base64: string, mimeType: string): string {
  return `data:${mimeType};base64,${base64}`;
}

export function isPdf(file: File): boolean {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
}

export function createFileObjectUrl(file: File) {
  return URL.createObjectURL(file);
}

export function revokeFileObjectUrl(url: string) {
  URL.revokeObjectURL(url);
}

export function dataUrlToObjectUrl(dataUrl: string): string {
  const [metadata, base64Payload] = dataUrl.split(",");
  if (!base64Payload) {
    return dataUrl;
  }

  const mimeMatch = metadata.match(/^data:(.*?);base64$/);
  const mimeType = mimeMatch?.[1] ?? "application/octet-stream";
  const maybeBuffer = (globalThis as unknown as { Buffer?: NodeBuffer }).Buffer;
  const binary =
    typeof globalThis.atob === "function"
      ? atob(base64Payload)
      : maybeBuffer
          ?.from(base64Payload, "base64")
          .toString("binary");

  if (!binary) {
    return dataUrl;
  }

  const bytes = new Uint8Array(binary.length);

  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }

  const blob = new Blob([bytes], { type: mimeType });
  return URL.createObjectURL(blob);
}
