from fastapi import APIRouter, HTTPException

from app.graph.graph_repository import get_transaction_graph
from app.services.graph_risk_engine import analyze_graph_risk

router = APIRouter(
    prefix="/api/graph",
    tags=["Graph"],
)


@router.get("/users/{user_id}")
def get_user_graph_risk(user_id: int):
    return analyze_graph_risk(user_id)

@router.get("/transactions/{transaction_id}")
def get_transaction_graph_detail(transaction_id: int):
    transaction = get_transaction_graph(transaction_id)

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Graph transaction not found",
        )

    return transaction