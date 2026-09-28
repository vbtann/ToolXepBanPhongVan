"""CP-SAT interview scheduling example using pandas mock data."""

from __future__ import annotations

from pathlib import Path
import re
import unicodedata

import pandas as pd
from ortools.sat.python import cp_model

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


class SchedulerInfeasibleError(RuntimeError):
    """Raised when CP-SAT cannot find a feasible interview schedule."""


ROLE_ALIASES = {
    "event operator (entertainment and arts)": "event operator (entertainment & arts)",
    "event operator (entertaiment & arts)": "event operator (entertainment & arts)",
    "event operator (sport)": "event operator (sports)",
    "event operator (voluteers)": "event operator (volunteers)",
}


def normalize_role(value: object) -> str:
    """Return a case-insensitive canonical key for matching roles."""
    text = unicodedata.normalize("NFKC", str(value)).strip().casefold()
    text = re.sub(r"\s+", " ", text)
    return ROLE_ALIASES.get(text, text)


def normalize_time_slot(value: object) -> str:
    """Normalize variants such as ``8:00-9:00`` to ``08:00-09:00``."""
    text = str(value).strip()
    match = re.fullmatch(r"(\d{1,2})\s*:\s*(\d{2})\s*-\s*(\d{1,2})\s*:\s*(\d{2})", text)
    if not match:
        raise ValueError(
            f"Invalid time slot {value!r}. Expected format HH:MM-HH:MM, "
            "for example 08:00-09:00."
        )
    start_hour, start_minute, end_hour, end_minute = (
        int(part) for part in match.groups()
    )
    if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23):
        raise ValueError(f"Invalid hour in time slot {value!r}.")
    if not (0 <= start_minute <= 59 and 0 <= end_minute <= 59):
        raise ValueError(f"Invalid minute in time slot {value!r}.")
    return f"{start_hour:02d}:{start_minute:02d}-{end_hour:02d}:{end_minute:02d}"


def build_time_slots(
    start_time: str = "08:00",
    end_time: str = "17:00",
    break_start: str = "12:00",
    break_end: str = "13:00",
) -> list[str]:
    """Build one-hour slots and omit the configured break interval."""
    start = pd.Timestamp(start_time)
    end = pd.Timestamp(end_time)
    break_start_timestamp = pd.Timestamp(break_start)
    break_end_timestamp = pd.Timestamp(break_end)
    if end <= start or (end - start) % pd.Timedelta(hours=1) != pd.Timedelta(0):
        raise ValueError("Start/end time must define a positive whole number of hours.")

    slots = []
    current = start
    while current < end:
        next_time = current + pd.Timedelta(hours=1)
        if not (current < break_end_timestamp and next_time > break_start_timestamp):
            slots.append(f"{current:%H:%M}-{next_time:%H:%M}")
        current = next_time
    return slots


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


def run_scheduler(
    candidates_df: pd.DataFrame,
    interviewers_df: pd.DataFrame,
    *,
    number_tables: int = 15,
    start_time: str = "08:00",
    end_time: str = "17:00",
    break_start: str = "12:00",
    break_end: str = "13:00",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Solve the schedule and return the flat and matrix result DataFrames."""
    required_candidate_columns = {"id", "aspirations", "preferred_slots"}
    required_interviewer_columns = {"id", "name", "roles"}
    missing_candidates = required_candidate_columns - set(candidates_df.columns)
    missing_interviewers = required_interviewer_columns - set(interviewers_df.columns)
    if missing_candidates or missing_interviewers:
        raise ValueError(
            "Missing columns: "
            f"candidates={sorted(missing_candidates)}, "
            f"interviewers={sorted(missing_interviewers)}"
        )
    if number_tables < 1:
        raise ValueError("number_tables must be at least 1.")

    candidates = candidates_df.copy()
    interviewers = interviewers_df.copy()
    candidates["aspirations"] = candidates["aspirations"].apply(
        lambda roles: [role for role in roles if str(role).strip()]
    )
    interviewers["roles"] = interviewers["roles"].apply(
        lambda roles: [role for role in roles if str(role).strip()]
    )
    if "name" not in candidates.columns:
        candidates["name"] = candidates["id"].astype(str)
    candidates["preferred_slots"] = candidates["preferred_slots"].apply(
        lambda slots: [normalize_time_slot(slot) for slot in slots]
    )
    time_slots = build_time_slots(start_time, end_time, break_start, break_end)
    tables = [f"Table {number}" for number in range(1, number_tables + 1)]
    if not time_slots:
        raise ValueError("The configured time range contains no available slots.")
    unavailable_slots = sorted(
        {
            slot
            for slots in candidates["preferred_slots"]
            for slot in slots
            if slot not in time_slots
        }
    )
    if unavailable_slots:
        raise ValueError(
            "Candidate preferred slots are unavailable or outside the configured "
            f"schedule: {unavailable_slots}"
        )

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

    # Each table is either empty or has exactly one candidate. There is no
    # constraint across tables for the same slot, so multiple tables can run
    # concurrently in one time slot.
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
            # Empty tables get no interviewers; active tables get 1 to 4.
            model.Add(sum(interviewer_vars) >= occupancy)
            model.Add(sum(interviewer_vars) <= 4 * occupancy)

    # An interviewer cannot work two tables during one slot, but can cover
    # multiple aspirations for the candidate at their one assigned table.
    for interviewer_id in interviewer_ids:
        for slot in time_slots:
            model.Add(sum(y[interviewer_id, slot, table] for table in tables) <= 1)

    # Skill covering: each candidate skill is a Boolean OR over the qualified
    # interviewers at that table. AddImplication then requires that OR to be
    # true whenever the candidate is assigned. The same y[i, slot, table]
    # variable participates in every role that interviewer can cover, so one
    # interviewer can satisfy multiple aspirations for one candidate. Because
    # skills are composite strings, similarly named department roles remain
    # different exact-match skills.
    interviewer_roles = {
        interviewer_id: {normalize_role(role) for role in roles if str(role).strip()}
        for interviewer_id, roles in interviewers.set_index("id")["roles"].items()
    }
    for _, candidate in candidates.iterrows():
        candidate_id = candidate["id"]
        required_roles = {
            normalize_role(role)
            for role in candidate["aspirations"]
            if str(role).strip()
        }
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

    # Every input candidate is required to have exactly one assignment. If the
    # resources, preferred slots, or skills cannot support everyone, CP-SAT
    # returns INFEASIBLE instead of silently returning a partial schedule.
    model.Add(sum(is_scheduled.values()) == len(candidate_ids))

    # With all candidates mandatory, minimize interviewer usage as the
    # secondary objective.
    model.Minimize(sum(y.values()))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise SchedulerInfeasibleError(
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

    return df_flat, df_matrix


def main() -> None:
    candidates, interviewers, _, _ = build_mock_data()
    df_flat, df_matrix = run_scheduler(candidates, interviewers)
    scheduled_count = len(df_flat)
    print(f"Successfully scheduled candidates: {scheduled_count}/{len(candidates)}")
    print("\nFlat schedule:")
    print(df_flat.to_string(index=False))
    print("\nMatrix schedule:")
    print(df_matrix.to_string())
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df_flat.to_csv(OUTPUT_DIR / "interview_schedule_flat.csv", index=False)
    df_matrix.to_csv(OUTPUT_DIR / "interview_schedule_matrix.csv")
    print(f"\nCSV files written to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
