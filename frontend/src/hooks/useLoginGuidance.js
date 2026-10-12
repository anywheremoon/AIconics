import { useEffect, useState } from "react";

import {
  LOGIN_STATUS,
  getLoginGuidance,
} from "../api/authApi.js";


const VERIFICATION_GUIDANCE = {
  summary:
    "안전한 로그인을 위해 추가 인증이 필요합니다.",
  next_action:
    "인증번호를 요청한 후 등록된 인증 수단으로 받은 번호를 입력해주세요.",
};

const PENDING_GUIDANCE = {
  summary:
    "보안 확인이 필요하여 이번 로그인이 보류되었습니다.",
  next_action:
    "본인의 로그인 시도가 아니라면 계정 보안을 확인해주세요. 본인의 시도라면 서비스의 공식 지원 채널을 통해 확인을 요청해주세요.",
};


export function useLoginGuidance(pendingLogin) {
  const loginStatus = pendingLogin?.login_status;
  const verificationToken =
    pendingLogin?.verification_token;
  const sessionId = pendingLogin?.session_id;

  const fallback =
    loginStatus === LOGIN_STATUS.PENDING_REVIEW
      ? PENDING_GUIDANCE
      : VERIFICATION_GUIDANCE;

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setResult(null);
    setLoading(false);

    const supported =
      loginStatus === LOGIN_STATUS.REQUIRE_VERIFICATION ||
      loginStatus === LOGIN_STATUS.PENDING_REVIEW;

    if (
      !supported ||
      !verificationToken ||
      !sessionId
    ) {
      return;
    }

    const controller = new AbortController();
    let active = true;

    const timeoutId = setTimeout(() => {
      controller.abort();
    }, 10000);

    setLoading(true);

    const loadGuidance = async () => {
      try {
        const guidance = await getLoginGuidance(
          verificationToken,
          sessionId,
          controller.signal
        );

        if (active) {
          setResult({
            loginStatus,
            verificationToken,
            sessionId,
            guidance,
          });
        }
      } catch {
        // API 실패·미구현·시간 초과 시 기본 안내 유지
      } finally {
        clearTimeout(timeoutId);

        if (active) {
          setLoading(false);
        }
      }
    };

    loadGuidance();

    return () => {
      active = false;
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, [loginStatus, verificationToken, sessionId]);

  // 이전 로그인 시도의 안내가 표시되지 않도록 확인
  const matchesCurrentLogin =
    result !== null &&
    result.loginStatus === loginStatus &&
    result.verificationToken === verificationToken &&
    result.sessionId === sessionId;

  return {
    guidance: matchesCurrentLogin
      ? result.guidance
      : fallback,

    guidanceLoading: loading,
  };
}