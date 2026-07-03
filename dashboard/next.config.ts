import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      { source: "/api/:path*", destination: "http://backend:4900/api/:path*" },
    ];
  },
};

export default nextConfig;
