from fastapi import APIRouter

from agents import OrchestratorAgent, LostFoundAgent, MealsAgent

router = APIRouter()

# Instantiate core agents and orchestrator
_orchestrator = OrchestratorAgent(
    {
        "LOST": LostFoundAgent(),
        "MEAL": MealsAgent(),
    }
)


@router.post("/chat")
async def chat(intent: str):
    """Very small stub endpoint that routes based on intent string."""
    return await _orchestrator.handle(intent)
