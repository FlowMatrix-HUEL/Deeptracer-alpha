from pydantic import BaseModel, Field


class StructureAgentResult(BaseModel):
    summary: str = Field(description="One-paragraph structural summary.")
    focus_function: str = Field(description="The function a learner should inspect first.")
    points: list[str] = Field(description="Three concise structure insights.")


class PerformanceAgentResult(BaseModel):
    summary: str = Field(description="Short performance explanation.")
    hottest_function: str = Field(description="Most relevant hotspot.")
    points: list[str] = Field(description="Three concise performance insights.")


class MemoryAgentResult(BaseModel):
    summary: str = Field(description="Short memory explanation.")
    focus_area: str = Field(description="Most relevant memory hotspot.")
    points: list[str] = Field(description="Three concise memory insights.")


class SuggestionItem(BaseModel):
    id: str = Field(description="Stable suggestion id in kebab-case.")
    title: str = Field(description="Short user-facing title.")
    priority: str = Field(description="Priority label.")
    confidence: str = Field(description="Confidence label.")
    impact: str = Field(description="Expected impact.")
    risk: str = Field(description="Risk label.")
    file: str = Field(description="Display file label.")
    note: str = Field(description="One-line note shown in the list.")
    explanation: str = Field(description="Longer explanation for the detail panel.")
    diff: list[list] = Field(description="Diff preview rows as [line, marker, text, kind].")
    based_on_suggestion_id: str = Field(
        default="",
        description="Exact local suggestion id this item is based on, if applicable.",
    )
    anchor_ids: list[str] = Field(
        default_factory=list,
        description="Exact local code-anchor ids relevant to this suggestion.",
    )


class RefactorAgentResult(BaseModel):
    suggestions: list[SuggestionItem] = Field(description="One to three concrete suggestions.")


class TeachingAgentResult(BaseModel):
    overview: str = Field(description="Beginner-friendly overall explanation.")
    beginner_tip: str = Field(description="Practical tip for a beginner.")
    next_step: str = Field(description="Best next action for the user.")
