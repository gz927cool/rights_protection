from datetime import timedelta
from uuid import UUID
from app.utils.security import create_access_token, decode_token
from app.db.repositories import UserRepository
from app.db.database import AsyncSessionLocal

class AuthService:
    @staticmethod
    async def login(phone: str, code: str) -> str:
        # 验证码校验（简化版，实际应连接短信服务）
        if code != "123456":  # TODO: 真实验证码
            raise ValueError("Invalid code")

        async with AsyncSessionLocal() as db:
            repo = UserRepository(db)
            user = await repo.get_by_phone(phone)
            if not user:
                user = await repo.create(phone=phone)
            token = create_access_token({"sub": str(user.id)})
            return token

    @staticmethod
    async def get_current_user(token: str):
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid token")
        async with AsyncSessionLocal() as db:
            repo = UserRepository(db)
            user = await repo.get_by_id(UUID(user_id))
            if not user:
                raise ValueError("User not found")
            return user
