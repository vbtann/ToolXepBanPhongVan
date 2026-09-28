"""Streamlit web UI for the CP-SAT interview scheduler."""

from __future__ import annotations

import ast
from io import BytesIO
import unicodedata

import pandas as pd
import streamlit as st

from interview_scheduler import SchedulerInfeasibleError, run_scheduler

CANDIDATE_COLUMNS = ["mssv", "aspiration", "preferred_slots"]
INTERVIEWER_COLUMNS = ["mssv", "họ và tên", "roles"]


def normalize_column_name(column: object) -> str:
    """Normalize headers for matching while preserving values in the data."""
    text = str(column).strip().lower()
    return "".join(
        character
        for character in unicodedata.normalize("NFD", text)
        if unicodedata.category(character) != "Mn"
    )


def normalize_input_columns(dataframe: pd.DataFrame, input_type: str) -> pd.DataFrame:
    """Map Vietnamese upload headers to the scheduler's canonical schema."""
    if input_type == "candidates":
        aliases = {
            "mssv": "id",
            "student id": "id",
            "id": "id",
            "aspiration": "aspirations",
            "aspirations": "aspirations",
            "nguyen vong": "aspirations",
            "khung thoi gian ung vien chon": "preferred_slots",
            "preferred slots": "preferred_slots",
            "preferred_slots": "preferred_slots",
        }
        required = {"id", "aspirations", "preferred_slots"}
    else:
        aliases = {
            "mssv": "id",
            "student id": "id",
            "id": "id",
            "ho va ten": "name",
            "full name": "name",
            "name": "name",
            "cac vai tro co the phong van": "roles",
            "vai tro": "roles",
            "roles": "roles",
        }
        required = {"id", "name", "roles"}

    renamed = {}
    for column in dataframe.columns:
        normalized = normalize_column_name(column)
        if normalized in aliases:
            renamed[column] = aliases[normalized]
    normalized_dataframe = dataframe.rename(columns=renamed).copy()
    missing = required - set(normalized_dataframe.columns)
    if missing:
        raise ValueError(
            f"{input_type} file is missing required columns after mapping: "
            f"{sorted(missing)}. Expected columns: {sorted(required)}."
        )
    if input_type == "candidates" and "name" not in normalized_dataframe.columns:
        normalized_dataframe["name"] = normalized_dataframe["id"].astype(str)
    return normalized_dataframe


def parse_list_cell(value: object) -> list[str]:
    """Parse list columns from Excel objects or CSV string representations."""
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value]
    if pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, (list, tuple, set)):
            return [str(item).strip() for item in parsed]
    except (ValueError, SyntaxError):
        pass
    return [item.strip() for item in text.split(",") if item.strip()]


def read_uploaded_file(uploaded_file, input_type: str) -> pd.DataFrame:
    """Read and validate a CSV/XLSX upload."""
    suffix = uploaded_file.name.lower().rsplit(".", 1)[-1]
    if suffix == "csv":
        dataframe = pd.read_csv(uploaded_file)
    elif suffix == "xlsx":
        dataframe = pd.read_excel(uploaded_file)
    else:
        raise ValueError("Only CSV and XLSX files are supported.")

    dataframe = normalize_input_columns(dataframe, input_type)
    list_columns = {"aspirations", "preferred_slots", "roles"}.intersection(
        dataframe.columns
    )
    for column in list_columns:
        dataframe[column] = dataframe[column].apply(parse_list_cell)
    if dataframe.empty:
        raise ValueError(f"{uploaded_file.name} does not contain any rows.")
    return dataframe


def template_bytes() -> bytes:
    """Create an Excel workbook showing the required input structure."""
    candidates = pd.DataFrame(
        [
            {
                "mssv": "SV001",
                "aspiration": "['Photographer (Multimedia)', 'Editor (Multimedia)', 'MC (MC)']",
                "preferred_slots": "['08:00-09:00', '09:00-10:00', '10:00-11:00', '11:00-12:00']",
            }
        ],
        columns=CANDIDATE_COLUMNS,
    )
    interviewers = pd.DataFrame(
        [
            {
                "mssv": "PV001",
                "họ và tên": "Example Interviewer",
                "roles": "['Photographer (Multimedia)', 'Editor (Multimedia)', 'MC (MC)']",
            }
        ],
        columns=INTERVIEWER_COLUMNS,
    )
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        candidates.to_excel(writer, index=False, sheet_name="Candidates")
        interviewers.to_excel(writer, index=False, sheet_name="Interviewers")
    return buffer.getvalue()


