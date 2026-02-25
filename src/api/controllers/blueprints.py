"""Blueprints controller for thread management."""

from __future__ import annotations

import logging

from fastapi import APIRouter, status

from api.controllers.dependencies import BlueprintsServiceDep
from api.schemas.errors import ProblemDetails
from api.schemas.response import ThreadItemDto, ThreadResponseDto
from api.schemas.thread import ThreadMessageInputDto

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/blueprints", tags=["Blueprints Agent"])


@router.post(
    "/start",
    response_model=ThreadResponseDto,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new blueprint generation thread",
    description="Starts a new thread and routes the user's initial message through the supervisor.",
    responses={
        422: {"description": "Validation error", "model": ProblemDetails},
        500: {"description": "Internal error", "model": ProblemDetails},
    },
)
async def start_thread(
    request: ThreadMessageInputDto,
    service: BlueprintsServiceDep,
) -> ThreadResponseDto:
    """Start a new thread with an initial message."""
    logger.info("Received thread start request")
    return await service.start(request)


@router.post(
    "/{thread_id}/continue",
    response_model=ThreadResponseDto,
    status_code=status.HTTP_200_OK,
    summary="Continue a thread",
    description="Send a message to an existing thread.",
    responses={
        404: {"description": "Thread not found", "model": ProblemDetails},
        422: {"description": "Validation error", "model": ProblemDetails},
        500: {"description": "Internal error", "model": ProblemDetails},
    },
)
async def continue_thread(
    thread_id: str,
    request: ThreadMessageInputDto,
    service: BlueprintsServiceDep,
) -> ThreadResponseDto:
    """Continue an existing thread."""
    logger.info(f"Received continue request for thread {thread_id}")
    return await service.continue_thread(thread_id, request)


@router.post(
    "/{thread_id}/resume",
    response_model=ThreadResponseDto,
    status_code=status.HTTP_200_OK,
    summary="Resume a thread",
    description="Resume a paused or interrupted thread flow.",
    responses={
        404: {"description": "Thread not found", "model": ProblemDetails},
        422: {"description": "Validation error", "model": ProblemDetails},
        500: {"description": "Internal error", "model": ProblemDetails},
    },
)
async def resume_thread(
    thread_id: str,
    request: ThreadMessageInputDto,
    service: BlueprintsServiceDep,
) -> ThreadResponseDto:
    """Resume an existing thread."""
    logger.info(f"Received resume request for thread {thread_id}")
    return await service.resume(thread_id, request)


@router.get(
    "/threads",
    response_model=list[ThreadItemDto],
    status_code=status.HTTP_200_OK,
    summary="List all threads",
    description="Retrieve a list of all blueprint generation threads.",
)
async def get_threads(
    service: BlueprintsServiceDep,
) -> list[ThreadItemDto]:
    """Retrieve all tracked threads."""
    logger.info("Listing all threads")
    return await service.get_threads()


@router.get(
    "/threads/{thread_id}",
    response_model=ThreadResponseDto,
    status_code=status.HTTP_200_OK,
    summary="Get thread status",
    description="Retrieve the current state and messages of a specific thread.",
    responses={
        404: {"description": "Thread not found", "model": ProblemDetails},
    },
)
async def get_thread(
    thread_id: str,
    service: BlueprintsServiceDep,
) -> ThreadResponseDto:
    """Get the specific thread by ID."""
    logger.info(f"Getting thread {thread_id}")
    return await service.get_thread(thread_id)
