import {
  createContext,
  useContext,
  useEffect,
  useState
} from "react";

import {
  getCurrentUser,
  sendAgentAuth,
  clearAgentAuth
} from "../api/authApi.js";


const AuthContext =
  createContext(null);


export function AuthProvider({
  children
}) {

  const [token, setToken] =
    useState(
      localStorage.getItem(
        "access_token"
      )
    );


  const [sessionId, setSessionId] =
    useState(
      localStorage.getItem(
        "session_id"
      )
    );


  const [user, setUser] =
    useState(null);


  const [loading, setLoading] =
    useState(true);


  // ==========================================
  // 로그인 상태 복원
  // ==========================================

  useEffect(() => {

    const restoreLogin = async () => {

      const savedToken =
        localStorage.getItem(
          "access_token"
        );


      const savedSessionId =
        localStorage.getItem(
          "session_id"
        );


      if (!savedToken) {

        setLoading(false);

        return;
      }


      try {

        const currentUser =
          await getCurrentUser();


        setToken(
          savedToken
        );


        setSessionId(
          savedSessionId || null
        );


        setUser(
          currentUser
        );


        // 브라우저 새로고침 또는
        // Agent 재실행 시 인증정보 재전달
        if (
          savedToken &&
          savedSessionId
        ) {

          await sendAgentAuth(
            savedToken,
            savedSessionId
          );
        }


      } catch (error) {

        localStorage.removeItem(
          "access_token"
        );

        localStorage.removeItem(
          "session_id"
        );


        setToken(null);

        setSessionId(null);

        setUser(null);


      } finally {

        setLoading(false);
      }
    };


    restoreLogin();

  }, []);


  // ==========================================
  // 로그인 성공 처리
  // ==========================================

  const saveLogin = async (
    result
  ) => {

    // JWT 저장
    localStorage.setItem(
      "access_token",
      result.access_token
    );


    setToken(
      result.access_token
    );


    // Session ID 저장
    if (result.session_id) {

      localStorage.setItem(
        "session_id",
        result.session_id
      );


      setSessionId(
        result.session_id
      );

    } else {

      localStorage.removeItem(
        "session_id"
      );


      setSessionId(null);
    }


    // 사용자 정보 저장
    setUser(
      result.user
    );


    // --------------------------------------
    // Agent에 인증정보 전달
    // --------------------------------------

    if (
      result.access_token &&
      result.session_id
    ) {

      await sendAgentAuth(
        result.access_token,
        result.session_id
      );
    }
  };


  // ==========================================
  // 로그아웃
  // ==========================================

  const logout = async () => {

    // Agent 인증정보 먼저 제거
    await clearAgentAuth();


    // Frontend 인증정보 제거
    localStorage.removeItem(
      "access_token"
    );

    localStorage.removeItem(
      "session_id"
    );


    setToken(null);

    setSessionId(null);

    setUser(null);
  };


  return (
    <AuthContext.Provider
      value={{
        loading,
        token,
        sessionId,
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

  return useContext(
    AuthContext
  );
}