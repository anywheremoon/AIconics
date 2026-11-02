import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import os

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.event_model import Event
from app.models.user_session_model import UserSession
from app.schemas.risk_transfer_schema import (
    RiskTransferMessage,
    RiskTransferRequest,
    RiskTransferResponse,
)
from app.services.risk_decision_service import decide_risk
from app.services.risk_engine import calculate_risk_score
from app.services.transfer_signature_service import TransferSignatureService


DEFAULT_SIGNATURE_LIFETIME_SECONDS = 300
MAX_SIGNATURE_LIFETIME_SECONDS = 3600
RISK_LEVEL_CODES = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
    "CRITICAL": 3,
}

RiskScoreProvider = Callable[[Session, int, RiskTransferRequest], float]


def _integer_environment(name: str, default: int, *, minimum: int = 0) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as error:
        raise RuntimeError(f"{name} must be an integer") from error
    if value < minimum:
        raise RuntimeError(f"{name} must be at least {minimum}")
    return value


def _address_set_environment(name: str) -> frozenset[str]:
    values = [item.strip().lower() for item in os.getenv(name, "").split(",")]
    addresses = frozenset(item for item in values if item)
    invalid = [
        address
        for address in addresses
        if len(address) != 42
        or not address.startswith("0x")
        or any(character not in "0123456789abcdef" for character in address[2:])
    ]
    if invalid:
        raise RuntimeError(f"{name} contains an invalid Ethereum address")
    return addresses


@dataclass(frozen=True)
class BlockchainTransferRiskPolicy:
    """Transaction-specific policy layered on the existing AIconics engine."""

    token_decimals: int = 18
    elevated_amount_tokens: int = 1_000
    high_amount_tokens: int = 10_000
    critical_amount_tokens: int = 100_000
    trusted_chain_ids: frozenset[int] = frozenset({31337})
    allowed_contracts: frozenset[str] = frozenset()
    blocked_recipients: frozenset[str] = frozenset()

    def __post_init__(self):
        if not 0 <= self.token_decimals <= 77:
            raise ValueError("token_decimals must be between 0 and 77")
        if not (
            0 < self.elevated_amount_tokens
            < self.high_amount_tokens
            < self.critical_amount_tokens
        ):
            raise ValueError("amount thresholds must be positive and increasing")

    @classmethod
    def from_environment(cls) -> "BlockchainTransferRiskPolicy":
        chain_values = [
            item.strip()
            for item in os.getenv("AICONICS_TRUSTED_CHAIN_IDS", "31337").split(",")
            if item.strip()
        ]
        try:
            trusted_chain_ids = frozenset(int(item) for item in chain_values)
        except ValueError as error:
            raise RuntimeError(
                "AICONICS_TRUSTED_CHAIN_IDS must contain integers"
            ) from error
        if not trusted_chain_ids or any(chain_id <= 0 for chain_id in trusted_chain_ids):
            raise RuntimeError(
                "AICONICS_TRUSTED_CHAIN_IDS must contain positive chain IDs"
            )
        return cls(
            token_decimals=_integer_environment(
                "AICONICS_TOKEN_DECIMALS", 18, minimum=0
            ),
            elevated_amount_tokens=_integer_environment(
                "AICONICS_ELEVATED_AMOUNT_TOKENS", 1_000, minimum=1
            ),
            high_amount_tokens=_integer_environment(
                "AICONICS_HIGH_AMOUNT_TOKENS", 10_000, minimum=1
            ),
            critical_amount_tokens=_integer_environment(
                "AICONICS_CRITICAL_AMOUNT_TOKENS", 100_000, minimum=1
            ),
            trusted_chain_ids=trusted_chain_ids,
            allowed_contracts=_address_set_environment(
                "AICONICS_ALLOWED_TRANSFER_CONTRACTS"
            ),
            blocked_recipients=_address_set_environment(
                "AICONICS_BLOCKED_RECIPIENTS"
            ),
        )

    def apply(self, base_score: float, request: RiskTransferRequest) -> float:
        if request.recipient in self.blocked_recipients:
            return 100.0

        score = float(base_score)
        amount = int(request.amount)
        unit = 10**self.token_decimals
        if amount >= self.critical_amount_tokens * unit:
            score = max(score + 60, 85)
        elif amount >= self.high_amount_tokens * unit:
            score = max(score + 35, 70)
        elif amount >= self.elevated_amount_tokens * unit:
            score = max(score + 15, 40)

        if request.chain_id not in self.trusted_chain_ids:
            score += 20
        if (
            self.allowed_contracts
            and request.verifying_contract not in self.allowed_contracts
        ):
            score += 40
        return min(score, 100.0)


