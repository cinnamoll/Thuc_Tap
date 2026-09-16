# Plan to Fix Context Length Issue in LangGraph Financial Report Pipeline

## Problem
The LangGraph workflow is exceeding the maximum context length (1,048,576 tokens) because large data objects (such as pandas DataFrames, chart objects, or extensive validation results) are being passed directly between nodes in the workflow state. When these states are serialized into prompts for LLM calls (e.g., in validation, feature engineering, or reporting nodes), the token count becomes too large.

## Solution
Replace the passage of large data objects in the workflow state with references to temporary files stored on disk. Each node will:
1. Write its large output to a temporary file (e.g., Parquet, CSV, JSON, or pickle).
2. Store only the file path (or a summary) in the workflow state.
3. Subsequent nodes will read the data from the file path when needed.

This reduces the state size from megabytes (for DataFrames) to a few hundred bytes (for file paths).

## Steps to Implement

### 1. Identify Nodes Producing Large Data
Examine the following nodes (based on the workflow in `script.py` and the `Subgraph` directory) for large data outputs:
- `feature_engineering` (in `Subgraph/feature.py`): Likely produces engineered DataFrames.
- `validation` (in `Subgraph/validator.py`): May produce validation reports or large DataFrames.
- `financial_forecasting` (in `Subgraph/financial_forecasting.py`): May produce forecast DataFrames.
- `scenario_analysis` (in `Subgraph/scenario_analysis.py`): May produce scenario DataFrames.
- `ratio_trend_engine` (in `Subgraph/ratio_trend.py`): May produce ratio DataFrames.
- `build_charts_node` (in `Subgraph/charts.py`): May produce chart objects or base64-encoded images.
- `generate_report_node` / `review_report_node` / `build_report_node` (in `Subgraph/reporting.py`): May produce large report strings or structured data.

### 2. Modify Nodes to Write Large Outputs to Temporary Files
For each identified node:
- Choose an appropriate temporary file format:
  - For DataFrames: Use Parquet (efficient) or CSV.
  - For charts: Save as PNG/JPEG and store the file path, or store base64 string if small (but prefer file path).
  - For validation/report objects: Use JSON or pickle.
- Generate a unique temporary file path (e.g., using `uuid.uuid4()` or a timestamp) in a designated temporary directory (e.g., `/tmp/financial_report_pipeline/` or a subdirectory of the current working directory).
- Write the large data to the temporary file.
- Update the node's return dictionary to include the file path (e.g., `"engineered_df_path": "/tmp/.../engineered_df.parquet"`) instead of the data object.
- Remove the large data object from the returned state (do not return it).

### 3. Modify Nodes to Read Large Inputs from Temporary Files
For each node that consumes large data produced by another node:
- Instead of reading the data directly from the state (e.g., `state["engineered_df"]`), read the file path from the state (e.g., `state["engineered_df_path"]`).
- Load the data from the temporary file into memory (e.g., `pd.read_parquet(path)` for a DataFrame).
- Use the loaded data as needed in the node's logic.
- Do not store the reloaded data in the state unless it is modified and needs to be passed forward (in which case, repeat step 2 for the modified data).

### 4. Adjust State Structure (if Necessary)
- Check the `FinancialReportState` class in `Class/FinancialState.py`.
- If it does not already have fields for the file paths we intend to use, add them (e.g., `engineered_df_path: str`, `validation_report_path: str`, etc.).
- If modifying the state structure is not desirable (to avoid breaking changes), we can reuse existing fields by changing their meaning (e.g., store a string path where previously a DataFrame was stored). However, this requires careful coordination and may reduce clarity. Prefer adding new fields if possible.

### 5. Implement Cleanup of Temporary Files
- Option A: Use a temporary directory that is automatically cleaned by the system (e.g., `tempfile.TemporaryDirectory`). However, note that the workflow may span multiple interactions (due to interrupts), so the temporary directory must persist for the duration of the workflow run.
- Option B: At the end of the workflow (when the graph reaches `END`), delete all temporary files created during the run. This can be done by:
  - Keeping a list of temporary file paths in the state (e.g., `"temp_files": [list_of_paths]`), appending to it each time a new temp file is created.
  - Adding a final node (before `END`) that iterates over the list and deletes the files, then clears the list.
- Option C: Rely on the operating system's temporary file cleanup (e.g., files in `/tmp` are often cleared on reboot). This is less reliable for long-running processes but acceptable for short-lived workflows.

### 6. Test the Changes
- Run the workflow with a sample set of input PDF files.
- Monitor the state size (by logging the size of the state dictionary or using a debugger) to ensure it remains small.
- Verify that the outputs (reports, charts, etc.) are still generated correctly.
- Check that temporary files are created and cleaned up as expected.

## Expected Outcome
- The workflow state will no longer contain large data objects, reducing the token count when states are passed to LLM calls.
- The error "This model's maximum context length is 1048576 tokens" should be resolved.
- The functional behavior of the workflow remains unchanged.

## Files to Modify
- `script.py`: No changes needed (only defines the graph structure and edges).
- `Class/FinancialState.py`: Possibly to add new state fields for file paths.
- Each node file in `Subgraph/` that produces or consumes large data:
  - `feature.py`
  - `validator.py`
  - `financial_forecasting.py`
  - `scenario_analysis.py`
  - `ratio_trend.py`
  - `charts.py`
  - `reporting.py`
  - (Others as identified)

## Notes
- This plan assumes that the large data objects are the primary cause of the context length issue. If the issue stems from the LLM prompt itself including excessive historical messages or logs, additional steps (like truncating conversation history) may be needed.
- The temporary directory should be chosen with sufficient disk space and appropriate permissions.
- Error handling should be added around file I/O operations (e.g., what to do if a temporary file cannot be written or read).