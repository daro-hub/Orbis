/** @type {import('next').NextConfig} */
// API_BASE_URL is server-side only (read here at request time by Next's
// rewrite handler, never shipped to the browser bundle) -- defaults to
// the local FastAPI dev server so `npm run dev` works out of the box.
// A deployed frontend (e.g. on Vercel) must set this to the deployed
// backend's URL (e.g. a Render service), or every /api/* call 404s.
const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:8000";

const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_BASE_URL}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
