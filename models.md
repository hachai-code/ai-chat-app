# How `models.py` works

This file is a small [Pydantic](https://docs.pydantic.dev/) v2 example: **models** describe the shape of data, **validation** runs when instances are created, and the bottom of the file **demonstrates** success and failure paths.

Official background: [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/).

---

## `BaseModel` and the three models

`User`, `Message`, and `Conversation` each subclass `BaseModel`. That gives you:

- **Typed fields** — each attribute has an expected type; values are checked (and coerced when Pydantic allows it, for example ISO strings into `datetime`).
- **A single validation pipeline** — whether data comes from keyword arguments or from a dict, the same rules apply.
- **Helpers** such as `model_validate` and exceptions like `ValidationError`.

So a `User` is not an arbitrary dict: it is a validated object that must satisfy the field types and any extra rules from `Field` and validators.

---

## `Field(...)`: constraints and defaults

Plain annotations (`id: int`, `email: str`) mark required fields with those types.

`Field(...)` adds **constraints** and **defaults**:

| Location | What it does |
|----------|----------------|
| `username` | `min_length` / `max_length` enforce string length. |
| `content` | `min_length=1` rejects an empty message body. |
| `participants` | `min_length=2` requires at least two users in the list. |
| `created_at`, `timestamp` | `default_factory=datetime.now` means: if the field is **missing** from the input, Pydantic calls `datetime.now` (no parentheses in the source: you pass the **callable**, and Pydantic invokes it when building the instance) and assigns the result. If the field **is** present (for example in JSON), the factory is not used; the provided value is validated and stored. |

`messages` defaults to an empty list when you do not pass messages.

---

## Nested models

`Conversation` declares `participants: list[User]` and `messages: list[Message]`. Pydantic performs **nested validation**: each list element is validated as the inner model. Errors are attached to the appropriate path (for example under `participants` or `messages`) in a `ValidationError`.

---

## `@field_validator` on `email`

`email_must_contain_at` is a **field validator** for the `email` field:

- It runs as part of validation when `email` is set.
- Returning `v.lower()` **normalises** the stored value (for example `BOB@EXAMPLE.COM` becomes `bob@example.com`).
- Raising `ValueError` **rejects** the input; Pydantic wraps that in a `ValidationError` with a clear message (for example when `"@"` is missing).

Validators use `@classmethod` and the `cls, v` pattern required by Pydantic v2’s `field_validator`.

---

## Demo: two ways to build instances

1. **`User.model_validate(json.loads(user_json))`** — Turn JSON into a dict, then run the full validation pipeline on that dict. String datetimes in JSON coerce to `datetime` where valid.

2. **`User(id=2, username="bob", email="BOB@EXAMPLE.COM")`** — Direct construction also validates; the email validator lowercases the email.

`Message.model_validate(...)` is the same idea for messages.

Then a `Conversation` is built from already-valid `User` and `Message` instances, including nested lists.

---

## Demo: `ValidationError`

Each `try` / `except ValidationError` block shows a different failure:

- Invalid email (fails the custom validator).
- Username too short (fails `Field` on `username`).
- Only one participant (fails `Field` on `participants`).
- Empty `content` (fails `Field` on `content`).

Printing `e` shows Pydantic’s structured error summary; in real code you often use `e.errors()` for programmatic handling.

---

## `add_message`

`add_message` is normal Python: it appends to `self.messages`. Pydantic does not automatically re-validate the whole `Conversation` after every append; the demo assumes you only append objects that are already valid `Message` instances.
