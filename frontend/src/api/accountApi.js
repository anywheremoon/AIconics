const API_BASE_URL = "http://127.0.0.1:8000";

export async function getMyAccount(token) {
  const response = await fetch(
    `${API_BASE_URL}/api/accounts/me`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error("계좌 정보를 불러오지 못했습니다.");
  }

  return response.json();
}

export async function getTransactions(token) {
  const response = await fetch(
    `${API_BASE_URL}/api/transactions`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error("거래 내역을 불러오지 못했습니다.");
  }

  return response.json();
}