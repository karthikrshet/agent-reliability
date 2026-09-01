"""
Projects and Agent definitions management router.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from arl.core.storage.models import AgentDefinitionModel, AgentVersionModel, ProjectModel
from arl.server.db import get_db_session

router = APIRouter(prefix="/api/v1/projects", tags=["Projects"])


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=80)
    description: str = Field(default="", max_length=2000)


class ProjectResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    created_at: datetime


class CreateAgentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    framework: str = Field(..., min_length=1, max_length=60)  # http, langgraph, mock
    description: str = Field(default="", max_length=2000)
    version_tag: str = Field(default="1.0.0", max_length=64)
    endpoint_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    id: str
    project_id: str
    name: str
    framework: str
    description: str
    latest_version_id: str | None = None
    version_tag: str | None = None
    created_at: datetime


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    req: CreateProjectRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    """Create a new project workspace."""
    proj_id = f"proj-{uuid.uuid4().hex[:12]}"
    slug = req.slug or req.name.lower().replace(" ", "-")

    proj = ProjectModel(
        id=proj_id,
        name=req.name,
        slug=slug,
        description=req.description,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(proj)
    await session.commit()
    await session.refresh(proj)

    return ProjectResponse(
        id=proj.id,
        name=proj.name,
        slug=proj.slug,
        description=proj.description,
        created_at=proj.created_at,
    )


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    session: AsyncSession = Depends(get_db_session),
) -> list[ProjectResponse]:
    """List all projects."""
    stmt = select(ProjectModel).order_by(ProjectModel.created_at.desc())
    res = await session.execute(stmt)
    projects = res.scalars().all()

    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            slug=p.slug,
            description=p.description,
            created_at=p.created_at,
        )
        for p in projects
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    """Get project by ID."""
    stmt = select(ProjectModel).where(ProjectModel.id == project_id)
    res = await session.execute(stmt)
    proj = res.scalar_one_or_none()

    if proj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    return ProjectResponse(
        id=proj.id,
        name=proj.name,
        slug=proj.slug,
        description=proj.description,
        created_at=proj.created_at,
    )


@router.post(
    "/{project_id}/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED
)
async def register_agent(
    project_id: str,
    req: CreateAgentRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AgentResponse:
    """Register an agent definition and initial version under a project."""
    # Verify project exists
    proj_stmt = select(ProjectModel).where(ProjectModel.id == project_id)
    proj_res = await session.execute(proj_stmt)
    if proj_res.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    agent_id = f"ad-{uuid.uuid4().hex[:12]}"
    version_id = f"av-{uuid.uuid4().hex[:12]}"

    meta = req.metadata.copy()
    if req.endpoint_url:
        meta["endpoint_url"] = req.endpoint_url

    agent = AgentDefinitionModel(
        id=agent_id,
        project_id=project_id,
        name=req.name,
        framework=req.framework,
        description=req.description,
        created_at=datetime.now(UTC),
    )
    version = AgentVersionModel(
        id=version_id,
        agent_definition_id=agent_id,
        version_tag=req.version_tag,
        metadata_=meta,
        created_at=datetime.now(UTC),
    )

    session.add(agent)
    session.add(version)
    await session.commit()
    await session.refresh(agent)

    return AgentResponse(
        id=agent.id,
        project_id=agent.project_id,
        name=agent.name,
        framework=agent.framework,
        description=agent.description,
        latest_version_id=version_id,
        version_tag=req.version_tag,
        created_at=agent.created_at,
    )


@router.get("/{project_id}/agents", response_model=list[AgentResponse])
async def list_agents(
    project_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> list[AgentResponse]:
    """List agents registered in a project."""
    stmt = (
        select(AgentDefinitionModel)
        .where(AgentDefinitionModel.project_id == project_id)
        .order_by(AgentDefinitionModel.created_at.desc())
    )
    res = await session.execute(stmt)
    agents = res.scalars().all()

    return [
        AgentResponse(
            id=a.id,
            project_id=a.project_id,
            name=a.name,
            framework=a.framework,
            description=a.description,
            created_at=a.created_at,
        )
        for a in agents
    ]
