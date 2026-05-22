/** @type {import('next').NextConfig} */
//
// `assetPrefix: "./"` est REQUIS en PROD (static export → app Electron qui
// charge index.html via file://, donc les URLs absolues comme /_next/...
// ne marchent pas et il faut du relatif). MAIS en DEV (next dev sur
// http://localhost:3000), les sous-routes comme /tray-popup se résolvent
// en /tray-popup/_next/... qui n'existe pas → CSS/JS en 404 → page sans
// styles et boutons morts. Conditionner l'assetPrefix au NODE_ENV évite
// le piège.
const isProd = process.env.NODE_ENV === "production";

// PAS de trailingSlash : on veut que chaque route soit générée comme un
// fichier HTML au MÊME niveau que la racine (out/index.html ET
// out/tray-popup.html), et NON dans des sous-dossiers (out/tray-popup/
// index.html). Pourquoi : avec assetPrefix "./" (requis en prod pour le
// chargement file:// dans Electron), un HTML en sous-dossier chercherait
// ses assets dans out/tray-popup/_next/ (inexistant) → page sans styles.
// En gardant tous les HTML à la racine, "./_next/" résout toujours vers
// out/_next/.
const nextConfig = {
  output: "export",
  assetPrefix: isProd ? "./" : undefined,
  trailingSlash: false,
  images: { unoptimized: true },
  experimental: {
    serverActions: { bodySizeLimit: "500mb" },
    middlewareClientMaxBodySize: "500mb",
  },
};
module.exports = nextConfig;
