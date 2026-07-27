import { NextResponse, type NextRequest } from "next/server";

/**
 * Next.js 16'da `middleware` -> `proxy` deb nomlangan (runtime: nodejs).
 * Vazifasi: sessiya cookie'siz /admin va / marshrutlariga kirishni to'sish.
 */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const session = request.cookies.get("qr_session")?.value;

  const isPublic = pathname.startsWith("/login");

  if (!session && !isPublic) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  if (session && isPublic) {
    const url = request.nextUrl.clone();
    url.pathname = "/";
    url.search = "";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
