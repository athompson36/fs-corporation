/** Node 18 lacks globalThis.crypto; workbox/terser requires it during SW generation. */
const { webcrypto } = require("node:crypto");
if (!globalThis.crypto) {
  globalThis.crypto = webcrypto;
}
