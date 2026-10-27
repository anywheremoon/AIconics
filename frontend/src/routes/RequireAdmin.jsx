import { Navigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext.jsx";
import RequireAuth from "./RequireAuth.jsx";


function RequireAdmin({ children }) {
  const { user } = useAuth();

  return (
    <RequireAuth>
      {user?.role === "ADMIN" ? (
        children
      ) : (
        <Navigate
          to="/forbidden"
          replace
        />
      )}
    </RequireAuth>
  );
}

export default RequireAdmin;