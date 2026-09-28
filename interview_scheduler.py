"""CP-SAT interview scheduling example using pandas mock data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from ortools.sat.python import cp_model

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


def build_mock_data() -> tuple[pd.DataFrame, pd.DataFrame, list[str], list[str]]:
    """Build deterministic mock input data in the requested pandas format."""
    time_slots = [
        "08:00-09:00",
        "09:00-10:00",
        "10:00-11:00",
        "11:00-12:00",
        "13:00-14:00",
        "14:00-15:00",
        "15:00-16:00",
    ]
    tables = [f"Table {number}" for number in range(1, 16)]

    candidates = pd.DataFrame(
        [
            {
                "id": 1,
                "name": "Alice",
                "aspirations": [
                    "Multimedia_Photographer",
                    "Multimedia_Editor",
                    "Multimedia_Photographer",
                ],
                "preferred_slots": time_slots[0:4],
            },
            {
                "id": 2,
                "name": "Bao",
                "aspirations": [
                    "Sports_EventOperator",
                    "Multimedia_Designer",
                    "Sports_EventOperator",
                ],
                "preferred_slots": time_slots[1:5],
            },
            {
                "id": 3,
                "name": "Chi",
                "aspirations": [
                    "Volunteers_EventOperator",
                    "Multimedia_ContentWriter",
                    "Volunteers_EventOperator",
                ],
                "preferred_slots": time_slots[1:5],
            },
            {
                "id": 4,
                "name": "Duy",
                "aspirations": [
                    "Academy_EventOperator",
                    "MC_MC",
                    "Sports_EventOperator",
                ],
                "preferred_slots": time_slots[1:5],
            },
            {
                "id": 5,
                "name": "Em",
                "aspirations": [
                    "EntertainmentArts_EventOperator",
                    "Multimedia_Designer",
                    "EntertainmentArts_EventOperator",
                ],
                "preferred_slots": [
                    time_slots[0],
                    time_slots[1],
                    time_slots[4],
                    time_slots[5],
                ],
            },
            {
                "id": 6,
                "name": "Giang",
                "aspirations": [
                    "Multimedia_ContentWriter",
                    "Multimedia_Editor",
                    "Multimedia_ContentWriter",
                ],
                "preferred_slots": [
                    time_slots[0],
                    time_slots[1],
                    time_slots[4],
                    time_slots[5],
                ],
            },
            {
                "id": 7,
                "name": "Hanh",
                "aspirations": [
                    "Sports_EventOperator",
                    "Multimedia_Photographer",
                    "Sports_EventOperator",
                ],
                "preferred_slots": [
                    time_slots[1],
                    time_slots[3],
                    time_slots[5],
                    time_slots[6],
                ],
            },
            {
                "id": 8,
                "name": "Khanh",
                "aspirations": [
                    "MC_MC",
                    "Multimedia_Designer",
                    "MC_MC",
                ],
                "preferred_slots": [
                    time_slots[0],
                    time_slots[2],
                    time_slots[3],
                    time_slots[5],
                ],
            },
        ]
    )

    interviewers = pd.DataFrame(
        [
            {
                "id": 1,
                "name": "Interviewer 1",
                "roles": ["Multimedia_Photographer", "Multimedia_Editor"],
            },
            {
                "id": 2,
                "name": "Interviewer 2",
                "roles": ["Multimedia_ContentWriter", "Multimedia_Designer"],
            },
            {
                "id": 3,
                "name": "Interviewer 3",
                "roles": ["Sports_EventOperator", "Volunteers_EventOperator"],
            },
            {
                "id": 4,
                "name": "Interviewer 4",
                "roles": ["Academy_EventOperator", "EntertainmentArts_EventOperator"],
            },
            {
                "id": 5,
                "name": "Interviewer 5",
                "roles": ["MC_MC", "Multimedia_Designer"],
            },
            {
                "id": 6,
                "name": "Interviewer 6",
                "roles": ["Multimedia_Editor", "Multimedia_ContentWriter"],
            },
            {
                "id": 7,
                "name": "Interviewer 7",
                "roles": ["Sports_EventOperator", "Academy_EventOperator"],
            },
            {
                "id": 8,
                "name": "Interviewer 8",
                "roles": [
                    "Volunteers_EventOperator",
                    "EntertainmentArts_EventOperator",
                ],
            },
            {
                "id": 9,
                "name": "Interviewer 9",
                "roles": ["MC_MC", "Multimedia_Photographer"],
            },
            {
                "id": 10,
                "name": "Interviewer 10",
                "roles": ["Multimedia_Designer", "Sports_EventOperator"],
            },
            {
                "id": 11,
                "name": "Interviewer 11",
                "roles": ["Academy_EventOperator", "MC_MC"],
            },
            {
                "id": 12,
                "name": "Interviewer 12",
                "roles": ["Multimedia_ContentWriter", "Volunteers_EventOperator"],
            },
        ]
    )
    return candidates, interviewers, time_slots, tables


def solve_schedule(
    candidates: pd.DataFrame,
    interviewers: pd.DataFrame,
    time_slots: list[str],
    tables: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """Create, solve, and export the interview schedule."""
    model = cp_model.CpModel()
    candidate_ids = candidates["id"].tolist()
    interviewer_ids = interviewers["id"].tolist()

    x = {
        (candidate_id, slot, table): model.NewBoolVar(
            f"x_{candidate_id}_{slot}_{table}"
        )
        for candidate_id in candidate_ids
        for slot in time_slots
        for table in tables
    }
    y = {
        (interviewer_id, slot, table): model.NewBoolVar(
            f"y_{interviewer_id}_{slot}_{table}"
        )
        for interviewer_id in interviewer_ids
        for slot in time_slots
        for table in tables
    }
    is_scheduled = {
        candidate_id: model.NewBoolVar(f"is_scheduled_{candidate_id}")
        for candidate_id in candidate_ids
    }

    # A candidate can appear in at most one preferred slot and table.
    for _, candidate in candidates.iterrows():
        candidate_id = candidate["id"]
        preferred_slots = set(candidate["preferred_slots"])
        assignment_vars = [
            x[candidate_id, slot, table] for slot in preferred_slots for table in tables
        ]
        model.Add(sum(assignment_vars) == is_scheduled[candidate_id])
        for slot in set(time_slots) - preferred_slots:
            for table in tables:
                model.Add(x[candidate_id, slot, table] == 0)

    # Each table is either empty or has exactly one candidate.
    table_occupancy = {}
    for slot in time_slots:
        for table in tables:
            candidate_vars = [
                x[candidate_id, slot, table] for candidate_id in candidate_ids
            ]
            occupancy = model.NewBoolVar(f"occupied_{slot}_{table}")
            table_occupancy[slot, table] = occupancy
            model.Add(sum(candidate_vars) == occupancy)

            interviewer_vars = [
                y[interviewer_id, slot, table] for interviewer_id in interviewer_ids
            ]
            # Empty tables get no interviewers; active tables get 3 or 4.
            model.Add(sum(interviewer_vars) >= 3 * occupancy)
            model.Add(sum(interviewer_vars) <= 4 * occupancy)

    # An interviewer cannot work two tables during one slot.
    for interviewer_id in interviewer_ids:
        for slot in time_slots:
            model.Add(sum(y[interviewer_id, slot, table] for table in tables) <= 1)

    # Skill covering: each candidate skill is a Boolean OR over the qualified
    # interviewers at that table. AddImplication then requires that OR to be
    # true whenever the candidate is assigned. Because skills are composite
    # strings, Sports_EventOperator and Volunteers_EventOperator remain
    # different exact-match skills.
    interviewer_roles = interviewers.set_index("id")["roles"].to_dict()
    for _, candidate in candidates.iterrows():
        candidate_id = candidate["id"]
        required_roles = set(candidate["aspirations"])
        for slot in candidate["preferred_slots"]:
            for table in tables:
                assignment = x[candidate_id, slot, table]
                for role in required_roles:
                    qualified_interviewers = [
                        y[interviewer_id, slot, table]
                        for interviewer_id in interviewer_ids
                        if role in interviewer_roles[interviewer_id]
                    ]
                    if not qualified_interviewers:
                        model.Add(assignment == 0)
                    else:
                        role_covered = model.NewBoolVar(
                            f"covered_{candidate_id}_{slot}_{table}_{role}"
                        )
                        model.AddMaxEquality(role_covered, qualified_interviewers)
                        model.AddImplication(assignment, role_covered)

    # A large primary weight makes interviewer minimization lexicographically
    # secondary to scheduling as many candidates as possible.
    max_interviewer_assignments = len(interviewer_ids) * len(time_slots)
    primary_weight = max_interviewer_assignments + 1
    model.Maximize(primary_weight * sum(is_scheduled.values()) - sum(y.values()))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(
            f"No feasible schedule found. Solver status: {solver.StatusName(status)}"
        )

    rows = []
    matrix_values = {}
    for slot in time_slots:
        for table in tables:
            assigned_candidate = next(
                (
                    candidate
                    for _, candidate in candidates.iterrows()
                    if solver.Value(x[candidate["id"], slot, table])
                ),
                None,
            )
            if assigned_candidate is None:
                matrix_values[table, slot] = ""
                continue

            assigned_interviewers = [
                interviewers.loc[interviewers["id"] == interviewer_id, "name"].iloc[0]
                for interviewer_id in interviewer_ids
                if solver.Value(y[interviewer_id, slot, table])
            ]
            interviewer_columns = assigned_interviewers + [""] * (
                4 - len(assigned_interviewers)
            )
            rows.append(
                {
                    "Slot": slot,
                    "Table": table,
                    "Candidate": assigned_candidate["name"],
                    "Candidate_Aspirations": ", ".join(
                        assigned_candidate["aspirations"]
                    ),
                    "Interviewer_1": interviewer_columns[0],
                    "Interviewer_2": interviewer_columns[1],
                    "Interviewer_3": interviewer_columns[2],
                    "Interviewer_4": interviewer_columns[3],
                }
            )
            matrix_values[table, slot] = f"{assigned_candidate['name']} | " + ", ".join(
                assigned_interviewers
            )

    flat_columns = [
        "Slot",
        "Table",
        "Candidate",
        "Candidate_Aspirations",
        "Interviewer_1",
        "Interviewer_2",
        "Interviewer_3",
        "Interviewer_4",
    ]
    df_flat = pd.DataFrame(rows, columns=flat_columns).sort_values(["Slot", "Table"])
    df_matrix = pd.DataFrame(
        [[matrix_values[table, slot] for slot in time_slots] for table in tables],
        index=tables,
        columns=time_slots,
    )
    df_matrix.index.name = "Tables"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df_flat.to_csv(OUTPUT_DIR / "interview_schedule_flat.csv", index=False)
    df_matrix.to_csv(OUTPUT_DIR / "interview_schedule_matrix.csv")
    return (
        df_flat,
        df_matrix,
        sum(solver.Value(value) for value in is_scheduled.values()),
    )


def main() -> None:
    candidates, interviewers, time_slots, tables = build_mock_data()
    df_flat, df_matrix, scheduled_count = solve_schedule(
        candidates, interviewers, time_slots, tables
    )
    print(f"Successfully scheduled candidates: {scheduled_count}/{len(candidates)}")
    print("\nFlat schedule:")
    print(df_flat.to_string(index=False))
    print("\nMatrix schedule:")
    print(df_matrix.to_string())
    print(f"\nCSV files written to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
