from app.utils.database import get_session
from app.models import Measurement, Step, Experiment
from sqlmodel import select

def check_database():
    """檢查數據庫中的測量數據"""
    with get_session() as session:
        # 檢查測量數據總數
        measurement_count = session.query(Measurement).count()
        print(f"總測量數據數量: {measurement_count}")
        
        # 檢查步驟總數
        step_count = session.query(Step).count()
        print(f"總步驟數量: {step_count}")
        
        # 檢查實驗總數
        experiment_count = session.query(Experiment).count()
        print(f"總實驗數量: {experiment_count}")
        
        # 檢查每個實驗的步驟數量
        experiments = session.query(Experiment).all()
        print("\n每個實驗的步驟數量:")
        for exp in experiments:
            steps = session.query(Step).filter(Step.experiment_id == exp.id).all()
            print(f"實驗 {exp.id} ({exp.name}): {len(steps)} 步驟")
            
            # 檢查每個步驟的測量數據數量
            print(f"  步驟測量數據數量:")
            for step in steps:
                meas_count = session.query(Measurement).filter(Measurement.step_id == step.id).count()
                print(f"  - 步驟 {step.step_number} (ID: {step.id}): {meas_count} 測量")

if __name__ == "__main__":
    check_database() 