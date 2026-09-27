// Friendly names for the types generated from the backend's OpenAPI schema.
// Regenerate after any backend schema change:  npm run gen:api
import type { components } from "./generated/schema";

type Schemas = components["schemas"];

export type User = Schemas["UserRead"];
export type UserCreate = Schemas["UserCreate"];
export type UserUpdate = Schemas["UserUpdate"];
export type Role = Schemas["Role"];
export type Page<T> = { items: T[]; total: number; offset: number; limit: number };
