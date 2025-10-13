# Introduction

This document outlines the overall project architecture for **Minerva**, including backend systems, shared services, and non-UI specific concerns. Its primary goal is to serve as the guiding architectural blueprint for AI-driven development, ensuring consistency and adherence to chosen patterns and technologies.

**Relationship to Frontend Architecture:**
Minerva is a backend-focused system with a CLI interface. There is no web frontend for the MVP. The system operates in two deployment modes: local ingestion (with Playwright + GPT processing) and production API (lightweight query serving).

## Starter Template or Existing Project

**N/A - Greenfield project**

This is a greenfield Python project with no starter template. Given Minerva's unique requirements (Playwright automation, two-environment architecture, screenshot storage, pgvector integration), a custom setup is most appropriate. Standard FastAPI templates would include unnecessary complexity and dependencies.

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-06 | 1.0 | Initial architecture document | Winston (Architect) |
| 2025-10-06 | 1.1 | Added Quality Validation component, Rich library to tech stack, performance expectations clarification, marked Phase 1.5 components | Winston (Architect) |

---
