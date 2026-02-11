[x] Add a new nullable column pre_test_rest_time (float) to the Step table/model.
[x] Update DB schema
This column will automatically store the duration (工步執行時間(秒)) of the previous step (by step_number) for each step.
For steps where there is no previous step (e.g., the first step), this value will be None (null).
The value will be set automatically when steps are created or updated; users do not set it manually.
then this value will be store together with other data with step data in DB 