def latest_aiconics_risk_score(
    db: Session,
    user_id: int,
    _request: RiskTransferRequest,
) -> float:
    """Re-run the existing engine and score the current blockchain transfer."""
    event = (
        db.query(Event)
        .filter(Event.user_id == str(user_id))
        .order_by(Event.created_at.desc(), Event.id.desc())
        .first()
    )
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk analysis result not found for the authenticated user",
        )
    user_session = db.get(UserSession, event.session_id)
    engine_result = calculate_risk_score(
        {
            "typing_speed": event.typing_speed,
            "avg_hold_time": event.avg_hold_time,
            "avg_flight_time": event.avg_flight_time,
            "total_keystrokes": event.total_keystrokes,
            "mouse_move_count": event.mouse_move_count,
            "click_count": event.click_count,
        },
        {"profile_deviation_score": event.profile_deviation_score},
        device_trust_status=(
            user_session.device_trust_status
            if user_session is not None
            else ("NEW_DEVICE" if event.is_new_device else "TRUSTED_DEVICE")
        ),
        repeated_login_detected=(
            user_session.repeated_login_detected if user_session is not None else False
        ),
        account_switch_detected=(
            user_session.account_switch_detected if user_session is not None else False
        ),
        baseline_status=event.baseline_status,
    )
    # Never lower a previously persisted score merely because historical
    # comparison data is unavailable during this stateless transfer request.
    base_score = max(float(event.risk_score), float(engine_result["risk_score"]))
    return BlockchainTransferRiskPolicy.from_environment().apply(base_score, _request)


def normalize_risk_score(value: float) -> int:
    """Convert engine output to the uint8 integer signed on-chain."""
    if isinstance(value, bool):
        raise ValueError("risk score must be numeric")
    try:
        score = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError("risk score must be numeric") from error
    if not score.is_finite() or score < 0 or score > 100:
        raise ValueError("risk score must be between 0 and 100")
    return int(score.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class RiskTransferService:
    def __init__(
        self,
        signature_service: TransferSignatureService,
        *,
        risk_score_provider: RiskScoreProvider = latest_aiconics_risk_score,
        clock: Callable[[], float] = time.time,
        token_bytes: Callable[[int], bytes] = secrets.token_bytes,
    ):
        self._signature_service = signature_service
        self._risk_score_provider = risk_score_provider
        self._clock = clock
        self._token_bytes = token_bytes

    def assess_and_sign(
        self,
        db: Session,
        *,
        user_id: int,
        request: RiskTransferRequest,
    ) -> RiskTransferResponse:
        now = int(self._clock())
        deadline = request.deadline or now + DEFAULT_SIGNATURE_LIFETIME_SECONDS
        if deadline <= now:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="deadline must be in the future",
            )
        if deadline > now + MAX_SIGNATURE_LIFETIME_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "deadline must not exceed "
                    f"{MAX_SIGNATURE_LIFETIME_SECONDS} seconds from now"
                ),
            )

        risk_score = normalize_risk_score(
            self._risk_score_provider(db, user_id, request)
        )
        decision = decide_risk(risk_score)
        risk_level = decision["risk_level"]
        risk_level_code = RISK_LEVEL_CODES[risk_level]

        request_id = "0x" + self._token_bytes(32).hex()
        nonce = "0x" + self._token_bytes(32).hex()
        message = RiskTransferMessage(
            sender=request.sender,
            recipient=request.recipient,
            amount=request.amount,
            riskScore=risk_score,
            riskLevel=risk_level_code,
            requestId=request_id,
            deadline=deadline,
            nonce=nonce,
        )
        signed = self._signature_service.sign(
            chain_id=request.chain_id,
            verifying_contract=request.verifying_contract,
            message=message,
        )
        return RiskTransferResponse(
            riskScore=risk_score,
            riskLevel=risk_level,
            riskLevelCode=risk_level_code,
            requestId=request_id,
            nonce=nonce,
            deadline=deadline,
            signer=signed.signer,
            signature=signed.signature,
            typedData=signed.typed_data,
        )
