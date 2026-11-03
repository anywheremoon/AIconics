import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "../api/ethVaultApi";
import { validateVaultInput } from "../utils/ethVaultContract";

export default function useEthVault() {
  const [transfers, setTransfers] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [now, setNow] = useState(Date.now());
  const locked = useRef(false);

  const refresh = useCallback(async () => {
    const rows = await api.listVaultTransfers();
    setTransfers(rows);
  }, []);

  useEffect(() => {
    refresh().catch((err) => setError(err.message));

    const timer = setInterval(() => setNow(Date.now()), 1000);

    const onStorage = () => {
      refresh().catch((err) => setError(err.message));
    };

    window.addEventListener("storage", onStorage);

    return () => {
      clearInterval(timer);
      window.removeEventListener("storage", onStorage);
    };
  }, [refresh]);

  const run = useCallback(async (operation) => {
    if (locked.current) return false;

    locked.current = true;
    setBusy(true);
    setError("");

    try {
      await operation();
      await refresh();
      return true;
    } catch (err) {
      setError(err.message || "처리 중 오류가 발생했습니다.");
      return false;
    } finally {
      locked.current = false;
      setBusy(false);
    }
  }, [refresh]);

  return {
    transfers,
    busy,
    error,
    now,
    refresh: () => run(refresh),

    create: (input) => run(async () => {
      validateVaultInput(input);
      await api.createVaultTransfer(input);
    }),

    completeAuth: (id) => run(() => api.completeVaultAuth(id)),
    approve: (id) => run(() => api.approveVaultTransfer(id)),
    reject: (id) => run(() => api.rejectVaultTransfer(id)),
    execute: (id) => run(() => api.executeVaultTransfer(id)),
    cancelExpired: (id) => run(
      () => api.cancelExpiredVaultTransfer(id)
    ),
  };
}