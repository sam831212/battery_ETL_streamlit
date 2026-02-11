# Debugging Summary: Streamlit Page Disappearance

**Date:** 2025-06-17

**Problem:**
The Streamlit page `app/ui/delete_experiment_page.py` disappears (goes blank or navigates away unexpectedly) after the user clicks the "🗑️ 刪除實驗" button. This issue was observed consistently, even when attempting to delete experiments that might involve a large amount of related data.

**Debugging Steps & Findings:**

1.  **Initial Hypothesis & Logging:**
    *   **Hypothesis:** The disappearance was due to timeouts or unhandled exceptions during large database deletion operations.
    *   **Actions:**
        *   Added extensive `st.write` debug statements in the UI (`delete_experiment_page.py`).
        *   Added `logger.info` statements in the backend data service (`app/services/database_service.py`), specifically within the `delete_experiment_and_related` function.
        *   Displayed data statistics (counts of experiments, steps, measurements, files) on the UI to give the user an idea of the deletion scope.
        *   Strengthened `try-except` blocks in the UI to catch and display potential errors.
    *   **Findings:** User-provided logs showed database `ROLLBACK` commands when actual deletion was attempted, indicating that the database transaction was failing.

2.  **Backend - Batch Deletion Attempt:**
    *   **Hypothesis:** A single large transaction for deleting an experiment and all its related data was causing issues (e.g., database locks, timeouts).
    *   **Actions:**
        *   Refactored `delete_experiment_and_related` to delete related entities in smaller batches with intermediate commits:
            1.  Batch delete `Measurement` records.
            2.  Delete `Step` records.
            3.  Delete `ProcessedFile` records.
            4.  Delete the `Experiment` record itself.
    *   **Findings:** The page *still* disappeared after clicking the delete button, even with batching implemented.

3.  **Backend - "No-Op" Deletion Test:**
    *   **Hypothesis:** To isolate whether the issue was with the database operations or the Streamlit UI flow.
    *   **Actions:**
        *   Modified `delete_experiment_and_related` in `database_service.py` to become a "no-operation" (no-op) function. This version only logged that it was called and which experiment ID it received, without performing any actual database read or write operations.
    *   **Findings:** The page *still* disappeared. This was a critical finding, strongly suggesting the problem was not with the database deletion logic itself but likely within the Streamlit UI or its interaction with the backend call.

4.  **UI Simplification:**
    *   **Hypothesis:** Complex UI updates or Streamlit commands after the button click might be causing instability.
    *   **Actions:**
        *   In `delete_experiment_page.py`, significantly simplified the code block executed when the delete button is clicked (and confirmation is given):
            *   Temporarily removed `st.spinner`.
            *   Removed success messages (`st.success`, `st.balloons`).
            *   Removed cache clearing (`load_experiments.clear()`).
            *   Removed session state modifications (`st.session_state.delete_success_message`).
            *   Removed the secondary "重新載入實驗列表" button and its associated `st.rerun()` call.
        *   The UI logic was reduced to printing debug messages and calling the (now no-op) `delete_experiment_and_related` function.
    *   **Findings:** The page *still* disappeared even with this highly simplified UI logic and no-op backend.

**Current Understanding:**

*   The root cause of the page disappearing is highly likely within the Streamlit UI layer (`delete_experiment_page.py`) or Streamlit's core mechanisms for handling form submissions, page reruns, or session state. It does not appear to be directly caused by the database deletion operations themselves.
*   The `ROLLBACK` statements observed in SQLAlchemy logs during normal page operations (like fetching statistics) are likely standard behavior for read-only transactions within a session context that doesn't explicitly commit changes. The `ROLLBACK` observed during *actual* deletion attempts (before the no-op change) was indicative of the deletion transaction failing.

**Next Steps for Future Debugging:**

1.  **Browser Developer Console:** Thoroughly inspect the browser's developer console (usually F12, "Console" tab) for any JavaScript errors or warnings that occur at the moment the page disappears.
2.  **Further UI Isolation:**
    *   Temporarily remove the `st.form` wrapper and use a simple `st.button` for the delete action. If this resolves the issue, the problem lies specifically with `st.form` or `st.form_submit_button`.
    *   Comment out the call to `delete_experiment_and_related(selected_id)` *entirely* from the button's click handler in the UI. If the page *stops* disappearing, then something about the act of calling this function (even as a no-op) or Streamlit's control flow around it is problematic.
3.  **Minimal Reproducible Example:** If the issue persists, try creating a new, extremely simple Streamlit page with only a button that performs a trivial action. Gradually add components from `delete_experiment_page.py` to this minimal example to identify which component or pattern triggers the disappearance.
4.  **Streamlit Version & Environment:** Check for any recent updates to Streamlit or related packages. Consider if any environment changes could be a factor.
5.  **Review `main.py` (Multipage Structure):** Investigate how `delete_experiment_page.py` is integrated into the overall multipage application structure in `main.py`. An issue at the multipage management level could potentially cause such behavior.
