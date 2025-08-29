from __future__ import annotations

from typing import Any, Dict

from .base import BaseAgent


class OrchestratorAgent(BaseAgent):
    """Routes intents to specialized agents.

    The real implementation would combine rule based checks and model
    predictions to choose an intent and call the matching agent. For now it
    simply echoes the provided intent.
    """

    def __init__(self, agents: Dict[str, BaseAgent]) -> None:
        super().__init__("orchestrator")
        self.agents = agents

    async def handle(self, intent: str, *args: Any, **kwargs: Any) -> Any:
        agent = self.agents.get(intent)
        if agent is None:
            return {"intent": intent, "message": "Unknown intent"}
        return await agent.handle(*args, **kwargs)
