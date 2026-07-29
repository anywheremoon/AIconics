import { useEffect, useMemo, useState } from 'react';

import { getSuspiciousUsers } from '../api/riskApi.js';
import SuspiciousUserTable from '../components/SuspiciousUserTable.jsx';

function SuspiciousUsersPage() {
    const [users, setUsers] = useState([]);
    const [keyword, setKeyword] = useState('');
    const [riskLevel, setRiskLevel] = useState('ALL');
    const [sortOrder, setSortOrder] = useState('DESC');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        const fetchSuspiciousUsers = async () => {
            setLoading(true);
            setError('');

            try {
                const data = await getSuspiciousUsers();

                if (!Array.isArray(data)) {
                    throw new Error(
                        '의심 사용자 응답 형식이 올바르지 않습니다.',
                    );
                }

                // 백엔드 snake_case 데이터를 프론트 camelCase로 변환
                const formattedUsers = data.map((user) => ({
                    id: user.id,
                    userId: user.user_id,
                    deviceId: user.device_id,
                    riskScore: user.risk_score,
                    riskLevel: user.risk_level,
                    lastDetectedAt: user.created_at,
                }));

                setUsers(formattedUsers);
            } catch (requestError) {
                console.error('의심 사용자 조회 오류:', requestError);

                setUsers([]);
                setError(
                    requestError.message ||
                        '백엔드 서버에서 의심 사용자 목록을 불러오지 못했습니다.',
                );
            } finally {
                setLoading(false);
            }
        };

        fetchSuspiciousUsers();
    }, []);

    const filteredUsers = useMemo(() => {
        const searchKeyword = keyword.trim().toLowerCase();

        return [...users]
            .filter((user) => {
                const userId = String(user.userId ?? '').toLowerCase();

                // 검색어가 비어 있으면 전체 표시
                // 검색어가 있으면 정확히 일치하는 사용자만 표시
                const matchesKeyword =
                    searchKeyword === '' || userId === searchKeyword;

                const matchesRiskLevel =
                    riskLevel === 'ALL' || user.riskLevel === riskLevel;

                return matchesKeyword && matchesRiskLevel;
            })
            .sort((a, b) => {
                const firstScore = Number(a.riskScore ?? 0);
                const secondScore = Number(b.riskScore ?? 0);

                if (sortOrder === 'ASC') {
                    return firstScore - secondScore;
                }

                return secondScore - firstScore;
            });
    }, [users, keyword, riskLevel, sortOrder]);

    const handleUserSelect = (user) => {
        window.alert(`${user.userId}의 행동 로그를 확인합니다.`);
    };

    return (
        <main className="page-container">
            <div className="page-header">
                <div>
                    <h1 className="page-title">의심 사용자 목록</h1>

                    <p className="page-description">
                        리스크 점수가 높은 사용자를 검색하고 확인할 수 있습니다.
                    </p>
                </div>
            </div>

            {error && <p className="error-message">{error}</p>}

            <section className="filter-panel">
                <label>
                    <span>사용자 검색</span>

                    <input
                        type="search"
                        value={keyword}
                        placeholder="사용자 ID 입력"
                        onChange={(event) => setKeyword(event.target.value)}
                    />
                </label>

                <label>
                    <span>위험 등급</span>

                    <select
                        value={riskLevel}
                        onChange={(event) => setRiskLevel(event.target.value)}
                    >
                        <option value="ALL">전체</option>
                        <option value="LOW">정상</option>
                        <option value="MEDIUM">주의</option>
                        <option value="HIGH">위험</option>
                    </select>
                </label>

                <label>
                    <span>점수 정렬</span>

                    <select
                        value={sortOrder}
                        onChange={(event) => setSortOrder(event.target.value)}
                    >
                        <option value="DESC">높은 순</option>
                        <option value="ASC">낮은 순</option>
                    </select>
                </label>
            </section>

            {loading ? (
                <p className="loading-message">
                    의심 사용자 목록을 불러오는 중입니다.
                </p>
            ) : (
                <SuspiciousUserTable
                    users={filteredUsers}
                    onUserSelect={handleUserSelect}
                />
            )}
        </main>
    );
}

export default SuspiciousUsersPage;
     