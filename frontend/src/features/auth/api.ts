import { api } from "@/api/client";
import type { User } from "@/api/types";

export interface LoginInput {
  email: string;
  password: string;
}

export const authApi = {
  login: (input: LoginInput) => api.post<User>("/auth/login", input),
  logout: () => api.post<void>("/auth/logout"),
  me: () => api.get<User>("/auth/me"),
};
