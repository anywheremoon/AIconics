from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth_dependency import require_admin
from app.models.risk_assessment_model import RiskAssessment
from app.services.blockchain_service import (
    BlockchainError,
    get_analysis_hash,
    record_analysis_hash,
)
from app.services.integrity_service import (
    normalize_digest,
    verify_analysis_integrity,
)


router = APIRouter(
    prefix="/api/admin/analyses",
    tags=["Admin Integrity"],
)


def get_analysis_hash_calculator():
    """B의 정식 해시 함수를 연결할 위치."""
    raise HTTPException(
        status_code=503,
        detail="분석 결과 해시 함수 연결 대기 중입니다.",
    )


@router.get("/{analysis_id}/chain-record")
def read_chain_record(
    analysis_id: int = Path(..., gt=0),
    current_admin=Depends(require_admin),
):
    """관리자 전용 블록체인 기록 조회."""
    try:
        record = get_analysis_hash(analysis_id)
    except BlockchainError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "블록체인 기록을 조회할 수 없습니다. "
                "연결 상태를 확인해 주세요."
            ),
        ) from exc

    return {
        **record,
        "status": (
            "RECORDED"
            if record["exists"]
            else "NOT_RECORDED"
        ),
        "message": (
            "블록체인 기록이 있습니다."
            if record["exists"]
            else "블록체인 기록이 없습니다."
        ),
    }


@router.get("/{analysis_id}/integrity")
def check_analysis_integrity(
    analysis_id: int = Path(..., gt=0),
    current_admin=Depends(require_admin),
    db: Session = Depends(get_db),
    calculate_hash=Depends(get_analysis_hash_calculator),
):
    """현재 DB 분석 결과와 블록체인 기록을 비교한다."""
    try:
        assessment = (
            db.query(RiskAssessment)
            .filter(RiskAssessment.id == analysis_id)
            .populate_existing()
            .first()
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="분석 결과를 DB에서 조회하지 못했습니다.",
        ) from exc

    if assessment is None:
        raise HTTPException(
            status_code=404,
            detail="위험 분석 결과를 찾을 수 없습니다.",
        )

    try:
        return verify_analysis_integrity(
            assessment,
            calculate_hash,
        )
    except BlockchainError as exc:
        raise HTTPException(
            status_code=503,
            detail="블록체인 연결 오류로 검증하지 못했습니다.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail="해시 데이터 형식 오류로 검증하지 못했습니다.",
        ) from exc


@router.post("/{analysis_id}/anchor")
def anchor_analysis(
    analysis_id: int = Path(..., gt=0),
    current_admin=Depends(require_admin),
    db: Session = Depends(get_db),
    calculate_hash=Depends(get_analysis_hash_calculator),
):
    """DB 분석 결과를 읽어 계산한 해시를 블록체인에 기록한다."""
    try:
        assessment = (
            db.query(RiskAssessment)
            .filter(RiskAssessment.id == analysis_id)
            .populate_existing()
            .with_for_update()
            .first()
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="분석 결과를 DB에서 조회하지 못했습니다.",
        ) from exc

    if assessment is None:
        raise HTTPException(
            status_code=404,
            detail="위험 분석 결과를 찾을 수 없습니다.",
        )

    try:
        digest = normalize_digest(calculate_hash(assessment))

        if digest == "0x" + "00" * 32:
            raise ValueError("Zero digest is not allowed")

    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail="해시 데이터 형식 오류로 기록하지 못했습니다.",
        ) from exc

    try:
        existing = get_analysis_hash(analysis_id)

        if existing["exists"]:
            try:
                chain_digest = normalize_digest(existing["digest"])
            except ValueError as exc:
                raise HTTPException(
                    status_code=500,
                    detail="블록체인 해시 형식이 올바르지 않습니다.",
                ) from exc

            same_transaction = (
                existing["transaction_id"]
                == assessment.transaction_id
            )
            same_hash = chain_digest == digest

            if not (same_transaction and same_hash):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "기존 블록체인 기록과 현재 DB 데이터가 다릅니다. "
                        "기록을 덮어쓸 수 없습니다."
                    ),
                )

            return {
                "analysis_id": assessment.id,
                "transaction_id": assessment.transaction_id,
                "status": "ALREADY_RECORDED",
                "digest": digest,
                "message": "동일한 데이터가 이미 기록되어 있습니다.",
            }

        recorded = record_analysis_hash(
            assessment.id,
            assessment.transaction_id,
            digest,
        )

        return {
            **recorded,
            "status": "RECORDED",
            "message": "블록체인에 기록했습니다.",
        }

    except BlockchainError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "블록체인 기록 또는 확인에 실패했습니다. "
                "재시도 전에 기록 조회로 반영 여부를 확인해 주세요."
            ),
        ) from exc