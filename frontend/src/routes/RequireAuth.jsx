import { Navigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext.jsx";
import AuthLoading from "../components/AuthLoading.jsx";

function RequireAuth({ children }) {
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

  return children;
}

export default RequireAuth;