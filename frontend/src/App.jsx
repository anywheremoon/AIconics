import {
  BrowserRouter,
  NavLink,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

// 인증 관련
import {
  AuthProvider,
  useAuth,
} from "./auth/AuthContext.jsx";

import RequireAuth from "./routes/RequireAuth.jsx";
import RequireAdmin from "./routes/RequireAdmin.jsx";

import AppNavigation from "./components/AppNavigation.jsx";
import AuthLoading from "./components/AuthLoading.jsx";

// 관리자 페이지
import DashboardPage from "./pages/DashboardPage";
import SuspiciousUsersPage from "./pages/SuspiciousUsersPage";
import EventLogsPage from "./pages/EventLogsPage";

// 로그인·인증 페이지
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import AdditionalVerificationPage from "./pages/AdditionalVerificationPage.jsx";
import LoginPendingPage from "./pages/LoginPendingPage.jsx";

// 금융 기능 페이지
import AccountPage from "./pages/AccountPage.jsx";
import TransferPage from "./pages/TransferPage.jsx";
import WithdrawPage from "./pages/WithdrawPage.jsx";
import TransactionResultPage from "./pages/TransactionResultPage.jsx";

// 권한 없음 페이지
import ForbiddenPage from "./pages/ForbiddenPage.jsx";


// ================================
// 루트 주소("/") 이동 처리
// ================================

function HomeRedirect() {
  const {
    loading,
    user,
    pendingLogin,
  } = useAuth();

  if (loading) {
    return <AuthLoading />;
  }

  if (!user) {
    if (
      pendingLogin?.login_status ===
      "REQUIRE_VERIFICATION"
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
      "PENDING_REVIEW"
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

  return (
    <Navigate
      to={
        user.role === "ADMIN"
          ? "/dashboard"
          : "/account"
      }
      replace
    />
  );
}


// ================================
// 404 페이지
// ================================

function NotFoundPage() {
  const {
    loading,
    user,
  } = useAuth();

  if (loading) {
    return <AuthLoading />;
  }

  return (
    <main className="page-container">
      <h1 className="page-title">
        페이지를 찾을 수 없습니다.
      </h1>

      <p className="page-description">
        입력한 주소가 올바른지 확인해주세요.
      </p>

      {user?.role === "ADMIN" ? (
        <NavLink
          to="/dashboard"
          className="action-button"
        >
          대시보드로 이동
        </NavLink>
      ) : user ? (
        <NavLink
          to="/account"
          className="action-button"
        >
          내 계좌로 이동
        </NavLink>
      ) : (
        <NavLink
          to="/login"
          className="action-button"
        >
          로그인으로 이동
        </NavLink>
      )}
    </main>
  );
}


// ================================
// 실제 앱 라우팅
// ================================

function AppRoutes() {
  return (
    <>
      <AppNavigation />

      <Routes>
        {/* 시작 주소 */}
        <Route
          path="/"
          element={<HomeRedirect />}
        />

        {/* 로그인·회원가입 */}
        <Route
          path="/login"
          element={<LoginPage />}
        />

        <Route
          path="/register"
          element={<RegisterPage />}
        />

        {/* 로그인 완료 전 화면 */}
        <Route
          path="/additional-verification"
          element={<AdditionalVerificationPage />}
        />

        <Route
          path="/login-pending"
          element={<LoginPendingPage />}
        />

        {/* 로그인 사용자 */}
        <Route
          path="/account"
          element={
            <RequireAuth>
              <AccountPage />
            </RequireAuth>
          }
        />

        <Route
          path="/transfer"
          element={
            <RequireAuth>
              <TransferPage />
            </RequireAuth>
          }
        />

        <Route
          path="/withdraw"
          element={
            <RequireAuth>
              <WithdrawPage />
            </RequireAuth>
          }
        />

        <Route
          path="/transaction-result"
          element={
            <RequireAuth>
              <TransactionResultPage />
            </RequireAuth>
          }
        />

        {/* 관리자 전용 */}
        <Route
          path="/dashboard"
          element={
            <RequireAdmin>
              <DashboardPage />
            </RequireAdmin>
          }
        />

        <Route
          path="/suspicious-users"
          element={
            <RequireAdmin>
              <SuspiciousUsersPage />
            </RequireAdmin>
          }
        />

        <Route
          path="/event-logs"
          element={
            <RequireAdmin>
              <EventLogsPage />
            </RequireAdmin>
          }
        />

        {/* 권한 없음 */}
        <Route
          path="/forbidden"
          element={<ForbiddenPage />}
        />

        {/* 없는 주소 */}
        <Route
          path="*"
          element={<NotFoundPage />}
        />
      </Routes>
    </>
  );
}


// ================================
// App
// ================================

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}