export function hasScope(scopes: string[] | undefined, scope: string): boolean {
  return Boolean(scopes?.includes(scope));
}

export function canApprove(scopes: string[] | undefined): boolean {
  return hasScope(scopes, "policy.approve") || hasScope(scopes, "consultant.decide");
}

export function canPause(scopes: string[] | undefined): boolean {
  return hasScope(scopes, "company.pause");
}

export function canResume(scopes: string[] | undefined): boolean {
  return hasScope(scopes, "company.resume");
}

export function canEnroll(scopes: string[] | undefined): boolean {
  return hasScope(scopes, "project.enroll");
}

export function canRespondInbox(scopes: string[] | undefined): boolean {
  return hasScope(scopes, "company.pause");
}

export function canEscalate(scopes: string[] | undefined): boolean {
  return hasScope(scopes, "owner.escalate");
}
