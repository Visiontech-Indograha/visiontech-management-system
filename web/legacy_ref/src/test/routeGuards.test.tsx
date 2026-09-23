import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ProtectedRoute } from "../components/layout/ProtectedRoute";
import { RoleRoute } from "../components/layout/RoleRoute";
import { UserRole, UserApp } from "../types/auth";

const mockUseAuth = vi.fn();

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

const baseUser: UserApp = {
  id: "1",
  username: "tester",
  role: UserRole.FIELD_STAFF,
  is_active: true,
  created_at: "",
  updated_at: "",
};

function renderWithGuard(element: React.ReactNode) {
  return render(
    <MemoryRouter initialEntries={["/protected"]}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route path="/protected" element={element}>
          <Route index element={<div>Secret Content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe("ProtectedRoute", () => {
  it("redirects to /login when there is no user", () => {
    mockUseAuth.mockReturnValue({ user: null, isLoading: false });
    renderWithGuard(<ProtectedRoute />);
    expect(screen.getByText("Login Page")).toBeInTheDocument();
  });

  it("shows a loading state while auth is resolving", () => {
    mockUseAuth.mockReturnValue({ user: null, isLoading: true });
    renderWithGuard(<ProtectedRoute />);
    expect(screen.queryByText("Secret Content")).not.toBeInTheDocument();
    expect(screen.queryByText("Login Page")).not.toBeInTheDocument();
  });

  it("renders the outlet when a user is authenticated", () => {
    mockUseAuth.mockReturnValue({ user: baseUser, isLoading: false });
    renderWithGuard(<ProtectedRoute />);
    expect(screen.getByText("Secret Content")).toBeInTheDocument();
  });
});

describe("RoleRoute", () => {
  it("redirects to /login when there is no user", () => {
    mockUseAuth.mockReturnValue({ user: null, isLoading: false });
    renderWithGuard(<RoleRoute allowedRoles={[UserRole.ADMIN]} />);
    expect(screen.getByText("Login Page")).toBeInTheDocument();
  });

  it("shows Akses Ditolak when the user's role is not allowed", () => {
    mockUseAuth.mockReturnValue({ user: baseUser, isLoading: false });
    renderWithGuard(<RoleRoute allowedRoles={[UserRole.ADMIN]} />);
    expect(screen.getByText("Akses Ditolak")).toBeInTheDocument();
    expect(screen.queryByText("Secret Content")).not.toBeInTheDocument();
  });

  it("renders the outlet when the user's role is allowed", () => {
    mockUseAuth.mockReturnValue({ user: baseUser, isLoading: false });
    renderWithGuard(<RoleRoute allowedRoles={[UserRole.FIELD_STAFF]} />);
    expect(screen.getByText("Secret Content")).toBeInTheDocument();
  });
});
