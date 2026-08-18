import { createContext, useContext, useEffect, useState } from "react";
import { getCurrentUser } from "../api/authApi.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(
    localStorage.getItem("access_token")
  );
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const restoreLogin = async () => {
      const savedToken = localStorage.getItem("access_token");

      if (!savedToken) {
        setLoading(false);
        return;
      }

      try {
        const currentUser = await getCurrentUser();

        setToken(savedToken);
        setUser(currentUser);
      } catch (error) {
        localStorage.removeItem("access_token");
        setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    restoreLogin();
  }, []);

  const saveLogin = (result) => {
    localStorage.setItem(
      "access_token",
      result.access_token
    );

    setToken(result.access_token);
    setUser(result.user);
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        loading,
        token,
        user,
        login: saveLogin,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}