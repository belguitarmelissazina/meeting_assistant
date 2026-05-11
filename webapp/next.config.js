/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  assetPrefix: "./",
  trailingSlash: true,
  images: { unoptimized: true },
  experimental: {
    serverActions: { bodySizeLimit: "500mb" },
    middlewareClientMaxBodySize: "500mb",
  },
};
module.exports = nextConfig;
