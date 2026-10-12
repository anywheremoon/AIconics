from pydantic import BaseModel, Field


class SecurityGuidanceResponse(BaseModel):
    summary: str = Field(
        ...,
        min_length=1,
        description="로그인 보안 상태에 대한 안내",
    )

    next_action: str = Field(
        ...,
        min_length=1,
        description="사용자가 다음에 수행할 행동",
    )