def dataframe_csv(dataframe: pd.DataFrame, include_index: bool = False) -> bytes:
    return dataframe.to_csv(index=include_index).encode("utf-8")


def main() -> None:
    st.set_page_config(
        page_title="Interview Scheduling System",
        page_icon="📅",
        layout="wide",
    )
    st.title("Interview Scheduling System")
    st.sidebar.title("Interview Scheduling System")
    st.sidebar.caption("Upload structured data and optimize the interview plan.")

    with st.sidebar:
        candidates_file = st.file_uploader(
            "Candidates data", type=["csv", "xlsx"], key="candidates_file"
        )
        interviewers_file = st.file_uploader(
            "Interviewers data", type=["csv", "xlsx"], key="interviewers_file"
        )
        st.download_button(
            "Download Template Excel File",
            data=template_bytes(),
            file_name="interview_scheduler_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        with st.expander("Advanced Settings"):
            number_tables = st.number_input(
                "Number of tables", min_value=1, max_value=100, value=15, step=1
            )
            start_time = st.time_input("Start time", value=pd.Timestamp("08:00").time())
            end_time = st.time_input("End time", value=pd.Timestamp("17:00").time())
            break_start = st.time_input(
                "Break start", value=pd.Timestamp("12:00").time()
            )
            break_end = st.time_input("Break end", value=pd.Timestamp("13:00").time())

    st.markdown(
        "Upload candidate and interviewer files, check the previews, and run the "
        "CP-SAT optimizer. Aspirations and interviewer roles must use the exact "
        "format `Role (Department)`, such as `Event operator (Entertainment & Arts)`."
    )

    candidates_df = None
    interviewers_df = None
    if candidates_file or interviewers_file:
        st.subheader("Input Preview")
        preview_left, preview_right = st.columns(2)
        if candidates_file:
            try:
                candidates_df = read_uploaded_file(candidates_file, "candidates")
                with preview_left:
                    st.write("Candidates")
                    st.dataframe(candidates_df, use_container_width=True)
            except Exception as error:
                st.error(f"Could not read candidates file: {error}")
        if interviewers_file:
            try:
                interviewers_df = read_uploaded_file(interviewers_file, "interviewers")
                with preview_right:
                    st.write("Interviewers")
                    st.dataframe(interviewers_df, use_container_width=True)
            except Exception as error:
                st.error(f"Could not read interviewers file: {error}")

    run_clicked = st.button(
        "🚀 Run Optimization",
        type="primary",
        use_container_width=True,
        disabled=candidates_df is None or interviewers_df is None,
    )
    if not run_clicked:
        if not candidates_file or not interviewers_file:
            st.info("Upload both required files to enable optimization.")
        return

    try:
        with st.spinner("Scheduling in progress..."):
            df_flat, df_matrix = run_scheduler(
                candidates_df,
                interviewers_df,
                number_tables=int(number_tables),
                start_time=start_time.strftime("%H:%M"),
                end_time=end_time.strftime("%H:%M"),
                break_start=break_start.strftime("%H:%M"),
                break_end=break_end.strftime("%H:%M"),
            )
    except SchedulerInfeasibleError:
        st.error(
            "Could not schedule all candidates. The constraints or available "
            "resources are insufficient. Try adding interviewers or tables, "
            "widening preferred slots, or checking the exact role spellings."
        )
        return
    except Exception as error:
        st.error(f"Scheduling failed: {error}")
        return

    scheduled_count = len(df_flat)
    st.success(
        f"Successfully scheduled {scheduled_count}/{len(candidates_df)} candidates"
    )
    flat_tab, matrix_tab = st.tabs(["Flat Table View", "Matrix View"])
    with flat_tab:
        st.dataframe(df_flat, use_container_width=True, hide_index=True)
        st.download_button(
            "Download Flat Schedule CSV",
            dataframe_csv(df_flat),
            "interview_schedule_flat.csv",
            "text/csv",
            key="download_flat",
        )
    with matrix_tab:
        st.dataframe(df_matrix, use_container_width=True)
        st.download_button(
            "Download Matrix Schedule CSV",
            dataframe_csv(df_matrix, include_index=True),
            "interview_schedule_matrix.csv",
            "text/csv",
            key="download_matrix",
        )


if __name__ == "__main__":
    main()
