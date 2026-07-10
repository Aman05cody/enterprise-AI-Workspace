import { api, type ApiEnvelope } from "@/shared/api/client";

export type User = {
  id: string;
  email: string;
  full_name: string;
  avatar_url?: string | null;
  email_verified_at?: string | null;
  is_active: boolean;
};

export type TokenPayload = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
  logo_url?: string | null;
  plan_tier: string;
  seat_limit?: number | null;
  settings: Record<string, unknown>;
  my_role?: string | null;
};

export async function register(input: {
  email: string;
  password: string;
  full_name: string;
}) {
  const { data } = await api.post<ApiEnvelope<TokenPayload>>(
    "/auth/register",
    input
  );
  return data.data;
}

export async function login(input: { email: string; password: string }) {
  const { data } = await api.post<ApiEnvelope<TokenPayload>>(
    "/auth/login",
    input
  );
  return data.data;
}

export async function getMe() {
  const { data } = await api.get<ApiEnvelope<User>>("/auth/me");
  return data.data;
}

export async function listOrganizations() {
  const { data } = await api.get<ApiEnvelope<Organization[]>>("/organizations");
  return data.data;
}

export async function createOrganization(input: {
  name: string;
  slug?: string;
}) {
  const { data } = await api.post<ApiEnvelope<Organization>>(
    "/organizations",
    input
  );
  return data.data;
}

export function persistSession(tokens: TokenPayload) {
  localStorage.setItem("eaw_access_token", tokens.access_token);
  localStorage.setItem("eaw_refresh_token", tokens.refresh_token);
  localStorage.setItem("eaw_user", JSON.stringify(tokens.user));
}

export function clearSession() {
  localStorage.removeItem("eaw_access_token");
  localStorage.removeItem("eaw_refresh_token");
  localStorage.removeItem("eaw_user");
  localStorage.removeItem("eaw_org_id");
}
