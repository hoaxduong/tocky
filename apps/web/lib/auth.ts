import { betterAuth } from "better-auth"
import { jwt, admin } from "better-auth/plugins"
import { Pool } from "pg"

export const auth = betterAuth({
  secret: process.env.AUTH_SECRET,
  database: new Pool({
    connectionString: process.env.DATABASE_URL?.replace(
      "postgresql+asyncpg",
      "postgresql",
    ),
  }),
  plugins: [jwt(), admin()],
  session: {
    cookieCache: {
      enabled: true,
    },
  },
  user: {
    additionalFields: {
      role: {
        type: "string",
        defaultValue: "doctor",
        required: true,
      },
    },
  },
})
