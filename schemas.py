from typing import List, Optional
from pydantic import BaseModel

class QuestionAddRequest(BaseModel):
    category_id: int
    location_id: Optional[int] = None
    event_year_month: Optional[str] = None
    gk_question: str
    complexity: Optional[float] = None
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str
    gk_answer: Optional[str] = None
    marks: int = 1
    creation_date: Optional[str] = None

class QuestionUpdateRequest(BaseModel):
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    event_year_month: Optional[str] = None
    gk_question: Optional[str] = None
    complexity: Optional[float] = None
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct_answer: Optional[str] = None
    gk_answer: Optional[str] = None
    marks: Optional[int] = None
    status: Optional[str] = None
    creation_date: Optional[str] = None

class CategoryCreate(BaseModel):
    category_name: str
    description: Optional[str] = None
    status: int = 1

class CategoryUpdate(BaseModel):
    category_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[int] = None

class CategoryResponse(BaseModel):
    category_id: int
    category_name: str
    description: Optional[str] = None
    status: int

class AssessmentStartRequest(BaseModel):
    user_id: int
    assessment_type: str = "40M Standard"
    creation_mode: str = "Normal"
    category_ids: Optional[List[int]] = []

class AreaOfFocusItem(BaseModel):
    category_id: int
    percentage: float

class ProfileUpdate(BaseModel):
    area_of_focus: List[AreaOfFocusItem]

class ProfileResponse(BaseModel):
    gk_profile_id: int
    user_id: int
    user_name: Optional[str] = None
    area_of_focus: Optional[List[AreaOfFocusItem]] = None
    creation_date: Optional[str] = None

class UserAssessmentSummaryItem(BaseModel):
    gk_user_ass_id: int
    gk_assessment_id: int
    gk_assessment_name: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_score: int
    correct_count: int
    incorrect_count: int
    skipped_count: int
    accuracy: float
    status: str

class UserAssessmentsSummaryResponse(BaseModel):
    total_assessments: int
    assessments: List[UserAssessmentSummaryItem]

class AnswerSubmit(BaseModel):
    gk_question_id: int
    user_answer: Optional[str] = None # A, B, C, D, or None if skipped
    time_taken_seconds: int = 0

class AssessmentEndRequest(BaseModel):
    answers: List[AnswerSubmit]


