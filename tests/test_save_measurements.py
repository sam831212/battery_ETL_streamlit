import pandas as pd
from app.utils.database import get_session
from app.models import Measurement, Step, Experiment
from app.etl import convert_numpy_types

def save_measurements_to_db(
    experiment_id: int,
    details_df: pd.DataFrame,
    step_mapping: dict,
    nominal_capacity: float,
    batch_size: int = 1000
):
    """
    保存測量數據到資料庫
    
    Args:
        experiment_id: 實驗ID
        details_df: 詳細數據DataFrame
        step_mapping: 步驟編號到步驟ID的映射
        nominal_capacity: 標稱容量
        batch_size: 批處理大小
    """
    print(f"===== DEBUG: save_measurements_to_db =====")
    print(f"Experiment ID: {experiment_id}")
    print(f"Details DataFrame length: {len(details_df)}")
    print(f"Step mapping: {step_mapping}")
    
    with get_session() as session:
        saved_count = 0
        error_count = 0
        
        for i in range(0, len(details_df), batch_size):
            batch = details_df.iloc[i:min(i+batch_size, len(details_df))]
            measurements = []
            
            for _, row in batch.iterrows():
                try:
                    row_dict = convert_numpy_types(row.to_dict())
                    step_number = row_dict.get("step_number")
                    step_id = step_mapping.get(step_number)
                    
                    if step_id is not None:
                        # 確保所有數值欄位都是有效的浮點數
                        execution_time = float(row_dict.get("execution_time", 0.0))
                        voltage = float(row_dict.get("voltage", 0.0))
                        current = float(row_dict.get("current", 0.0))
                        temperature = float(row_dict.get("temperature", 25.0))
                        capacity = float(row_dict.get("capacity", 0.0))
                        energy = float(row_dict.get("energy", 0.0))
                        
                        measurement = Measurement(
                            step_id=step_id,
                            execution_time=execution_time,
                            voltage=voltage,
                            current=current,
                            temperature=temperature,
                            capacity=capacity,
                            energy=energy
                        )
                        measurements.append(measurement)
                        saved_count += 1
                except Exception as e:
                    error_count += 1
                    print(f"Error creating measurement: {str(e)}")
            
            if measurements:
                try:
                    # Add batch of measurements
                    session.add_all(measurements)
                    session.commit()
                    print(f"Saved batch of {len(measurements)} measurements")
                except Exception as e:
                    session.rollback()
                    print(f"Error saving batch of measurements: {str(e)}")
        
        print(f"Saved {saved_count} measurements with {error_count} errors")

def create_test_data(step_numbers):
    """創建測試數據
    
    Args:
        step_numbers: 要使用的步驟編號列表
    """
    # 確保至少有兩個步驟編號
    if len(step_numbers) < 2:
        step_numbers = step_numbers * 2
    
    # 創建一個簡單的測量數據DataFrame
    data = {
        "step_number": [step_numbers[0], step_numbers[0], step_numbers[0], step_numbers[1], step_numbers[1], step_numbers[1]],
        "execution_time": [0.0, 1.0, 2.0, 0.0, 1.0, 2.0],
        "voltage": [3.8, 3.7, 3.6, 3.5, 3.4, 3.3],
        "current": [1.0, 1.0, 1.0, -1.0, -1.0, -1.0],
        "temperature": [25.0, 25.1, 25.2, 25.3, 25.4, 25.5],
        "capacity": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
        "energy": [0.0, 0.37, 0.74, 1.05, 1.36, 1.65]
    }
    return pd.DataFrame(data)

def test_save_measurements():
    """測試保存測量數據到資料庫"""
    with get_session() as session:
        # 檢查是否有實驗
        experiment = session.query(Experiment).first()
        if not experiment:
            print("沒有找到實驗，無法進行測試")
            return
        
        # 檢查是否有步驟
        steps = session.query(Step).filter(Step.experiment_id == experiment.id).all()
        if not steps:
            print(f"實驗 {experiment.id} 沒有步驟，無法進行測試")
            return
        
        # 創建步驟映射
        step_mapping = {step.step_number: step.id for step in steps}
        print(f"步驟映射: {step_mapping}")
        
        # 獲取步驟編號列表
        step_numbers = list(step_mapping.keys())
        print(f"步驟編號: {step_numbers}")
        
        # 創建測試數據
        test_data = []
        for step_number in step_numbers:
            for i in range(3):  # 每個步驟創建3個測量點
                test_data.append({
                    'step_number': step_number,
                    'execution_time': i * 10.0,  # 每10秒一個測量點
                    'voltage': 3.7 + (i * 0.1),  # 電壓從3.7V開始，每次增加0.1V
                    'current': 1.0,  # 固定電流1A
                    'temperature': 25.0,  # 固定溫度25度
                    'capacity': i * 0.5,  # 容量每次增加0.5Ah
                    'energy': i * 2.0,  # 能量每次增加2Wh
                    'soc': 50.0 + (i * 10.0)  # SOC從50%開始，每次增加10%
                })
        
        # 創建DataFrame
        details_df = pd.DataFrame(test_data)
        print(f"測試數據:\n{details_df}")
        
        # 保存測量數據
        print("保存測量數據...")
        save_measurements_to_db(
            experiment_id=experiment.id,
            details_df=details_df,
            step_mapping=step_mapping,
            nominal_capacity=experiment.nominal_capacity
        )
        
        # 檢查是否保存成功
        measurement_count = session.query(Measurement).count()
        print(f"保存後的測量數據總數: {measurement_count}")
        
        # 檢查每個步驟的測量數據
        for step in steps:
            count = session.query(Measurement).filter(Measurement.step_id == step.id).count()
            print(f"步驟 {step.step_number} (ID: {step.id}): {count} 測量")
            
            # 檢查測量數據的具體值
            measurements = session.query(Measurement).filter(Measurement.step_id == step.id).all()
            for measurement in measurements:
                print(f"  測量數據:")
                print(f"    execution_time: {measurement.execution_time}")
                print(f"    voltage: {measurement.voltage}")
                print(f"    current: {measurement.current}")
                print(f"    temperature: {measurement.temperature}")
                print(f"    capacity: {measurement.capacity}")
                print(f"    energy: {measurement.energy}")
                print(f"    soc: {measurement.soc}")

if __name__ == "__main__":
    test_save_measurements() 