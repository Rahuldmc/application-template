import { useState } from "react";

import { errorMessage } from "@/api/errors";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";

import { useUpdateUser, useUsers } from "./api";

const PAGE_SIZE = 20;

export function UsersPage() {
  const [offset, setOffset] = useState(0);
  const { data, error, isPending } = useUsers(offset, PAGE_SIZE);
  const updateUser = useUpdateUser();

  if (isPending) return <p>Loading users…</p>;
  if (error) return <Alert>{errorMessage(error)}</Alert>;

  const hasNext = offset + PAGE_SIZE < data.total;

  return (
    <section>
      <h1>Users</h1>
      {updateUser.error && <Alert>{errorMessage(updateUser.error)}</Alert>}
      <table className="table">
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Email</th>
            <th scope="col">Role</th>
            <th scope="col">Status</th>
            <th scope="col">
              <span className="visually-hidden">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((user) => (
            <tr key={user.id}>
              <td>{user.full_name}</td>
              <td>{user.email}</td>
              <td>{user.role}</td>
              <td>{user.is_active ? "Active" : "Disabled"}</td>
              <td>
                <Button
                  variant="secondary"
                  disabled={updateUser.isPending}
                  onClick={() =>
                    updateUser.mutate({ id: user.id, input: { is_active: !user.is_active } })
                  }
                >
                  {user.is_active ? "Disable" : "Enable"}
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <nav className="pager" aria-label="Pagination">
        <Button
          variant="secondary"
          disabled={offset === 0}
          onClick={() => setOffset(offset - PAGE_SIZE)}
        >
          Previous
        </Button>
        <span>
          {data.total === 0 ? 0 : offset + 1}–{Math.min(offset + PAGE_SIZE, data.total)} of{" "}
          {data.total}
        </span>
        <Button
          variant="secondary"
          disabled={!hasNext}
          onClick={() => setOffset(offset + PAGE_SIZE)}
        >
          Next
        </Button>
      </nav>
    </section>
  );
}
