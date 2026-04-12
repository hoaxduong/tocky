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

/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@workspace/ui"],
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: "http://localhost:8000/api/v1/:path*",
      },
      {
        source: "/ws/:path*",
        destination: "http://localhost:8000/ws/:path*",
      },
    ]
  },
}

export default withNextIntl(nextConfig)
