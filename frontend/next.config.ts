import type {NextConfig} from "next";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendInternalUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
