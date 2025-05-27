from models.user import models as user_models
from models.trip.models import Trip, TripMember, TripInvitation # 从新的路径导入模型
# 或者可以这样导入:
# from models.trip import models as trip_models
# 然后在 __all__ 中使用 trip_models.Trip 等

# 将来可以添加更多的模型导入
# from models.expense import models as expense_models

# 必要时可以为 alembic 或 DB 初始化导出所有模型
__all__ = ['user_models', 'Trip', 'TripMember', 'TripInvitation'] # 如果直接导入模型，这里保持不变
# 如果使用 'from models.trip import models as trip_models'
# 则 __all__ 应该包含 'trip_models' 或者 'trip_models.Trip' 等，取决于如何使用
# 为了简单起见，我们保持直接导入模型的方式
