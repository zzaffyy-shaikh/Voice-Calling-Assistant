import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@vapi-ai/web"],
  output: "standalone",
  turbopack: {},
};

export default nextConfig;
