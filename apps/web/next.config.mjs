import createNextIntlPlugin from "next-intl/plugin"

const withNextIntl = createNextIntlPlugin({
  requestConfig: "./i18n/request.ts",
  experimental: {
    srcPath: ".",
    extract: {
      sourceLocale: "en",
    },
    messages: {
      path: "./messages",
      format: "po",
      locales: "infer",
    },
  },
})

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@workspace/ui"],
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${API_URL}/api/v1/:path*`,
      },
    ]
  },
}

export default withNextIntl(nextConfig)
