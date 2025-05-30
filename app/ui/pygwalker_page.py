import streamlit as st
import pandas as pd
from pygwalker.api.streamlit import StreamlitRenderer
from app.models.database import Experiment, Measurement
from app.utils.database import get_session

@st.cache_resource
def get_renderer(df: pd.DataFrame) -> StreamlitRenderer:
    return StreamlitRenderer(df)

def render_pygwalker_page():
    st.title("Pygwalker Page")

    session = get_session()
    experiments = session.query(Experiment).all()
    experiment_names = [exp.name for exp in experiments]

    selected_experiment_name = st.selectbox("Select Experiment", experiment_names)

    if selected_experiment_name:
        selected_experiment = next(exp for exp in experiments if exp.name == selected_experiment_name)
        
        measurements = session.query(Measurement).filter(Measurement.experiment_id == selected_experiment.id).all()

        if measurements:
            data = []
            for m in measurements:
                data.append({
                    "id": m.id,
                    "experiment_id": m.experiment_id,
                    "name": m.name,
                    "type": m.type,
                    "unit": m.unit,
                    "value_int": m.value_int,
                    "value_float": m.value_float,
                    "value_str": m.value_str,
                    "timestamp": m.timestamp,
                    "created_at": m.created_at,
                    "updated_at": m.updated_at
                })
            
            df = pd.DataFrame(data)
            
            renderer = get_renderer(df)
            renderer.explorer()
        else:
            st.write("No measurements found for this experiment.")
    session.close()
