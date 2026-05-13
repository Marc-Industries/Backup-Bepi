from datetime import datetime

from pydantic import BaseModel, ConfigDict

from bepi.core.enums import BudgetType, MarginStatus, Maturity


class BudgetAllocationCreate(BaseModel):
    node_id: int
    budget_type: BudgetType
    operating_mode_id: int | None = None
    nominal_value: float
    unit: str
    margin_pct: float = 0.0
    maturity: Maturity = Maturity.ESTIMATE
    source: str | None = None
    notes: str | None = None


class BudgetAllocationUpdate(BaseModel):
    budget_type: BudgetType | None = None
    operating_mode_id: int | None = None
    nominal_value: float | None = None
    unit: str | None = None
    margin_pct: float | None = None
    maturity: Maturity | None = None
    source: str | None = None
    notes: str | None = None


class BudgetAllocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    node_id: int
    budget_type: BudgetType
    operating_mode_id: int | None = None
    nominal_value: float
    unit: str
    margin_pct: float
    maturity: Maturity
    source: str | None = None
    notes: str | None = None
    value_with_margin: float
    created_at: datetime
    updated_at: datetime


class BudgetLimitCreate(BaseModel):
    mission_id: int
    budget_type: BudgetType
    operating_mode_id: int | None = None
    limit_value: float
    unit: str


class BudgetLimitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mission_id: int
    budget_type: BudgetType
    operating_mode_id: int | None = None
    limit_value: float
    unit: str
    created_at: datetime
    updated_at: datetime


class BudgetLineItem(BaseModel):
    node_id: int
    node_code: str
    node_name: str
    nominal_value: float
    value_with_margin: float
    unit: str
    margin_pct: float
    maturity: Maturity


class BudgetSummaryResponse(BaseModel):
    mission_id: int
    budget_type: BudgetType
    operating_mode_id: int | None = None
    unit: str
    total_nominal: float
    total_with_margin: float
    limit_value: float | None = None
    margin_status: MarginStatus | None = None
    items: list[BudgetLineItem]


class BudgetRollupNode(BaseModel):
    node_id: int
    node_code: str
    node_name: str
    nominal_value: float
    value_with_margin: float
    unit: str
    children: list[BudgetRollupNode] = []


BudgetRollupNode.model_rebuild()


class BudgetRollupResponse(BaseModel):
    mission_id: int
    budget_type: BudgetType
    operating_mode_id: int | None = None
    unit: str
    tree: list[BudgetRollupNode]
