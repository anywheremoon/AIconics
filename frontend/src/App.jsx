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

// 금융 기능 페이지
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
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
  } = useAuth();

  // 로그인 정보 복원 중
  if (loading) {
    return <AuthLoading />;
  }

  // 비로그인
  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  // 관리자
  if (user.role === "ADMIN") {
    return (
      <Navigate
        to="/dashboard"
        replace
      />
    );
  }

  // 일반 사용자
  return (
    <Navigate
      to="/account"
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
      {/* 로그인 상태에 따라 메뉴 표시 */}
      <AppNavigation />

      <Routes>

        {/* ===================== */}
        {/* 시작 주소 */}
        {/* ===================== */}

        <Route
          path="/"
          element={<HomeRedirect />}
        />


        {/* ===================== */}
        {/* 비로그인도 접근 가능 */}
        {/* ===================== */}

        <Route
          path="/login"
          element={<LoginPage />}
        />

        <Route
          path="/register"
          element={<RegisterPage />}
        />


        {/* ===================== */}
        {/* 로그인 사용자 */}
        {/* ===================== */}

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


        {/* ===================== */}
        {/* 관리자 전용 */}
        {/* ===================== */}

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


        {/* ===================== */}
        {/* 권한 없음 */}
        {/* ===================== */}

        <Route
          path="/forbidden"
          element={<ForbiddenPage />}
        />


        {/* ===================== */}
        {/* 없는 주소 */}
        {/* ===================== */}

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