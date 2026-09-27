import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import type { Page, User, UserUpdate } from "@/api/types";

// Reference feature module: API calls + React Query hooks in one place.
// Components use the hooks; they never call `api` directly.

export const usersApi = {
  list: (offset: number, limit: number) =>
    api.get<Page<User>>("/users", { query: { offset, limit } }),
  update: (id: string, input: UserUpdate) =>
    api.patch<User>(`/users/${encodeURIComponent(id)}`, input),
};

export const userKeys = {
  all: ["users"] as const,
  list: (offset: number, limit: number) => [...userKeys.all, "list", offset, limit] as const,
};

export function useUsers(offset = 0, limit = 50) {
  return useQuery({
    queryKey: userKeys.list(offset, limit),
    queryFn: () => usersApi.list(offset, limit),
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: UserUpdate }) => usersApi.update(id, input),
    // Refetch every users query so lists and details show the change.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: userKeys.all }),
  });
}
