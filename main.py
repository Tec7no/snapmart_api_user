import logging
import smtplib
import uuid
from datetime import timedelta
from contextvars import Token
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pyotp

from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from fastapi import BackgroundTasks
from tortoise.transactions import in_transaction
from datetime import datetime, timedelta
from pydantic import BaseModel

import jwt
from fastapi import FastAPI, Request, HTTPException, status, Depends
from tortoise.contrib.fastapi import register_tortoise

# Authentication
from authentication import *
from fastapi.security import(OAuth2PasswordBearer, OAuth2PasswordRequestForm)

# signals
from tortoise.signals import post_save
from typing import List, Optional, Type
from tortoise import BaseDBAsyncClient
from emails import *

# response classes
from fastapi.responses import HTMLResponse
from models import user_pydanticIn, user_pydantic, Account, account_pydantic

# templates
from fastapi.templating import Jinja2Templates

# image upload
from fastapi import File, UploadFile
import secrets
from fastapi.staticfiles import StaticFiles



app = FastAPI()

oath2_scheme = OAuth2PasswordBearer(tokenUrl='token')

# static file setup config
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.post('/token')
async def generate_token(request_from: OAuth2PasswordRequestForm = Depends()):
    token = await token_generator(request_from.username, request_from.password)
    return {"access_token" : token, "token_type" : "bearer"}

async def get_current_user(token: str = Depends(oath2_scheme)):
    try:
        payload = jwt.decode(token, config_credentials["SECRET"], algorithms=['HS256'])
        user = await User.get(id = payload.get("id"))

    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return await user


@app.post("/user/me")
async def user_login(user: user_pydanticIn = Depends(get_current_user)):
    account = await Account.get(owner=user)
    logo = account.logo #asl6as5d4.png
    logo_path = "localhost:8000/static/images"+logo

    return {
        "status": "ok",
        "data": {
            "username": user.username,
            "email": user.email,
            "verified": user.is_verified,
            "joined_date": user.join_date.strftime("%b %d %Y"),
            "logo": logo_path
        }
    }


@post_save(User)
async def create_account(
        sender: "Type[User]",
        instance: User,
        created: bool,
        using_db: "Optional[BaseDBAsyncClient]",
        update_fields: List[str]
) -> None:
    if created:
        account_obj = await Account.create(
            account_name=instance.username, owner=instance
        )

        await account_pydantic.from_tortoise_orm(account_obj)
        # send the email
        await send_email([instance.email], instance)


templates = Jinja2Templates(directory="templates")


@app.get('/verification', response_class=HTMLResponse)
async def email_verification(request: Request, token: str):
    try:
        user = await verify_token(token)
        if user and not user.is_verified:
            user.is_verified = True
            await user.save()
            return templates.TemplateResponse("verification.html",
                                              {"request": request, "username": user.username})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

@app.post("/registration")
async def user_registrations(user: user_pydanticIn):
    user_info = user.dict(exclude_unset=True)
    user_info["password"] = get_hashed_password(user_info["password"])
    user_obj = await User.create(**user_info)
    new_user = await user_pydantic.from_tortoise_orm(user_obj)
    return {
        "status": "ok",
        "data": f"Hello {new_user.username} , thanks for choosing snapmart. please check your email inbox and click on the link to verify your account .",
    }


@app.put("/user/change-password")
async def change_password_endpoint(new_password: str, current_password: str, user: user_pydanticIn = Depends(get_current_user)):
    # Retrieve user from database
    user_obj = await User.get(username=user.username)

    # Verify the current password
    if not await verify_password(current_password, user_obj.password):
        raise HTTPException(status_code=400, detail="Incorrect current password")

    # Hash the new password
    hashed_password = get_hashed_password(new_password)

    # Update the user's password
    user_obj.password = hashed_password
    await user_obj.save()

    return {"status": "ok", "message": "Password updated successfully"}


register_tortoise(
    app,
    db_url="sqlite://User.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True
)


@app.get("/")
def index():
    return {"Message": "Hello World"}

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
if __name__ == "__main__":
    main()