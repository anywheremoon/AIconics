import { Navigate } from "react-router-dom";

import { LOGIN_STATUS } from "../api/authApi.js";
import { useAuth } from "../auth/AuthContext.jsx";
import AuthLoading from "../components/AuthLoading.jsx";


function RequireAuth({ children }) {
  const {
    loading,
    isAuthenticated,
    pendingLogin,
  } = useAuth();

  if (loading) {
    return <AuthLoading />;
  }

  if (isAuthenticated) {
    return children;
  }

  if (
    pendingLogin?.login_status ===
    LOGIN_STATUS.REQUIRE_VERIFICATION
  ) {
    return (
      <Navigate
        to="/additional-verification"
        replace
      />
    );
  }

  if (
    pendingLogin?.login_status ===
    LOGIN_STATUS.PENDING_REVIEW
  ) {
    return (
      <Navigate
        to="/login-pending"
        replace
      />
    );
  }

  return (
    <Navigate
      to="/login"
      replace
    />
  );
}

export default RequireAuth;