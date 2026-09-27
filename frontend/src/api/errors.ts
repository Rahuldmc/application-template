export interface FieldError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

/** Every failed API call throws this, built from the backend's
 *  `{"error": {"code", "message", "details"}}` shape. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }

  /** Validation messages keyed by field name, for showing next to form inputs. */
  get fieldErrors(): Record<string, string> {
    if (this.code !== "validation_error" || !Array.isArray(this.details)) return {};
    const result: Record<string, string> = {};
    for (const err of this.details as FieldError[]) {
      const field = String(err.loc[err.loc.length - 1] ?? "");
      if (field && !result[field]) result[field] = err.msg;
    }
    return result;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

/** A message that's safe and sensible to show a user. */
export function errorMessage(error: unknown): string {
  if (isApiError(error)) return error.message;
  return "Something went wrong. Please try again.";
}
