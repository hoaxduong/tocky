import { NextRequest, NextResponse } from "next/server"
import { jwtVerify, importSPKI } from "jose"

const PUBLIC_PATHS = ["/sign-in", "/sign-up"]
const ADMIN_PREFIX = "/admin"

let publicKeyPromise: ReturnType<typeof importSPKI> | null = null

function getPublicKey() {
  const pem = process.env.NEXT_PUBLIC_JWT_PUBLIC_KEY ?? ""
  if (!pem) return null
  if (!publicKeyPromise) {
    publicKeyPromise = importSPKI(pem, "ES256")
  }
  return publicKeyPromise
}

async function verifyToken(token: string) {
  const key = getPublicKey()
  if (!key) return null
  try {
    const { payload } = await jwtVerify(token, await key, {
      issuer: "tocky",
      algorithms: ["ES256"],
    })
    return payload as { sub: string; email: string; role: string }
  } catch {
    return null
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const accessToken = request.cookies.get("tocky_access")?.value

  const isPublicPath = PUBLIC_PATHS.some((p) => pathname.startsWith(p))

  // Public paths: redirect authenticated users to dashboard
  if (isPublicPath) {
    if (accessToken) {
      const payload = await verifyToken(accessToken)
      if (payload) {
        return NextResponse.redirect(new URL("/dashboard", request.url))
      }
    }
    return NextResponse.next()
  }

  // Protected paths: require authentication
  if (!accessToken) {
    const signInUrl = new URL("/sign-in", request.url)
    signInUrl.searchParams.set("callbackUrl", pathname)
    return NextResponse.redirect(signInUrl)
  }

  const payload = await verifyToken(accessToken)
  if (!payload) {
    // Token invalid/expired — let client-side refresh handle it,
    // but clear the cookie to avoid redirect loops
    const signInUrl = new URL("/sign-in", request.url)
    const response = NextResponse.redirect(signInUrl)
    response.cookies.delete("tocky_access")
    return response
  }

  // Admin routes: require admin role
  if (pathname.startsWith(ADMIN_PREFIX) && payload.role !== "admin") {
    return NextResponse.redirect(new URL("/dashboard", request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|api/).*)",
  ],
}
