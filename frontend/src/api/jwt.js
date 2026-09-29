// Decodes the JWT payload for UI display only (e.g. "you're viewing as
// agency_admin @ Northwind"). All real authorization happens server-side —
// this never gates what the UI lets you click.
export function decodeJwt(token) {
  try {
    const payload = token.split('.')[1]
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')))
  } catch {
    return null
  }
}
