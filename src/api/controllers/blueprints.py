"""Blueprints controller for thread management."""

from __future__ import annotations

import logging

from fastapi import APIRouter, status

from api.controllers.dependencies import BlueprintsServiceDep
from api.schemas.errors import ProblemDetails
from api.schemas.response import InterruptResponseDto, ThreadItemDto, ThreadResponseDto
from api.schemas.thread import ResumeInputDto, ThreadMessageInputDto

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/blueprints", tags=["Blueprints Agent"])


@router.post(
    "/start",
    response_model=ThreadResponseDto | InterruptResponseDto,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new blueprint generation thread",
    description=(
        "Starts a new thread and routes the user's initial message through the supervisor. "
        "May return an InterruptResponseDto if the graph pauses for user confirmation."
    ),
    responses={
        422: {"description": "Validation error", "model": ProblemDetails},
        500: {"description": "Internal error", "model": ProblemDetails},
    },
)
async def start_thread(
    request: ThreadMessageInputDto,
    service: BlueprintsServiceDep,
) -> ThreadResponseDto | InterruptResponseDto:
    """Start a new thread with an initial message."""
    logger.info("Received thread start request")
    return await service.start(request)


@router.post(
    "/{thread_id}/continue",
    response_model=ThreadResponseDto | InterruptResponseDto,
    status_code=status.HTTP_200_OK,
    summary="Continue a thread",
    description=(
        "Send a new message to an existing thread. "
        "The message is routed through the supervisor for intent re-evaluation. "
        "Use this for normal conversation turns (ask, design). "
        "May return an InterruptResponseDto if the graph pauses for user confirmation."
    ),
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
) -> ThreadResponseDto | InterruptResponseDto:
    """Continue an existing thread with a new message routed through the supervisor."""
    logger.info("Received continue request for thread %s", thread_id)
    return await service.continue_thread(thread_id, request)


@router.post(
    "/{thread_id}/resume",
    response_model=ThreadResponseDto | InterruptResponseDto,
    status_code=status.HTTP_200_OK,
    summary="Resume an interrupted thread",
    description=(
        "Resume a thread that is paused at a graph interrupt (e.g. waiting for "
        "the user to confirm or correct a generation plan). Accepts either a "
        "structured HumanResponse (type + args) or a plain-text message. "
        "May return another InterruptResponseDto if the graph pauses again."
    ),
    responses={
        404: {"description": "Thread not found or no pending interrupt", "model": ProblemDetails},
        422: {"description": "Validation error", "model": ProblemDetails},
        500: {"description": "Internal error", "model": ProblemDetails},
    },
)
async def resume_thread(
    thread_id: str,
    request: ResumeInputDto,
    service: BlueprintsServiceDep,
) -> ThreadResponseDto | InterruptResponseDto:
    """Resume a thread from a graph interrupt with the user's response."""
    logger.info("Received resume request for thread %s", thread_id)
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
    response_model=ThreadResponseDto | InterruptResponseDto,
    status_code=status.HTTP_200_OK,
    summary="Get thread status",
    description=(
        "Retrieve the current state and messages of a specific thread. "
        "Returns an InterruptResponseDto if the thread is paused at an interrupt."
    ),
    responses={
        404: {"description": "Thread not found", "model": ProblemDetails},
    },
)
async def get_thread(
    thread_id: str,
    service: BlueprintsServiceDep,
) -> ThreadResponseDto | InterruptResponseDto:
    """Get the specific thread by ID."""
    logger.info("Getting thread %s", thread_id)
    return await service.get_thread(thread_id)
