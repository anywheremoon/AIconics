import { Navigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext.jsx";
import AuthLoading from "../components/AuthLoading.jsx";

function RequireAdmin({ children }) {
  const {
    loading,
    token,
    user,
  } = useAuth();

  if (loading) {
    return <AuthLoading />;
  }

  if (!token || !user) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  if (user.role !== "ADMIN") {
    return (
      <Navigate
        to="/forbidden"
        replace
      />
    );
  }

  return children;
}

export default RequireAdmin;