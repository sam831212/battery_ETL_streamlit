# Battery ETL Dashboard Design Plan

## Overview
This dashboard is part of a battery data ETL project. It will:
- Show hierarchical data across three levels: Project → Experiment → Step
- Allow selection via checkbox per row in each table
- Enable data filtering based on user selections
- Provide two separate plotting areas:
  - Step-level data visualization
  - Detail-level time-series visualization

---

## Tools

| Component        | Tool / Library   | Purpose                            |
|------------------|------------------|------------------------------------|
| UI framework     | Streamlit        | Main application framework         |
| Table display    | st_aggrid        | Interactive tables with checkboxes |
| Plotting (Step)  | Plotly           | Configurable plots for Step data   |
| Plotting (Detail)| (Optional) pygwalker | Freeform EDA for time-series data    |

---

## Table Structure and Interaction

### Tables Displayed (Vertically):
- **Project Table**
- **Experiment Table**
- **Step Table**

### Interaction Rules:
- Each table includes a **checkbox column** for row selection.
- Selecting rows in one table **filters lower-level tables**:
  - Project selection → filters Experiments
  - Experiment selection → filters Steps
- Step table selection enables plotting.

---

## Plotting Areas

### 1. Step Plot Area

**Purpose:** Plot filtered Step-level data

**Controls:**
- Dropdowns for:
  - X-axis
  - Y-axis
  - Legend (optional: color/group)

**Plot:**
- Generated using `plotly.express` or `plotly.graph_objects`
- Interactive: zoom, hover, export

---

### 2. Detail Plot Area

**Purpose:** Plot Detail-level time-series data (optional)

**Options:**
- **Option A (Final Product):** Use Plotly with same config as Step area
- **Option B (Exploration/Prototype):** Use `pygwalker` for free-form exploration

---

## State and Filtering

- Use `st.session_state` to track selected rows
- Filtering logic:
  ```python
  selected_projects = df_project[df_project["selected"]]["project_id"]
  df_experiment = df_experiment[df_experiment["project_id"].isin(selected_projects)]
  ...
