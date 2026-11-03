import { useEffect, useState } from "react";

export default function useWallet() {
  const [account, setAccount] = useState("");
  const [chainId, setChainId] = useState(null);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const provider = window.ethereum;
    if (!provider) return;

    let mounted = true;

    const onAccountsChanged = (accounts) => {
      if (mounted) setAccount(accounts[0] || "");
    };

    const onChainChanged = (value) => {
      if (mounted) setChainId(Number(value));
    };

    Promise.all([
      provider.request({ method: "eth_accounts" }),
      provider.request({ method: "eth_chainId" }),
    ])
      .then(([accounts, chain]) => {
        if (!mounted) return;
        setAccount(accounts[0] || "");
        setChainId(Number(chain));
      })
      .catch(() => {
        if (mounted) setError("지갑 정보를 가져오지 못했습니다.");
      });

    provider.on("accountsChanged", onAccountsChanged);
    provider.on("chainChanged", onChainChanged);

    return () => {
      mounted = false;
      provider.removeListener("accountsChanged", onAccountsChanged);
      provider.removeListener("chainChanged", onChainChanged);
    };
  }, []);

  async function connect() {
    setError("");

    if (!window.ethereum) {
      setError("MetaMask를 설치한 뒤 다시 시도해 주세요.");
      return;
    }

    setConnecting(true);

    try {
      const accounts = await window.ethereum.request({
        method: "eth_requestAccounts",
      });

      const chain = await window.ethereum.request({
        method: "eth_chainId",
      });

      setAccount(accounts[0] || "");
      setChainId(Number(chain));
    } catch (err) {
      setError(
        err.code === 4001
          ? "지갑 연결 요청을 취소했습니다."
          : "지갑 연결에 실패했습니다."
      );
    } finally {
      setConnecting(false);
    }
  }

  return { account, chainId, connecting, error, connect };
}