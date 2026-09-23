import React, { createContext, useContext, useState, useEffect } from "react";
import axios from "axios";
import api, { setMemoryToken } from "../lib/api";
import { UserApp } from "../types/auth";

/** 401 saat boot tanpa sesi adalah kondisi normal, bukan error yang perlu di-log. */
const isExpectedUnauthorized = (error: unknown): boolean =>
  axios.isAxiosError(error) && error.response?.status === 401;

interface AuthContextType {
  user: UserApp | null;
  isLoading: boolean;
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserApp | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchUser = async () => {
    try {
      const response = await api.get<UserApp>("/api/v1/auth/me");
      setUser(response.data);
    } catch (error) {
      if (!isExpectedUnauthorized(error)) {
        console.error("Failed to fetch user profile", error);
      }
      setUser(null);
      setMemoryToken(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    (async () => {
      try {
        const response = await api.get<UserApp>("/api/v1/auth/me");
        if (!ignore) setUser(response.data);
      } catch (error) {
        if (!isExpectedUnauthorized(error)) {
          console.error("Failed to fetch user profile", error);
        }
        if (!ignore) {
          setUser(null);
          setMemoryToken(null);
        }
      } finally {
        if (!ignore) setIsLoading(false);
      }
    })();
    return () => {
      ignore = true;
    };
  }, []);

  const login = (token: string) => {
    setMemoryToken(token);
    fetchUser();
  };

  const logout = async () => {
    try {
      await api.post("/api/v1/auth/logout");
    } catch (e) {
      console.error("Logout failed", e);
    } finally {
      setMemoryToken(null);
      setUser(null);
      window.location.href = "/login";
    }
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
