import { useState } from "react";
import EthVaultPage from "./pages/EthVaultPage";
import AdminEthVaultPage from "./pages/AdminEthVaultPage";

export default function EthVaultTest() {
  const [screen, setScreen] = useState("user");

  return (
    <>
      <div className="ev-page ev-actions">
        <button onClick={() => setScreen("user")}>
          사용자 화면
        </button>

        <button onClick={() => setScreen("admin")}>
          관리자 화면
        </button>
      </div>

      {screen === "user"
        ? <EthVaultPage key="user" />
        : <AdminEthVaultPage key="admin" />}
    </>
  );
}