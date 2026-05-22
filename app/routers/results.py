import json
from fastapi import APIRouter, HTTPException
from app.database import db

router = APIRouter(prefix="/results", tags=["results"])


@router.get("/")
async def list_all_runs():
    """List all test runs with their summary."""
    runs = await db.testrun.find_many(order={"createdAt": "desc"})
    return {
        "total_runs": len(runs),
        "runs": [
            {
                "run_id": r.id,
                "filename": r.filename,
                "total_test_cases": r.total,
                "status": r.status,
                "created_at": r.createdAt
            }
            for r in runs
        ]
    }


@router.get("/{run_id}")
async def get_result(run_id: int):
    """Get full test results for a specific run including all generated test cases."""
    run = await db.testrun.find_unique(where={"id": run_id})
    if not run:
        raise HTTPException(status_code=404, detail=f"No test run found with id {run_id}")

    results = await db.testresult.find_many(
        where={"runId": run_id},
        order={"id": "asc"}
    )

    return {
        "run_id": run.id,
        "filename": run.filename,
        "status": run.status,
        "total": run.total,
        "created_at": run.createdAt,
        "test_cases": [
            {
                "id": r.id,
                "title": r.title,
                "steps": json.loads(r.steps),
                "expected_result": r.expectedResult,
                "type": r.type,
                "created_at": r.createdAt
            }
            for r in results
        ]
    }


@router.get("/{run_id}/execution")
async def get_execution_history(run_id: int):
    """
    Get all execution history for a test run.
    Returns every time this run was executed, newest first.
    """
    run = await db.testrun.find_unique(where={"id": run_id})
    if not run:
        raise HTTPException(status_code=404, detail=f"No test run found with id {run_id}")

    execution_runs = await db.executionrun.find_many(
        where={"runId": run_id},
        order={"createdAt": "desc"}
    )

    if not execution_runs:
        return {
            "run_id": run_id,
            "filename": run.filename,
            "total_executions": 0,
            "executions": []
        }

    executions = []
    for er in execution_runs:
        exec_results = await db.executionresult.find_many(
            where={"executionRunId": er.id},
            order={"id": "asc"}
        )
        executions.append({
            "execution_run_id": er.id,
            "base_url": er.baseUrl,
            "summary": {
                "total": er.total,
                "executed": er.executed,
                "passed": er.passed,
                "failed": er.failed,
                "not_run": er.notRun
            },
            "stopped_early": er.stoppedEarly,
            "executed_at": er.createdAt,
            "test_case_results": [
                {
                    "title": r.title,
                    "passed": r.passed,
                    "type": r.type,
                    "expected_result": r.expectedResult,
                    "agent_output": r.agentOutput,
                    "step_results": json.loads(r.stepResults)
                }
                for r in exec_results
            ]
        })

    return {
        "run_id": run_id,
        "filename": run.filename,
        "total_executions": len(executions),
        "executions": executions
    }


@router.get("/{run_id}/execution/latest")
async def get_latest_execution(run_id: int):
    """
    Get only the most recent execution for a test run.
    """
    run = await db.testrun.find_unique(where={"id": run_id})
    if not run:
        raise HTTPException(status_code=404, detail=f"No test run found with id {run_id}")

    execution_runs = await db.executionrun.find_many(
        where={"runId": run_id},
        order={"createdAt": "desc"},
        take=1
    )

    if not execution_runs:
        raise HTTPException(status_code=404, detail=f"No execution history found for run {run_id}")

    er = execution_runs[0]
    exec_results = await db.executionresult.find_many(
        where={"executionRunId": er.id},
        order={"id": "asc"}
    )

    return {
        "run_id": run_id,
        "filename": run.filename,
        "execution_run_id": er.id,
        "base_url": er.baseUrl,
        "summary": {
            "total": er.total,
            "executed": er.executed,
            "passed": er.passed,
            "failed": er.failed,
            "not_run": er.notRun
        },
        "stopped_early": er.stoppedEarly,
        "executed_at": er.createdAt,
        "test_case_results": [
            {
                "title": r.title,
                "passed": r.passed,
                "type": r.type,
                "expected_result": r.expectedResult,
                "agent_output": r.agentOutput,
                "step_results": json.loads(r.stepResults)
            }
            for r in exec_results
        ]
    }


@router.delete("/{run_id}")
async def delete_run(run_id: int):
    """Delete a test run and all its test cases and execution history."""
    run = await db.testrun.find_unique(where={"id": run_id})
    if not run:
        raise HTTPException(status_code=404, detail=f"No test run found with id {run_id}")

    # Delete execution results → execution runs → test results → test run (order matters for FK)
    execution_runs = await db.executionrun.find_many(where={"runId": run_id})
    for er in execution_runs:
        await db.executionresult.delete_many(where={"executionRunId": er.id})
    await db.executionrun.delete_many(where={"runId": run_id})
    await db.testresult.delete_many(where={"runId": run_id})
    await db.testrun.delete(where={"id": run_id})

    return {"message": f"Run {run_id} and all its test cases and execution history deleted successfully"}