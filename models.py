import json
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError, field_validator


class User(BaseModel):
    id: int
    username: str = Field(min_length=3, max_length=50)
    email: str
    created_at: datetime = Field(default_factory=datetime.now)

    @field_validator("email")
    @classmethod
    def email_must_contain_at(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("invalid email address")
        return v.lower()


class Message(BaseModel):
    id: int
    content: str = Field(min_length=1)
    sender_id: int
    timestamp: datetime = Field(default_factory=datetime.now)


class Conversation(BaseModel):
    id: int
    participants: list[User] = Field(min_length=2)
    messages: list[Message] = []

    def add_message(self, message: Message) -> None:
        self.messages.append(message)


# --- Demo ---

user_json = """
{
    "id": 1,
    "username": "alice",
    "email": "alice@example.com",
    "created_at": "2024-01-15T10:30:00"
}
"""

message_json = """
{
    "id": 101,
    "content": "Hello, Bob!",
    "sender_id": 1,
    "timestamp": "2024-01-15T10:31:00"
}
"""

print("=== Parsing valid data ===")
alice = User.model_validate(json.loads(user_json))
print(f"User: {alice}")

bob = User(id=2, username="bob", email="BOB@EXAMPLE.COM")
print(f"User: {bob}")  # email normalised to lowercase

msg = Message.model_validate(json.loads(message_json))
print(f"Message: {msg}")

convo = Conversation(id=1, participants=[alice, bob], messages=[msg])
print(f"Conversation participants: {[u.username for u in convo.participants]}")
print(f"Messages: {len(convo.messages)}")

print("\n=== Triggering validation errors ===")

# Bad email
try:
    User(id=3, username="charlie", email="not-an-email")
except ValidationError as e:
    print(f"Bad email error:\n{e}\n")

# Username too short
try:
    User(id=4, username="x", email="x@y.com")
except ValidationError as e:
    print(f"Short username error:\n{e}\n")

# Conversation with only one participant (min_length=2)
try:
    Conversation(id=2, participants=[alice])
except ValidationError as e:
    print(f"Too few participants error:\n{e}\n")

# Empty message content
try:
    Message(id=999, content="", sender_id=1)
except ValidationError as e:
    print(f"Empty content error:\n{e}")
