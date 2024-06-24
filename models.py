from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Model
from datetime import datetime, timedelta
import uuid
from pydantic import BaseModel


class PasswordResetToken(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='password_reset_tokens', null=True)
    token = fields.UUIDField(default=uuid.uuid4)
    expires_at = fields.DatetimeField()

    class Meta:
        table = "password_reset_tokens"

    @classmethod
    async def create_with_expiration(cls, user=None, normal_user=None, reset_token=uuid.uuid4()):
        expires_at = datetime.utcnow() + timedelta(hours=1)
        instance = cls(user=user, normal_user=normal_user, token=reset_token, expires_at=expires_at)
        await instance.save()
        return instance


class MessageResponse(BaseModel):
    message: str


class AuthToken(BaseModel):
    access_token: str
    token_type: str


class User(Model):
    id = fields.IntField(pk=True, index=True)
    username = fields.CharField(max_length=20, null=False, unique=True)
    email = fields.CharField(max_length=200, null=False, unique=True)
    password = fields.CharField(max_length=100, null=False)
    is_verified = fields.BooleanField(default=False)
    join_date = fields.DatetimeField(default=datetime.utcnow)


class Account(Model):
    id = fields.IntField(pk=True, index=True)
    account_name = fields.CharField(max_length=20, null=False, unique=True)
    city = fields.CharField(max_length=100, null=False, default="Unspecified")
    postal_code = fields.CharField(max_length=100, null=False, default="Unspecified")
    logo = fields.CharField(max_length=200, null=False, default="default.jpg")
    owner = fields.ForeignKeyField("models.User", related_name="accountant")


class ChangePassword(BaseModel):
    current_password: str
    new_password: str


# Pydantic models creation
user_pydantic = pydantic_model_creator(User, name="User", exclude=("is_verified",))
user_pydanticIn = pydantic_model_creator(User, name="UserIn", exclude_readonly=True, exclude=("is_verified", "join_date"))
user_pydanticOut = pydantic_model_creator(User, name="UserOut", exclude=("password",))

account_pydantic = pydantic_model_creator(Account, name="Account")
account_pydanticIn = pydantic_model_creator(Account, name="AccountIn", exclude=("logo", "id"))
