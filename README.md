# Sphere-PGHS

Prototype multi-agent backend for Pangyo High School's Sphere project.

This repository provides a FastAPI application with a minimal skeleton of
AI agents described in `AGENTS.md`. The current implementation stubs out
agents such as the orchestrator, meals, and lost & found so that student
contributors can progressively add real logic.

## Development

```bash
uvicorn main:app --reload
```

The API currently exposes placeholder endpoints under `/meals`, `/lost`
and `/ai`.
