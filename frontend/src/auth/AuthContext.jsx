import {
  createContext,
  useContext,
  useEffect,
  useState,
} from "react";

import {
  AuthApiError,
  LOGIN_STATUS,
  normalizeLoginResult,
  getCurrentUser,
  sendAgentAuth,
  clearAgentAuth,
  logoutSession,
} from "../api/authApi.js";

const AuthContext = createContext(null);

function removeSavedLogin() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("session_id");
  localStorage.removeItem("agent_session_id");
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // 추가 인증·보류 정보. 일반 로그인 정보와 분리한다.
  const [pendingLogin, setPendingLogin] = useState(null);

  // 기존 로그인 상태 복원
  useEffect(() => {
    let cancelled = false;

    const restoreLogin = async () => {
      const savedToken =
        localStorage.getItem("access_token");

      const savedSessionId =
        localStorage.getItem("session_id");

      if (!savedToken || !savedSessionId) {
        removeSavedLogin();

        if (!cancelled) {
          setLoading(false);
        }

        return;
      }

      try {
        const currentUser = await getCurrentUser();

        if (cancelled) {
          return;
        }

        setToken(savedToken);
        setSessionId(savedSessionId);
        setUser(currentUser);

        // 서버에서 기존 인증을 확인한 후 Agent에 전달한다.
        await sendAgentAuth(
          savedToken,
          savedSessionId
        );
      } catch (error) {
        if (cancelled) {
          return;
        }

        // 만료·종료된 인증은 프론트와 Agent에서 제거한다.
        // 서버 연결 오류일 때는 저장값을 유지해 재시도가 가능하게 한다.
        if (
          error.status === 401 ||
          error.status === 403
        ) {
          removeSavedLogin();
          await clearAgentAuth();
        }

        setToken(null);
        setSessionId(null);
        setUser(null);
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    restoreLogin();

    return () => {
      cancelled = true;
    };
  }, []);

  // 최종 로그인 완료 처리
  const saveLogin = async (result) => {
    if (loading) {
      throw new AuthApiError(
        "로그인 상태 확인 중입니다. 잠시 후 다시 시도해주세요.",
        409
      );
    }

    const normalized = normalizeLoginResult(result);

    if (
      normalized.login_status !==
      LOGIN_STATUS.AUTHENTICATED
    ) {
      throw new AuthApiError(
        "추가 인증 또는 보류 상태에서는 로그인을 완료할 수 없습니다.",
        403
      );
    }

    localStorage.setItem(
      "access_token",
      normalized.access_token
    );

    localStorage.setItem(
      "session_id",
      normalized.session_id
    );

    localStorage.removeItem("agent_session_id");

    setToken(normalized.access_token);
    setSessionId(normalized.session_id);
    setUser(normalized.user);
    setPendingLogin(null);

    const agentConnected = await sendAgentAuth(
      normalized.access_token,
      normalized.session_id
    );

    return { agentConnected };
  };

  // 추가 인증·로그인 보류 상태 저장
  const savePendingLogin = async (result) => {
    if (loading) {
      throw new AuthApiError(
        "로그인 상태 확인 중입니다. 잠시 후 다시 시도해주세요.",
        409
      );
    }

    // 기존 로그인 세션을 남겨둔 채 계정을 전환하지 않는다.
    if (
      token ||
      user ||
      localStorage.getItem("access_token")
    ) {
      throw new AuthApiError(
        "기존 계정에서 로그아웃한 후 다시 로그인해주세요.",
        409
      );
    }

    const normalized = normalizeLoginResult(result);

    if (
      normalized.login_status !==
        LOGIN_STATUS.REQUIRE_VERIFICATION &&
      normalized.login_status !==
        LOGIN_STATUS.PENDING_REVIEW
    ) {
      throw new AuthApiError(
        "인증 대기 또는 보류 응답이 아닙니다.",
        400
      );
    }

    // 이전 Agent 인증이 남아 있으면 제거한다.
    const agentCleared = await clearAgentAuth();

    removeSavedLogin();

    setToken(null);
    setSessionId(null);
    setUser(null);

    setPendingLogin({
      login_status: normalized.login_status,
      requires_verification:
        normalized.requires_verification,
      verification_token:
        normalized.verification_token,
      session_id: normalized.session_id,
      reason_codes: normalized.reason_codes,
      device_trust_status:
        normalized.device_trust_status,
    });

    return { agentCleared };
  };

  // 인증 대기 화면에서 다시 로그인할 때 사용한다.
  // 서버의 대기 세션 취소는 A의 취소 API가 있어야 별도로 처리할 수 있다.
  const clearPendingLogin = () => {
    setPendingLogin(null);
  };

  // 로그아웃
  const logout = async () => {
    const accessToken =
      token || localStorage.getItem("access_token");

    const currentSessionId =
      sessionId || localStorage.getItem("session_id");

    if (accessToken || currentSessionId) {
      // 서버 세션 종료 실패 시 기존 인증정보를 유지한다.
      await logoutSession(
        accessToken,
        currentSessionId
      );
    }

    const agentCleared = await clearAgentAuth();

    removeSavedLogin();

    setToken(null);
    setSessionId(null);
    setUser(null);
    setPendingLogin(null);

    return { agentCleared };
  };

  return (
    <AuthContext.Provider
      value={{
        loading,
        token,
        sessionId,
        user,
        pendingLogin,

        isAuthenticated: Boolean(
          token && sessionId && user
        ),

        login: saveLogin,
        savePendingLogin,
        clearPendingLogin,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth는 AuthProvider 내부에서 사용해야 합니다."
    );
  }

  return context;
}