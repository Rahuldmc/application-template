import { QueryClient } from "@tanstack/react-query";

import { isApiError } from "@/api/errors";

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        // Retrying a 4xx (bad input, no permission) never helps; retry network/5xx once.
        retry: (count, error) => !(isApiError(error) && error.status < 500) && count < 1,
      },
    },
  });
}
