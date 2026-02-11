import os
import shutil
import time

class DBSyncManager:
    def __init__(self, shared_db_path, local_db_path, lock_timeout=600):
        self.shared_db_path = shared_db_path
        self.local_db_path = local_db_path
        self.lock_path = shared_db_path + '.lock'
        self.lock_timeout = lock_timeout  # 秒，預設10分鐘

    def is_locked(self):
        if not os.path.exists(self.lock_path):
            return False
        # 檢查 lock 是否過期
        lock_age = time.time() - os.path.getmtime(self.lock_path)
        if lock_age > self.lock_timeout:
            os.remove(self.lock_path)
            return False
        return True

    def acquire_lock(self):
        if self.is_locked():
            raise RuntimeError('資料庫正在被其他人寫入，請稍後再試。')
        with open(self.lock_path, 'w') as f:
            f.write(f'locked by {os.environ.get("USERNAME", "unknown")} at {time.ctime()}')

    def release_lock(self):
        if os.path.exists(self.lock_path):
            os.remove(self.lock_path)

    def download_db(self):
        shutil.copy2(self.shared_db_path, self.local_db_path)

    def upload_db(self):
        shutil.copy2(self.local_db_path, self.shared_db_path)

    def safe_write(self, write_func, *args, **kwargs):
        """
        寫入時自動處理下載、加鎖、寫入、上傳、解鎖
        write_func: 你的寫入邏輯（函式），會傳入 local_db_path
        """
        self.acquire_lock()
        try:
            self.download_db()
            write_func(self.local_db_path, *args, **kwargs)
            self.upload_db()
        finally:
            self.release_lock()

# 使用範例：
# dbsync = DBSyncManager(r"\\smpfile11.simplo.com.tw\Prj_share\TPRD_CA\電池應用部測試資料\CA DB\2025_06_CA_DB.db", r"C:\\Users\\sam2_chen\\DB0609\\B\\battery.db")
# dbsync.safe_write(your_write_func)
