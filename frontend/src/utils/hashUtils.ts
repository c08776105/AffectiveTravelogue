export async function sha256Hash(value: string) {
  const encodedUint8 = new TextEncoder().encode(value);
  const buffer = await window.crypto.subtle.digest("SHA-256", encodedUint8);
  const hexString = Array.from(new Uint8Array(buffer), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
  return hexString;
}
